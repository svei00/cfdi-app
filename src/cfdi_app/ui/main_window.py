# --- cfdi_app/ui/main_window.py ---
# Interfaz grafica (PySide6) que ENVUELVE el flujo existente carpeta -> parseo ->
# Excel. No agrega funciones nuevas: hace lo mismo que cli.py pero como una app
# de ventana, con barra de progreso, registro en vivo y una maquina de estados
# explicita. Toda la logica de procesamiento vive en core.py.
#
# CORRECCION DE FONDO DEL BUG 1 ("GUI congelada"): ver ROADMAP.md Sec.3 y 6.2.
# Reglas de oro de este archivo (documentadas ahi, repetidas aqui a proposito):
#   1. Los slots conectados a senales del worker/hilo (on_result, on_error,
#      on_progress, on_move_finished, on_move_failed) SOLO mutan estado y
#      widgets. JAMAS abren dialogos modales.
#   2. Todo dialogo modal nace de un clic directo del usuario (on_select_folder,
#      on_save_clicked, on_move_vault_clicked). Un dialogo iniciado por clic
#      siempre tiene foco.
#   3. En estado DONE, el resumen se muestra DENTRO de la ventana (log), no en
#      un QMessageBox.
#   4. La exportacion ocurre en el hilo principal al hacer clic en "Guardar
#      Excel...".
#   5. Tras exportar con exito: se habilita el boton "Abrir archivo" - NO se
#      dispara un QMessageBox.question automatico.
#
# B3-R2 (D36): el central widget es un QStackedWidget de dos paginas -
# InicioPage (caratula) y AdminBovedaPage (modulo "Administrador de Boveda",
# que absorbe el arbol de boveda + resultados + log; reemplaza al
# QDockWidget, que se elimino por completo junto con el menu Ver). Los hilos
# y senales de procesamiento (y de mudanza de boveda, D39) siguen viviendo
# AQUI, no en las paginas: cambiar de pagina nunca cancela un proceso en curso.
import logging
import os

from PySide6.QtCore import QThread, Slot
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QMainWindow, QMessageBox, QStackedWidget,
)

from cfdi_app import core, paths, settings, vault
from cfdi_app.exporters import desglose_exporter
from cfdi_app.reports import desglose_conceptos
from cfdi_app.ui.admin_boveda_page import AdminBovedaPage
from cfdi_app.ui.desglose_dialog import DesgloseDialog
from cfdi_app.ui.desglose_lote_dialog import DesgloseLoteDialog
from cfdi_app.ui.desglose_xml_dialog import DesgloseXmlDialog
from cfdi_app.ui.inicio_page import InicioPage
from cfdi_app.ui.reportes_page import ReportesPage
from cfdi_app.ui.state import AppState, widget_states_for
from cfdi_app.ui.vault_move_worker import VaultMoveWorker
from cfdi_app.ui.worker import ProcessWorker

logger = logging.getLogger(__name__)

APP_TITLE = "Procesador CFDI"

