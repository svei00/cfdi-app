# --- cfdi_app/ui/vault_move_worker.py ---
# Worker que ejecuta vault.move_vault en un hilo aparte (QThread) para no
# congelar la UI mientras se mudan potencialmente muchos archivos entre
# discos (D39). Mismo patron canonico que ui/worker.py - ver
# ROADMAP.md Sec.6.3 para las conexiones que usa main_window.py con esta clase.
import logging

from PySide6.QtCore import QObject, Signal, Slot

from cfdi_app import vault

logger = logging.getLogger(__name__)


class VaultMoveWorker(QObject):
    """Mueve la boveda completa (current_root) dentro de dest_parent."""

    log = Signal(str)
    progress = Signal(int, int, str)   # actual, total, nombre de la carpeta RFC
    finished = Signal(str)             # ruta nueva de la boveda
    failed = Signal(str)

    def __init__(self, current_root, dest_parent):
        super().__init__()
        self.current_root = current_root
        self.dest_parent = dest_parent

    @Slot()
    def run(self):
        try:
            new_root = vault.move_vault(
                self.current_root, self.dest_parent,
                on_progress=lambda c, t, n: self.progress.emit(c, t, n),
                on_log=self.log.emit,
            )
            self.finished.emit(new_root)
        except Exception as exc:  # red de seguridad: nunca matar el hilo en silencio
            logger.exception("Error inesperado en VaultMoveWorker.run")
            self.failed.emit(str(exc))
