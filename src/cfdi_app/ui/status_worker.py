# --- cfdi_app/ui/status_worker.py ---
# Worker que verifica el estatus SAT del lote en un hilo aparte (mismo patron
# canonico que ProcessWorker, ROADMAP Sec.6.3). Jamas abre dialogos.
import logging
import os

from PySide6.QtCore import QObject, Signal, Slot

from cfdi_app import paths, sat_status

logger = logging.getLogger(__name__)

CACHE_FILE_NAME = "sat_status_cache.sqlite"


class StatusWorker(QObject):
    progress = Signal(int, int)    # hechos, total
    finished = Signal(object)      # dict resumen de sat_status.verify_records
    failed = Signal(str)

    def __init__(self, records, force=False):
        super().__init__()
        self.records = records
        self.force = force

    @Slot()
    def run(self):
        try:
            cache = sat_status.StatusCache(os.path.join(
                paths.BASE_APP_DIR, CACHE_FILE_NAME))
            resumen = sat_status.verify_records(
                self.records, cache, force=self.force,
                on_progress=lambda hechos, total: self.progress.emit(hechos, total))
            self.finished.emit(resumen)
        except Exception as exc:  # red de seguridad: nunca matar el hilo en silencio
            logger.exception("Error inesperado en StatusWorker.run")
            self.failed.emit(str(exc))
