# --- cfdi_app/ui/main_window.py ---
# Interfaz grafica (PySide6) que ENVUELVE el flujo existente carpeta -> parseo ->
# Excel. No agrega funciones nuevas: hace lo mismo que cli.py pero como una app
# de ventana, con barra de progreso, registro en vivo y una maquina de estados
# explicita. Toda la logica de procesamiento vive en core.py.
#
# CORRECCION DE FONDO DEL BUG 1 ("GUI congelada"): ver ROADMAP.md Sec.3 y 6.2.
# Reglas de oro de este archivo (documentadas ahi, repetidas aqui a proposito):
#   1. Los slots conectados a senales del worker/hilo (on_result, on_error,
#      on_progress) SOLO mutan estado y widgets. JAMAS abren dialogos modales.
#   2. Todo dialogo modal nace de un clic directo del usuario (on_select_folder,
#      on_save_clicked). Un dialogo iniciado por clic siempre tiene foco.
#   3. En estado DONE, el resumen se muestra DENTRO de la ventana (log), no en
#      un QMessageBox.
#   4. La exportacion ocurre en el hilo principal al hacer clic en "Guardar
#      Excel...".
#   5. Tras exportar con exito: se habilita el boton "Abrir archivo" - NO se
#      dispara un QMessageBox.question automatico.
import logging
import os

from PySide6.QtCore import Qt, QThread, Slot
from PySide6.QtWidgets import (
    QDockWidget, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout,
    QWidget,
)

from cfdi_app import core, paths, settings, vault
from cfdi_app.ui.results_view import ResultsView
from cfdi_app.ui.state import AppState, widget_states_for
from cfdi_app.ui.vault_sidebar import VaultSidebar
from cfdi_app.ui.worker import ProcessWorker

logger = logging.getLogger(__name__)

