# --- cfdi_app/log_setup.py ---
# Logging centralizado (ver ROADMAP.md Sec.6.7).
#
# RotatingFileHandler en Documents/CFDI-Processor/Logs/cfdi-app.log +
# sys.excepthook global. Con pythonw.exe no hay consola visible: este archivo
# es el UNICO lugar donde ver que paso si algo truena al arrancar o durante
# la ejecucion (Bug 2 del ROADMAP: pythonw descarta stdout/stderr).
import logging
import logging.handlers
import os
import sys

from cfdi_app import paths

_LOG_FILE_NAME = "cfdi-app.log"
_configured = False


def log_file_path():
    return os.path.join(paths.LOGS_DIR, _LOG_FILE_NAME)


def setup_logging(level=logging.INFO):
    """Configura el logger raiz de la app. Seguro de llamar mas de una vez."""
    global _configured
    if _configured:
        return
    _configured = True

    paths.create_initial_directories()

    handler = logging.handlers.RotatingFileHandler(
        log_file_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)

    sys.excepthook = _make_excepthook(root)
    root.info("Logging inicializado. Archivo: %s", log_file_path())


def _make_excepthook(logger):
    def _excepthook(exc_type, exc_value, exc_tb):
        logger.critical(
            "Excepcion no capturada", exc_info=(exc_type, exc_value, exc_tb))
        _try_show_crash_dialog(exc_value)
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    return _excepthook


def _try_show_crash_dialog(exc_value):
    """Muestra un dialogo de error si hay una QApplication viva.

    Con pythonw no hay consola: sin esto, un crash seria completamente
    silencioso para el usuario (solo quedaria en el log).
    """
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        return
    app = QApplication.instance()
    if app is None:
        return
    QMessageBox.critical(
        None, "Error inesperado",
        f"Ocurrio un error inesperado:\n{exc_value}\n\n"
        f"Revisa el registro para mas detalle:\n{log_file_path()}")
