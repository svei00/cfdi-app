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

    def __init__(self, folders):
        super().__init__()
        # `folders` puede ser una carpeta (str, flujo "Abrir carpeta" ad-hoc) o
        # una lista de carpetas (flujo de la boveda B3). Ambos alimentan el
        # MISMO motor de core.
        self.folders = folders

    @Slot()
    def run(self):
        try:
            if isinstance(self.folders, (list, tuple)):
                result = core.process_paths(
                    list(self.folders),
                    on_log=self.log.emit,
                    on_progress=lambda c, t, n: self.progress.emit(c, t, n),
                )
            else:
                result = core.process_path(
                    self.folders,
                    on_log=self.log.emit,
                    on_progress=lambda c, t, n: self.progress.emit(c, t, n),
                )
            self.finished.emit(result)
        except Exception as exc:  # red de seguridad: nunca matar el hilo en silencio
            logger.exception("Error inesperado en ProcessWorker.run")
            self.failed.emit(str(exc))
