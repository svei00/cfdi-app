# --- cfdi_app/ui/worker.py ---
# Worker que ejecuta core.process_path en un hilo aparte (QThread) para no
# congelar la UI. Ver ROADMAP.md Sec.6.3 para el patron canonico de conexiones
# que usa main_window.py con esta clase.
import logging

from PySide6.QtCore import QObject, Signal, Slot

from cfdi_app import core

logger = logging.getLogger(__name__)


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
            logger.exception("Error inesperado en ProcessWorker.run")
            self.failed.emit(str(exc))