PAGE_INICIO = 0
PAGE_MODULO = 1
PAGE_REPORTES = 2


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1100, 750)

        self.input_folder = ""
        self._state = AppState.IDLE
        self._vault_move_busy = False

        # Refs de hilo con nombre "_thread"/"_worker" (NO "self.thread": eso
        # sombrearia el metodo heredado QObject.thread() - defecto contribuyente
        # del Bug 1, ver ROADMAP.md Sec.3).
        self._thread = None
        self._worker = None
        self._last_result = None
        self._last_error = None
        self._last_saved_path = None

        self._move_thread = None
        self._move_worker = None

        core.create_initial_directories()

        self._build_ui()
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
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self.inicio_page = InicioPage()
        self.inicio_page.open_vault_module.connect(self.show_module_page)
        self.inicio_page.open_reports_page.connect(self.show_reportes_page)
        self._stack.addWidget(self.inicio_page)

        # D39: la ruta ACTIVA de la boveda viene de settings, no del default
        # fijo de paths.py (que puede haber quedado atras tras una mudanza).
        self.vault_source = vault.FolderVaultSource(settings.get_vault_root())
        self.admin_page = AdminBovedaPage(self.vault_source)
        self.admin_page.home_btn.clicked.connect(self.show_inicio_page)
        self._stack.addWidget(self.admin_page)

        self.reportes_page = ReportesPage()
        self.reportes_page.go_home.connect(self.show_inicio_page)
        self.reportes_page.open_reports_folder.connect(self.on_open_reports_folder_clicked)
        self.reportes_page.open_desglose.connect(self.on_desglose_clicked)
        self._stack.addWidget(self.reportes_page)

        # Alias para que el resto de la clase (logica preexistente, sin
        # cambios de comportamiento) siga hablando de estos widgets por su
        # nombre de siempre, aunque ahora vivan dentro de AdminBovedaPage.
        self.vault_sidebar = self.admin_page.vault_sidebar
        self.folder_label = self.admin_page.folder_label
        self.open_loose_xml_btn = self.admin_page.open_loose_xml_btn
        self.process_btn = self.admin_page.process_btn
        self.save_btn = self.admin_page.save_btn
        self.save_filtered_btn = self.admin_page.save_filtered_btn
        self.desglose_lote_btn = self.admin_page.desglose_lote_btn
        self.open_btn = self.admin_page.open_btn
        self.open_folder_btn = self.admin_page.open_folder_btn
        self.progress_bar = self.admin_page.progress_bar
        self.results_view = self.admin_page.results_view
        self.log_view = self.admin_page.log_view

        # F2.10 etapa 3: clic derecho en Facturas -> desglose de ese XML.
        self.results_view.desglose_requested.connect(
            self.on_desglose_xml_requested)

        self.open_loose_xml_btn.clicked.connect(self.on_select_folder)
        self.process_btn.clicked.connect(self.on_process_clicked)
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.save_filtered_btn.clicked.connect(self.on_save_filtered_clicked)
        self.desglose_lote_btn.clicked.connect(self.on_desglose_lote_clicked)
        self.open_btn.clicked.connect(self.on_open_clicked)
        self.open_folder_btn.clicked.connect(self.on_open_folder_clicked)
        # F2.7: el filtro de texto no es parte de AppState (§16.3) - se
        # recalcula aparte, en vivo, cada vez que cambia alguna caja de busqueda.
        self.results_view.filter_changed.connect(self._update_save_filtered_enabled)

        self.vault_sidebar.load_requested.connect(self.on_vault_load)
        self.vault_sidebar.status_message.connect(self.append_log)
        self.vault_sidebar.single_rfc_violation.connect(self.on_single_rfc_violation)
        self.vault_sidebar.multiple_tipos_violation.connect(self.on_multiple_tipos_violation)

        self._stack.setCurrentIndex(PAGE_INICIO)

    def _build_menu(self):
        menu = self.menuBar()

        # "Guardar Excel…" se retira de este menu (2026-07-19): duplicaba,
        # con otro texto, el boton que ya esta pegado a "Procesar" en el
        # modulo - un menu no debe repetir un boton siempre visible (feedback
        # real: "no tiene mucho sentido... tienes los botones justo arriba").
        archivo = menu.addMenu("&Archivo")
        self.select_action = archivo.addAction("Abrir XMLs sueltos…")
        self.select_action.triggered.connect(self.on_select_folder)
        archivo.addSeparator()
        # F2.9 (D43/§18.3): SOLO menu, sin boton propio - la fila de acciones
        # ya trae 5 botones y un sexto la satura. Distinto de "Guardar
        # Excel..." (arriba): aquella accion SI duplicaba un boton siempre
        # visible; esta no tiene boton en ningun lado, el menu es su unico hogar.
        self.export_csv_action = archivo.addAction("Exportar pestaña a CSV…")
        self.export_csv_action.triggered.connect(self.on_export_csv_clicked)
        archivo.addSeparator()
        salir = archivo.addAction("Salir")
        salir.triggered.connect(self.close)

        # D40: el menu Ver se elimina por completo (version/licencia iran en
        # un futuro menu Ayuda). D36: el modulo se abre/cierra desde aqui.
        boveda = menu.addMenu("&Bóveda")
        self.open_module_action = boveda.addAction("Mi Bóveda")
        self.open_module_action.setShortcut(QKeySequence("Ctrl+B"))
        self.open_module_action.triggered.connect(self.show_module_page)
        boveda.addSeparator()
        recargar = boveda.addAction("Recargar bóveda")
        recargar.triggered.connect(self.vault_sidebar.reload)
        # Dos acciones DISTINTAS a proposito (feedback real del dueño, D41):
        # "mover" fisicamente reubica los archivos de la boveda ACTUAL a una
        # carpeta vacia; "usar otra carpeta" adopta una carpeta EXISTENTE que
        # ya tiene la estructura RFC/tipo/año/mes (p. ej. una boveda armada
        # con otra herramienta) SIN mover ni un archivo - solo cambia a donde
        # apunta la app. Confundirlas arriesgaria datos reales del dueño.
        self.move_vault_action = boveda.addAction("Mover bóveda a otra carpeta…")
        self.move_vault_action.setToolTip(
            "Reubica físicamente los archivos de la bóveda actual")
        self.move_vault_action.triggered.connect(self.on_move_vault_clicked)
        self.adopt_vault_action = boveda.addAction("Usar otra carpeta como bóveda…")
        self.adopt_vault_action.setToolTip(
            "Apunta la app a una carpeta ya existente, sin mover archivos")
        self.adopt_vault_action.triggered.connect(self.on_adopt_vault_clicked)
        boveda.addSeparator()
        self.download_action = boveda.addAction("Descargar del SAT…")
        self.download_action.setEnabled(False)  # F6: CIEC/e.firma (no construido)

        # D40 preveia este menu para version/licencia; se adelanta un poco
        # (2026-07-19) porque "mover" vs "usar otra carpeta" resulto confuso
        # en la practica (feedback real) y merece una explicacion a un clic.
        ayuda = menu.addMenu("A&yuda")
        self.vault_help_action = ayuda.addAction("Mover vs. usar otra carpeta…")
        self.vault_help_action.setShortcut(QKeySequence("F1"))
        self.vault_help_action.triggered.connect(self.on_vault_help_clicked)

    @Slot()
    def on_vault_help_clicked(self):
        """Clic directo (F1 o menu) - dialogo informativo legitimo."""
        QMessageBox.information(
            self, "Mover vs. usar otra carpeta",
            "Tu bóveda vive en UNA ubicación a la vez. Hay dos formas de "
            "cambiarla, y hacen cosas distintas:\n\n"
            "• Mover bóveda a otra carpeta…\n"
            "Reubica físicamente tus archivos actuales a una carpeta nueva. "
            "Solo funciona si el destino está vacío - si ya tuviera datos, "
            "la app se niega a continuar (nunca mezcla).\n\n"
            "• Usar otra carpeta como bóveda…\n"
            "NO mueve nada. Apunta la app a una carpeta que YA tiene tus "
            "RFCs (por ejemplo, una bóveda armada con otra herramienta). "
            "Elige la carpeta que contiene las carpetas de RFC, o su carpeta "
            "padre - la app detecta el nivel correcto automáticamente.")

    # --- Navegacion entre paginas (D36) ---------------------------------------
    @Slot()
    def show_module_page(self):
        self._stack.setCurrentIndex(PAGE_MODULO)

    @Slot()
    def show_inicio_page(self):
        self._stack.setCurrentIndex(PAGE_INICIO)

    @Slot()
    def show_reportes_page(self):
        self.reportes_page.set_desglose_available(
            self._last_result is not None and self._last_result.has_data)
        self._stack.setCurrentIndex(PAGE_REPORTES)

    @Slot()
    def on_desglose_clicked(self):
        """Desglose de conceptos (F2.10): opera sobre el lote ya cargado."""
        if self._last_result is None or not self._last_result.has_data:
            return
        datos = self._last_result.all_parsed_data
        lineas = desglose_conceptos.aplanar_lote(datos)
        if not lineas:
            QMessageBox.information(
                self, APP_TITLE,
                "El lote cargado no tiene facturas con conceptos "
                "(solo hay pagos, nóminas u otros).")
            return

        dialog = DesgloseDialog(
            desglose_conceptos.proveedores(lineas),
            desglose_exporter.HOJAS_DISPONIBLES,
            desglose_conceptos.hay_ecc(lineas),
            desglose_exporter.HOJA_COMBUSTIBLE, self)
        if dialog.exec() != QDialog.Accepted:
            return

        rfc = dialog.selected_provider
        filtradas = desglose_conceptos.filtrar_por_proveedor(lineas, rfc)
        hojas = dialog.selected_sheets
        self._guardar_desglose_excel(
            lambda ruta: desglose_exporter.exportar_desglose(
                datos, ruta, rfc_emisor=rfc, hojas=hojas),
            desglose_conceptos.nombre_archivo(filtradas, rfc))

    @Slot(str)
    def on_desglose_xml_requested(self, uuid):
        """Desglose de UN comprobante (F2.10 etapa 3): clic derecho en el
        visor de Facturas. Si el mismo UUID aparece varias veces en el lote
        se usa la primera aparicion."""
        if self._last_result is None:
            return
        uuid = str(uuid).upper()
        registros = [d for d in self._last_result.all_parsed_data
                     if str(d.get("UUID") or "").upper() == uuid][:1]
        lineas = desglose_conceptos.aplanar_lote(registros)
        if not lineas:
            QMessageBox.information(
                self, APP_TITLE,
                "Este comprobante no tiene conceptos de gasto que desglosar "
                "(por ejemplo un pago o una nómina).")
            return

        dialog = DesgloseXmlDialog(lineas, desglose_conceptos.cuadre(registros)[0], self)
        dialog.exec()
        if not dialog.wants_export:
            return
        # Un solo comprobante: las hojas agregadas ("Por mes", etc.) no
        # aportan nada, solo Detalle, IVA, Cuadre y (si aplica) Combustible.
        hojas = {desglose_exporter.HOJA_DETALLE, desglose_exporter.HOJA_IVA,
                 desglose_exporter.HOJA_CUADRE,
                 desglose_exporter.HOJA_COMBUSTIBLE}
        self._guardar_desglose_excel(
            lambda ruta: desglose_exporter.exportar_desglose(
                registros, ruta, hojas=hojas),
            desglose_conceptos.nombre_archivo(
                lineas, sufijo=lineas[0]["factura"] or uuid[:8]))

    @Slot()
    def on_desglose_lote_clicked(self):
        """Visor del desglose del lote completo: arbol RFC -> factura ->
        conceptos con caja de busqueda (F2.10)."""
        if self._last_result is None or not self._last_result.has_data:
            return
        lineas = desglose_conceptos.aplanar_lote(
            self._last_result.all_parsed_data)
        if not lineas:
            QMessageBox.information(
                self, APP_TITLE,
                "El lote cargado no tiene facturas con conceptos "
                "(solo hay pagos, nóminas u otros).")
            return

        dialog = DesgloseLoteDialog(lineas, self)
        dialog.desglose_requested.connect(self.on_desglose_xml_requested)
        dialog.exec()
        if not dialog.wants_export:
            return
        visibles = dialog.visible_lines
        sufijo = f"filtrado-{dialog.query[:30]}" if dialog.query else ""
        self._guardar_desglose_excel(
            lambda ruta: desglose_exporter.exportar_desglose_lineas(
                visibles, ruta),
            desglose_conceptos.nombre_archivo(visibles, sufijo=sufijo))

    def _guardar_desglose_excel(self, escribir, nombre_sugerido):
        """Pide la ruta y llama a escribir(ruta) (compartido por el reporte
        del lote, el de un solo XML y el filtrado del visor)."""
        default_dir = settings.get_last_save_dir() or paths.REPORTS_DIR
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Desglose de conceptos",
            os.path.join(default_dir, nombre_sugerido),
            "Archivos de Excel (*.xlsx)")
        if not output_path:
            self.append_log("Desglose cancelado por el usuario.")
            return

        try:
            escribir(output_path)
        except PermissionError:
            QMessageBox.critical(
                self, APP_TITLE,
                "No se pudo guardar el Excel: el archivo está abierto en otro "
                "programa (por ejemplo Excel). Ciérralo e intenta de nuevo.")
            return
        except Exception as exc:
            QMessageBox.critical(
                self, APP_TITLE, f"Error al exportar el desglose:\n{exc}")
            return

        self._last_saved_path = output_path
        settings.set_last_save_dir(os.path.dirname(output_path))
        self.append_log(f"\nDesglose guardado en: {output_path}")

    @Slot()
    def on_open_reports_folder_clicked(self):
        """Clic directo del usuario (dialogo/accion del SO, legitimo)."""
        try:
            os.makedirs(paths.REPORTS_DIR, exist_ok=True)
            core.open_folder(paths.REPORTS_DIR)
        except Exception as exc:
            self.append_log(f"No se pudo abrir la carpeta de reportes: {exc}")

    # --- Maquina de estados --------------------------------------------------
    def _apply_state(self, state: AppState):
        self._state = state
        has_folder = bool(self.input_folder and os.path.isdir(self.input_folder))
        ws = widget_states_for(state, has_folder)
        # Una mudanza de boveda en curso deshabilita todo lo que toca la
        # boveda o dispara procesamiento, igual que PROCESSING (D39).
        moving = self._vault_move_busy

        self.select_action.setEnabled(ws.select_enabled and not moving)
        self.open_loose_xml_btn.setEnabled(ws.select_enabled and not moving)
        self.process_btn.setEnabled(ws.process_enabled and not moving)
        self.save_btn.setEnabled(ws.save_enabled and not moving)
        self.desglose_lote_btn.setEnabled(ws.save_enabled and not moving)
        # F2.9 (D43/§18.3): mismo criterio que "Guardar Excel..." - hay
        # resultado (DONE) que exportar.
        self.export_csv_action.setEnabled(ws.save_enabled and not moving)
        self.move_vault_action.setEnabled(state != AppState.PROCESSING and not moving)
        self.adopt_vault_action.setEnabled(state != AppState.PROCESSING and not moving)
        self.vault_sidebar.set_busy(state == AppState.PROCESSING or moving)

        if state != AppState.PROCESSING:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1 if state in (AppState.DONE, AppState.ERROR) else 0)
            self.progress_bar.setFormat(ws.progress_format)
        else:
            self.progress_bar.setRange(0, 0)  # indeterminada hasta el primer avance real
            self.progress_bar.setFormat("Procesando…")

        self._update_save_filtered_enabled()

    @Slot()
    def _update_save_filtered_enabled(self):
        """F2.7 (D29/§16.3): "Guardar filtrado…" se habilita SOLO con estado
        DONE y al menos una pestaña con filtro activo. El filtro de texto no
        es parte de AppState, asi que esto se recalcula aparte - tanto desde
        _apply_state (cambios de estado) como desde ResultsView.filter_changed
        (el usuario escribe/borra en una caja de busqueda sin que el estado
        cambie)."""
        self.save_filtered_btn.setEnabled(
            self._state == AppState.DONE
            and not self._vault_move_busy
            and self.results_view.has_any_active_filter())

    # --- Helpers de UI -------------------------------------------------------
    def append_log(self, message):
        self.log_view.appendPlainText(message)

    # --- Acciones (todas nacen de un clic del usuario) -----------------------
    @Slot()
    def on_select_folder(self):
        start_dir = self.input_folder or settings.get_last_input_dir() or settings.get_vault_root()
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
        # D36: "Abrir carpeta…" tambien navega al modulo - es EL espacio de
        # trabajo de procesamiento, venga la carga de boveda o de carpeta suelta.
        self.show_module_page()

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

    @Slot(list)
    def on_multiple_tipos_violation(self, tipos):
        """Aviso por clic directo en «Cargar» (regla dura D21: una direccion
        por carga - Emitidas XOR Recibidas, nunca ambas). Bug real
        2026-07-25: sin esta validacion, casillas de una carga anterior que
        quedaban marcadas por accidente (vault_sidebar ahora las limpia tras
        Cargar) podian combinarse con las de la carga nueva y mezclar
        direcciones en un solo lote."""
        QMessageBox.warning(
            self, "Una dirección a la vez",
            "No se pueden mezclar Emitidas y Recibidas en la misma carga.\n\n"
            "Tienes marcados: " + ", ".join(tipos) + ".\n"
            "Deja marcada solo una dirección y vuelve a intentar.")

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

    # --- Exportacion filtrada "espejo del visor" (F2.7, D29/§16) -------------
    @Slot()
    def on_save_filtered_clicked(self):
        """Cada hoja sale segun SU PROPIO filtro de pestaña (§16.2): pestañas
        con filtro activo salen recortadas, sin filtro salen COMPLETAS. El
        boton "Guardar Excel…" (on_save_clicked) NO cambia - este es un
        camino separado a proposito (§16.3)."""
        if self._state != AppState.DONE or self._last_result is None:
            return
        if not self.results_view.has_any_active_filter():
            return  # boton deberia estar deshabilitado; defensivo nomas

        active = self.results_view.active_filter_info()
        default_name = core.build_filtered_filename(
            self._last_result.all_parsed_data, [query for _, query in active])
        default_dir = settings.get_last_save_dir() or paths.REPORTS_DIR
        default_path = os.path.join(default_dir, default_name)
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel filtrado", default_path,
            "Archivos de Excel (*.xlsx)")

        if not output_path:
            self.append_log("Exportacion filtrada cancelada por el usuario.")
            return

        filtered = self.results_view.filtered_data()
        try:
            core.export_report_filtered(
                filtered.get("invoice_data", []), filtered.get("nomina_data", []),
                filtered.get("pagos_data", []), output_path)
        except PermissionError:
            QMessageBox.critical(
                self, APP_TITLE,
                "No se pudo guardar el Excel: el archivo esta abierto en otro "
                "programa (por ejemplo Excel). Cierralo e intenta de nuevo.")
            return
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Error al exportar el Excel:\n{exc}")
            return

        # Igual que on_save_clicked (§16.3): "Abrir archivo"/"Abrir carpeta"
        # apuntan al ultimo archivo guardado, sea filtrado o completo.
        self._last_saved_path = output_path
        settings.set_last_save_dir(os.path.dirname(output_path))
        self.append_log(f"\nExcel filtrado guardado en: {output_path}")
        self.open_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)

    # --- Exportacion CSV de la pestaña activa (F2.9, D43/§18) ----------------
    @Slot()
    def on_export_csv_clicked(self):
        """Exporta la pestaña ACTIVA del visor a CSV, respetando su filtro
        (misma fidelidad que "Guardar filtrado…", §16.5/§18.6). El modo de
        columnas (curado D46-D48 vs las 70 del Excel + suficiencia) se elige
        con el propio selector de filtro del dialogo de guardado - SIN
        widgets nuevos (D44). El Excel (Guardar Excel…/Guardar filtrado…) NO
        cambia."""
        if self._state != AppState.DONE or self._last_result is None:
            return

        export_data = self.results_view.active_tab_export_data()
        default_name = core.build_csv_filename(
            self._last_result.all_parsed_data,
            export_data["title"], export_data["query"])
        default_dir = settings.get_last_save_dir() or paths.REPORTS_DIR
        default_path = os.path.join(default_dir, default_name)

        filtro_visor = "Columnas del visor (*.csv)"
        filtro_todas = "Todas las columnas (*.csv)"
        output_path, filtro_elegido = QFileDialog.getSaveFileName(
            self, "Exportar pestaña a CSV", default_path,
            f"{filtro_visor};;{filtro_todas}", filtro_visor)

        if not output_path:
            self.append_log("Exportacion a CSV cancelada por el usuario.")
            return

        # D46-D48: curacion + campos derivados (bases IVA, cruce relacionado)
        # + columnas constantes separadas a un encabezado unico, todo resuelto
        # aqui - el cruce necesita el LOTE COMPLETO (sin filtrar) para tener
        # la mejor oportunidad de encontrar el CFDI relacionado.
        preamble, columns, rows = core.build_csv_export(
            export_data["tab_key"], export_data["rows"],
            all_columns=(filtro_elegido == filtro_todas),
            full_batch_invoice_data=self._last_result.invoice_data)

        try:
            core.export_tab_csv(rows, columns, output_path, preamble_lines=preamble)
        except PermissionError:
            QMessageBox.critical(
                self, APP_TITLE,
                "No se pudo guardar el CSV: el archivo esta abierto en otro "
                "programa (por ejemplo Excel). Cierralo e intenta de nuevo.")
            return
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Error al exportar el CSV:\n{exc}")
            return

        self._last_saved_path = output_path
        settings.set_last_save_dir(os.path.dirname(output_path))
        self.append_log(f"\nCSV exportado en: {output_path}")
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

    # --- Mover boveda (D39, clic directo del usuario) ------------------------
    @Slot()
    def on_move_vault_clicked(self):
        """Reubica FISICAMENTE los archivos de la boveda actual a una carpeta
        vacia. NO usar para adoptar una carpeta que ya tiene datos - eso es
        on_adopt_vault_clicked (D41), que no mueve nada."""
        current_root = settings.get_vault_root()
        dest_parent = QFileDialog.getExistingDirectory(
            self, "Elegir carpeta destino para la bóveda", current_root)
        if not dest_parent:
            return

        try:
            new_root = vault.validate_vault_move(current_root, dest_parent)
        except vault.VaultMoveError as exc:
            QMessageBox.warning(self, "Mover bóveda a otra carpeta", str(exc))
            return

        # D41 ampliado 2026-07-19: el dueño temia que "mover" pudiera MEZCLAR
        # su boveda con datos reales ya existentes en el destino. Ya es
        # imposible - validate_vault_move (arriba) rechaza la mudanza si el
        # destino ya tiene una BovedaCFDI con contenido - pero el aviso debe
        # DECIRLO explicitamente, no solo serlo por debajo.
        rfc_count = len(self.vault_source.rfcs())
        confirm = QMessageBox.question(
            self, "Mover bóveda a otra carpeta",
            f"Se moverá TODA la bóveda ({rfc_count} RFC(s)) de:\n{current_root}\n\n"
            f"a:\n{new_root}\n\n"
            "Es seguro: si el destino ya tuviera datos, la app se hubiera "
            "negado a continuar (nunca mezcla). ¿Continuar?")
        if confirm != QMessageBox.Yes:
            return

        self._vault_move_busy = True
        self._apply_state(self._state)
        self.append_log(f"\nMoviendo bóveda a: {new_root}…")

        # Mismo patron canonico Qt que _start_processing (ROADMAP.md Sec.6.3).
        self._move_thread = QThread(self)
        self._move_worker = VaultMoveWorker(current_root, dest_parent)
        self._move_worker.moveToThread(self._move_thread)

        self._move_thread.started.connect(self._move_worker.run)
        self._move_worker.log.connect(self.append_log)
        self._move_worker.progress.connect(self.on_move_progress)
        self._move_worker.finished.connect(self.on_move_finished)
        self._move_worker.finished.connect(self._move_thread.quit)
        self._move_worker.finished.connect(self._move_worker.deleteLater)
        self._move_worker.failed.connect(self.on_move_failed)
        self._move_worker.failed.connect(self._move_thread.quit)
        self._move_worker.failed.connect(self._move_worker.deleteLater)
        self._move_thread.finished.connect(self._move_thread.deleteLater)
        self._move_thread.finished.connect(self._on_move_thread_fully_finished)

        self._move_thread.start()

    @Slot(int, int, str)
    def on_move_progress(self, current, total, name):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.progress_bar.setFormat(f"Moviendo %v / %m  -  {name}")

    @Slot(str)
    def on_move_finished(self, new_root):
        """Se ejecuta en el hilo principal. REGLA DE ORO: sin dialogos modales."""
        settings.set_vault_root(new_root)
        self.vault_source.root = new_root
        self._vault_move_busy = False
        self._apply_state(self._state)
        self.vault_sidebar.reload()
        self.append_log(f"\nBóveda movida a: {new_root}")

    @Slot(str)
    def on_move_failed(self, message):
        """Se ejecuta en el hilo principal. REGLA DE ORO: sin dialogos modales."""
        self._vault_move_busy = False
        self._apply_state(self._state)
        self.append_log(f"\nERROR moviendo la bóveda: {message}")
        logger.error("VaultMoveWorker fallo: %s", message)

    @Slot()
    def _on_move_thread_fully_finished(self):
        self._move_thread = None
        self._move_worker = None

    # --- Adoptar carpeta existente como boveda (D41, clic directo) -----------
    @Slot()
    def on_adopt_vault_clicked(self):
        """Apunta vault_root a una carpeta EXISTENTE (p. ej. una boveda armada
        con otra herramienta, misma estructura RFC/tipo/año/mes) SIN mover ni
        borrar un solo archivo - es un cambio de puntero en settings.json, no
        una operacion de disco. Distinta de on_move_vault_clicked a proposito:
        el dueño ya tiene datos reales en una ruta ajena a la app y NO quiere
        que se muevan (feedback real, D39 solo cubria mudanza fisica)."""
        current_root = settings.get_vault_root()
        chosen = QFileDialog.getExistingDirectory(
            self, "Elegir la carpeta que contiene tus RFCs (o su carpeta padre)",
            current_root)
        if not chosen:
            return

        # D41 ampliado 2026-07-19: el dueño no sabia que NIVEL de carpeta
        # elegir (la que tiene los RFCs adentro, o su padre). Se adivina
        # automaticamente en vez de exigir precision del usuario.
        chosen, adjusted = vault.resolve_vault_candidate(chosen)
        if adjusted:
            self.append_log(f"Ajustada automáticamente a: {chosen}")

        if os.path.normcase(chosen) == os.path.normcase(os.path.abspath(current_root)):
            self.append_log("Esa carpeta ya es la bóveda activa.")
            return

        rfc_count = len(vault.FolderVaultSource(chosen).rfcs())
        if rfc_count:
            found = f"Se encontraron {rfc_count} RFC(s) válidos en esa carpeta."
        else:
            found = (
                "No se encontraron RFCs con el formato esperado en esa carpeta "
                "(puede estar vacía o no seguir la estructura "
                "RFC/Emitidas-Recibidas/año/mes).")
        confirm = QMessageBox.question(
            self, "Usar otra carpeta como bóveda",
            f"{found}\n\nLa bóveda activa pasará a ser:\n{chosen}\n\n"
            "NO se moverá ni se borrará ningún archivo - solo cambia a dónde "
            "apunta la app. ¿Continuar?")
        if confirm != QMessageBox.Yes:
            return

        settings.set_vault_root(chosen)
        self.vault_source.root = chosen
        self.vault_sidebar.reload()
        self.append_log(f"\nBóveda activa: {chosen}")
