# --- cfdi_app/__main__.py ---
# Punto de entrada de la GUI: `python -m cfdi_app` o `pythonw -m cfdi_app`.
import sys

from PySide6.QtWidgets import QApplication

from cfdi_app import log_setup
from cfdi_app.ui.main_window import APP_TITLE, MainWindow


def main():
    log_setup.setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