APP_TITLE = "Procesador CFDI"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(900, 700)

        self.input_folder = ""
        self._state = AppState.IDLE

        # Refs de hilo con nombre "_thread"/"_worker" (NO "self.thread": eso
        # sombrearia el metodo heredado QObject.thread() - defecto contribuyente
        # del Bug 1, ver ROADMAP.md Sec.3).
        self._thread = None
        self._worker = None
        self._last_result = None
        self._last_error = None
        self._last_saved_path = None

        core.create_initial_directories()

        self._build_ui()
        self._build_sidebar()
        self._build_menu()

        # Recordar ultima carpeta usada (settings.json - ver D14).
        last = settings.get_last_input_dir()
        if last:
            self.input_folder = last
            self.folder_label.setText(last)
            self._apply_state(AppState.READY)
        else:
            self._apply_state(AppState.IDLE)

    # --- Construccion de la UI ---------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Procesador de CFDI XML → Excel")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        subtitle = QLabel(
            "Selecciona una carpeta con XMLs (o .zip) del SAT. "
            "Detecta CFDI 3.3 / 4.0, Nomina y Pagos, y genera un Excel."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Flujo PRIMARIO = barra lateral de la bóveda (izquierda). Esta etiqueta
        # solo muestra el origen ad-hoc cuando se usa «Abrir carpeta…» del menú
        # (XMLs sueltos fuera de la bóveda, D11).
        folder_row = QHBoxLayout()
        self.folder_label = QLabel("Usa la Bóveda (izquierda) o «Archivo → Abrir carpeta…»")
        self.folder_label.setStyleSheet(
            "padding: 6px; border: 1px solid palette(mid); border-radius: 4px;")
        folder_row.addWidget(self.folder_label, stretch=1)
        layout.addLayout(folder_row)

        action_row = QHBoxLayout()
        self.process_btn = QPushButton("Procesar")
        self.process_btn.clicked.connect(self.on_process_clicked)
        self.save_btn = QPushButton("Guardar Excel…")
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.open_btn = QPushButton("Abrir archivo")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.on_open_clicked)
        self.open_folder_btn = QPushButton("Abrir carpeta")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.on_open_folder_clicked)
        action_row.addWidget(self.process_btn)
        action_row.addWidget(self.save_btn)
        action_row.addWidget(self.open_btn)
        action_row.addWidget(self.open_folder_btn)
        layout.addLayout(action_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Visor de resultados (ROADMAP.md Sec.11): tabla del lote actual con
        # filtro incremental y totales, ANTES de que exista cualquier Excel.
        layout.addWidget(QLabel("Resultados:"))
        self.results_view = ResultsView()
        layout.addWidget(self.results_view, stretch=2)

        layout.addWidget(QLabel("Registro:"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, stretch=1)

    # --- Barra lateral de la boveda (flujo primario, B3) ---------------------
    def _build_sidebar(self):
        self.vault_source = vault.FolderVaultSource(paths.BOVEDA_XML_DIR)
        self.vault_sidebar = VaultSidebar(self.vault_source)
        self.vault_sidebar.load_requested.connect(self.on_vault_load)
        self.vault_sidebar.status_message.connect(self.append_log)
        self.vault_sidebar.single_rfc_violation.connect(self.on_single_rfc_violation)

        self.vault_dock = QDockWidget("Bóveda", self)
        self.vault_dock.setObjectName("vault_dock")
        self.vault_dock.setWidget(self.vault_sidebar)
        self.vault_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.vault_dock)

    def _build_menu(self):
        menu = self.menuBar()

        archivo = menu.addMenu("&Archivo")
        self.select_action = archivo.addAction("Abrir carpeta de XMLs sueltos…")
        self.select_action.triggered.connect(self.on_select_folder)
        self.save_action = archivo.addAction("Guardar Excel…")
        self.save_action.triggered.connect(self.on_save_clicked)
        archivo.addSeparator()
        salir = archivo.addAction("Salir")
        salir.triggered.connect(self.close)

        boveda = menu.addMenu("&Bóveda")
        recargar = boveda.addAction("Recargar bóveda")
        recargar.triggered.connect(self.vault_sidebar.reload)
        self.download_action = boveda.addAction("Descargar del SAT…")
        self.download_action.setEnabled(False)  # F6: CIEC/e.firma (no construido)

        ver = menu.addMenu("&Ver")
        ver.addAction(self.vault_dock.toggleViewAction())

    # --- Maquina de estados --------------------------------------------------
    def _apply_state(self, state: AppState):
        self._state = state
        has_folder = bool(self.input_folder and os.path.isdir(self.input_folder))
        ws = widget_states_for(state, has_folder)

        self.select_action.setEnabled(ws.select_enabled)
        self.process_btn.setEnabled(ws.process_enabled)
        self.save_btn.setEnabled(ws.save_enabled)
        self.save_action.setEnabled(ws.save_enabled)
        self.vault_sidebar.set_busy(state == AppState.PROCESSING)

        if state != AppState.PROCESSING:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1 if state in (AppState.DONE, AppState.ERROR) else 0)
            self.progress_bar.setFormat(ws.progress_format)
        else:
            self.progress_bar.setRange(0, 0)  # indeterminada hasta el primer avance real
            self.progress_bar.setFormat("Procesando…")

    # --- Helpers de UI -------------------------------------------------------
    def append_log(self, message):
        self.log_view.appendPlainText(message)

    # --- Acciones (todas nacen de un clic del usuario) -----------------------
    @Slot()
    def on_select_folder(self):
        start_dir = self.input_folder or settings.get_last_input_dir() or paths.BOVEDA_XML_DIR
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de XMLs CFDI", start_dir)
        if not folder:
            return

        self.input_folder = folder
        self.folder_label.setText(folder)
        settings.set_last_input_dir(folder)

        # Una carpeta nueva invalida el resultado/archivo guardado anterior.
        self._last_result = None
        self._last_error = None
        self._last_saved_path = None
        self.open_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)
        self.results_view.clear()

        self.append_log(f"Carpeta seleccionada: {folder}")
        self._apply_state(AppState.READY)

    @Slot()
    def on_process_clicked(self):
        if not self.input_folder or not os.path.isdir(self.input_folder):
            QMessageBox.warning(self, APP_TITLE, "Selecciona primero una carpeta valida.")
            return
        self._start_processing(self.input_folder)

    @Slot(list)
    def on_vault_load(self, folders):
        """Carga desde la barra lateral de la boveda (lista de carpetas, B3)."""
        if not folders:
            return
        self.input_folder = ""  # una carga de boveda no es una carpeta ad-hoc
        self.folder_label.setText(
            f"Bóveda: {len(folders)} carpeta(s) seleccionada(s)")
        self._start_processing(folders)

    @Slot(list)
    def on_single_rfc_violation(self, rfcs):
        """Aviso por clic directo en «Cargar» (regla dura: un RFC por carga)."""
        QMessageBox.warning(
            self, "Un RFC a la vez",
            "No se pueden mezclar dos RFCs en la misma carga.\n\n"
            "Tienes marcados: " + ", ".join(rfcs) + ".\n"
            "Deja marcado solo uno y vuelve a intentar.")

    def _start_processing(self, folders):
        """Arranca el worker con una carpeta (str) o varias (list). Costura unica
        de ambos flujos: «Abrir carpeta…» ad-hoc y «Cargar» de la boveda."""
        self.log_view.clear()
        self._last_result = None
        self._last_error = None
        self._last_saved_path = None
        self.open_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)
        self.results_view.clear()
        self._apply_state(AppState.PROCESSING)

        # Patron canonico Qt (ROADMAP.md Sec.6.3): worker.finished dispara
        # tanto la limpieza de estado (on_result) como el cierre del hilo,
        # todo mientras el event loop del hilo sigue vivo -> sin fugas.
        self._thread = QThread(self)
        self._worker = ProcessWorker(folders)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(self.append_log)
        self._worker.progress.connect(self.on_progress)
        self._worker.finished.connect(self.on_result)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self.on_error)
        self._worker.failed.connect(self._thread.quit)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_fully_finished)

        self._thread.start()

    @Slot(int, int, str)
    def on_progress(self, current, total, name):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.progress_bar.setFormat(f"%v / %m  -  {name}")

    @Slot(object)
    def on_result(self, result):
        """Se ejecuta en el hilo principal cuando el worker termina.

        REGLA DE ORO: solo muta estado/widgets. Ningun dialogo modal aqui.
        """
        self._last_result = result

        if not result.has_data:
            self._apply_state(AppState.ERROR)
            self.append_log("\nNo se proceso ningun archivo XML CFDI valido.")
            self._log_errors(result.errors)
            return

        self._apply_state(AppState.DONE)
        summary = (
            f"\nProcesados: {result.processed_count}  |  Errores: {result.error_count}\n"
            f"Facturas: {len(result.invoice_data)}  |  "
            f"Nomina: {len(result.nomina_data)}  |  "
            f"Pagos: {len(result.pagos_data)}"
        )
        self.append_log(summary)
        self._log_errors(result.errors)
        self.results_view.set_result(result)

    @Slot(str)
    def on_error(self, message):
        """Se ejecuta en el hilo principal si el worker lanzo una excepcion."""
        self._last_error = message
        self._apply_state(AppState.ERROR)
        self.append_log(f"\nERROR durante el procesamiento: {message}")
        logger.error("ProcessWorker fallo: %s", message)

    @Slot()
    def _on_thread_fully_finished(self):
        # El hilo ya termino por completo; ahora si es seguro soltar las referencias.
        self._thread = None
        self._worker = None

    def _log_errors(self, errors):
        if not errors:
            return
        self.append_log(f"\n{len(errors)} archivo(s) con error:")
        for label, reason in errors:
            self.append_log(f"  - {label}: {reason}")

    @Slot()
    def on_save_clicked(self):
        if self._state != AppState.DONE or self._last_result is None:
            return

        default_name = core.build_default_filename(self._last_result.all_parsed_data)
        # D14: proponer la ultima carpeta donde se guardo un Excel; si no hay
        # ninguna aun, caer a Reports (comportamiento original).
        default_dir = settings.get_last_save_dir() or paths.REPORTS_DIR
        default_path = os.path.join(default_dir, default_name)
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Informe de Excel CFDI", default_path,
            "Archivos de Excel (*.xlsx)")

        if not output_path:
            self.append_log("Exportacion cancelada por el usuario.")
            return

        try:
            core.export_report(self._last_result, output_path)
        except PermissionError:
            QMessageBox.critical(
                self, APP_TITLE,
                "No se pudo guardar el Excel: el archivo esta abierto en otro "
                "programa (por ejemplo Excel). Cierralo e intenta de nuevo.")
            return
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Error al exportar el Excel:\n{exc}")
            return

        self._last_saved_path = output_path
        settings.set_last_save_dir(os.path.dirname(output_path))
        self.append_log(f"\nExcel guardado en: {output_path}")
        self.open_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)

    @Slot()
    def on_open_clicked(self):
        if not self._last_saved_path:
            return
        try:
            core.open_file(self._last_saved_path)
        except Exception as exc:
            self.append_log(f"No se pudo abrir el archivo: {exc}")

    @Slot()
    def on_open_folder_clicked(self):
        if not self._last_saved_path:
            return
        try:
            core.open_containing_folder(self._last_saved_path)
        except Exception as exc:
            self.append_log(f"No se pudo abrir la carpeta: {exc}")
