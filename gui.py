# --- gui.py ---
# Interfaz grafica (PySide6) que ENVUELVE el flujo existente carpeta -> parseo ->
# Excel. No agrega funciones nuevas: hace lo mismo que main.py pero como una app
# de ventana, con barra de progreso y registro en vivo. Toda la logica de
# procesamiento vive en core.py; este archivo solo arma la UI.
#
# Ejecutar con:  python gui.py
import os
import sys

from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QPlainTextEdit, QFileDialog,
    QMessageBox, QFrame,
)

import core

APP_TITLE = "Procesador CFDI"


class ProcessWorker(QObject):
    """Ejecuta core.process_path en un hilo aparte para no congelar la UI."""

    log = Signal(str)
    progress = Signal(int, int, str)   # actual, total, nombre de archivo
    finished = Signal(object)          # core.ProcessResult
    failed = Signal(str)

    def __init__(self, input_folder):
        super().__init__()
        self.input_folder = input_folder

    @Slot()
    def run(self):
        try:
            result = core.process_path(
                self.input_folder,
                on_log=self.log.emit,
                on_progress=lambda c, t, n: self.progress.emit(c, t, n),
            )
            self.finished.emit(result)
        except Exception as exc:  # red de seguridad: nunca matar el hilo en silencio
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(680, 480)

        self.input_folder = ""
        self.thread = None
        self.worker = None

        core.create_initial_directories()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Encabezado
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

        # Fila de seleccion de carpeta
        folder_row = QHBoxLayout()
        self.folder_label = QLabel("Ninguna carpeta seleccionada")
        self.folder_label.setStyleSheet(
            "padding: 6px; border: 1px solid palette(mid); border-radius: 4px;")
        self.select_btn = QPushButton("Seleccionar carpeta…")
        self.select_btn.clicked.connect(self.on_select_folder)
        folder_row.addWidget(self.folder_label, stretch=1)
        folder_row.addWidget(self.select_btn)
        layout.addLayout(folder_row)

        # Boton procesar
        self.process_btn = QPushButton("Procesar y exportar a Excel")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.on_process)
        layout.addWidget(self.process_btn)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Registro
        layout.addWidget(QLabel("Registro:"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, stretch=1)

        # Recordar ultima carpeta usada
        last = core.read_last_used_directory()
        if last:
            self._set_folder(last)

    # --- Helpers de UI ----------------------------------------------------
    def append_log(self, message):
        self.log_view.appendPlainText(message)

    def _set_folder(self, folder):
        self.input_folder = folder
        self.folder_label.setText(folder)
        self.process_btn.setEnabled(bool(folder) and os.path.isdir(folder))

    def _set_busy(self, busy):
        self.select_btn.setEnabled(not busy)
        self.process_btn.setEnabled(not busy and bool(self.input_folder))

    # --- Acciones ---------------------------------------------------------
    @Slot()
    def on_select_folder(self):
        start_dir = self.input_folder or core.read_last_used_directory() or core.BOVEDA_XML_DIR
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de XMLs CFDI", start_dir)
        if folder:
            self._set_folder(folder)
            core.save_last_used_directory(folder)
            self.append_log(f"Carpeta seleccionada: {folder}")

    @Slot()
    def on_process(self):
        if not self.input_folder or not os.path.isdir(self.input_folder):
            QMessageBox.warning(self, APP_TITLE,
                                "Selecciona primero una carpeta valida.")
            return

        self.log_view.clear()
        self.progress_bar.setValue(0)
        self._set_busy(True)

        # Arrancar worker en un hilo
        self.thread = QThread()
        self.worker = ProcessWorker(self.input_folder)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.append_log)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)

        # Limpieza del hilo
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    @Slot(int, int, str)
    def on_progress(self, current, total, name):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
            self.progress_bar.setFormat(f"%v / %m  -  {name}")

    @Slot(object)
    def on_finished(self, result):
        self._set_busy(False)
        self.thread = None
        self.worker = None

        if not result.has_data:
            self.progress_bar.setFormat("Sin datos")
            QMessageBox.information(
                self, APP_TITLE,
                "No se procesaron archivos XML CFDI validos.\n"
                "Verifica el directorio y los formatos de archivo.")
            return

        summary = (
            f"Procesados: {result.processed_count}  |  "
            f"Errores: {result.error_count}\n"
            f"Facturas: {len(result.invoice_data)}  |  "
            f"Nomina: {len(result.nomina_data)}  |  "
            f"Pagos: {len(result.pagos_data)}"
        )
        self.append_log("\n" + summary)
        self.progress_bar.setFormat("Completado")

        # Dialogo para guardar el Excel
        default_name = core.build_default_filename(result.all_parsed_data)
        default_path = os.path.join(core.REPORTS_DIR, default_name)
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Informe de Excel CFDI", default_path,
            "Archivos de Excel (*.xlsx)")

        if not output_path:
            self.append_log("Exportacion cancelada por el usuario.")
            return

        try:
            core.export_report(result, output_path)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE,
                                 f"Error al exportar el Excel:\n{exc}")
            return

        self.append_log(f"Excel guardado en: {output_path}")

        reply = QMessageBox.question(
            self, "Proceso completado",
            "Reporte generado correctamente.\n\nDeseas abrir el Excel ahora?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            try:
                core.open_file(output_path)
            except Exception as exc:
                self.append_log(f"No se pudo abrir el archivo: {exc}")

    @Slot(str)
    def on_failed(self, message):
        self._set_busy(False)
        self.thread = None
        self.worker = None
        self.progress_bar.setFormat("Error")
        QMessageBox.critical(self, APP_TITLE,
                             f"Ocurrio un error durante el procesamiento:\n{message}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
