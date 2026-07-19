# --- cfdi_app/ui/inicio_page.py ---
"""Carátula de la app (Task B3-R2, D36).

Primera pantalla que ve el usuario: banner + botones grandes que navegan a
cada módulo. No conoce el motor de procesamiento ni el estado de la app -
solo emite `open_vault_module` cuando el usuario pide entrar al Administrador
de Bóveda; MainWindow decide qué hacer con eso (cambiar de página).

D40 (anti-plagio): términos genéricos del dominio SAT se usan libremente,
pero NO se clona acomodo/iconografía/textos de MiAdminXML.
"""
import os

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QMovie, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from cfdi_app import paths

BANNER_URL = "https://excelsolutionsv.com"


class InicioPage(QWidget):
    """Carátula: banner clicable + botones de módulo."""

    open_vault_module = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._banner_movie = None  # referencia viva mientras el QMovie corre
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Procesador de CFDI XML → Excel")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignHCenter)
        subtitle = QLabel(
            "Organiza tu bóveda de CFDI, procesa lotes de XML del SAT y "
            "genera reportes en Excel.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignHCenter)
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(self._build_banner())
        layout.addSpacing(12)

        self.vault_module_btn = self._build_module_button(
            "Administrador de Bóveda",
            "Organiza y procesa los CFDI de tu bóveda.",
            enabled=True)
        self.vault_module_btn.clicked.connect(self.open_vault_module.emit)
        layout.addWidget(self.vault_module_btn)

        self.download_module_btn = self._build_module_button(
            "Descargar del SAT",
            "Próximamente: descarga automática con CIEC o e.firma.",
            enabled=False)
        layout.addWidget(self.download_module_btn)

        self.reports_module_btn = self._build_module_button(
            "Reportes",
            "Próximamente: papeles de trabajo y reportes fiscales.",
            enabled=False)
        layout.addWidget(self.reports_module_btn)

        layout.addStretch(1)

    def _build_banner(self):
        banner = QLabel()
        banner.setObjectName("banner")
        banner.setAlignment(Qt.AlignHCenter)
        banner.setCursor(Qt.PointingHandCursor)
        banner.mousePressEvent = lambda _event: QDesktopServices.openUrl(QUrl(BANNER_URL))

        gif_path = os.path.join(paths.ASSETS_DIR, "banner.gif")
        png_path = os.path.join(paths.ASSETS_DIR, "banner.png")
        if os.path.isfile(gif_path):
            movie = QMovie(gif_path)
            banner.setMovie(movie)
            movie.start()
            self._banner_movie = movie
        elif os.path.isfile(png_path):
            pixmap = QPixmap(png_path)
            banner.setPixmap(pixmap.scaledToWidth(400, Qt.SmoothTransformation))
        else:
            # Zona lista para el banner real sin bloquear esta fase (D36 §2).
            banner.setText("Excel Solutions — soluciones contables")
            banner.setObjectName("banner_placeholder")
            banner.setStyleSheet(
                "font-size: 14px; font-style: italic; color: palette(link); "
                "padding: 24px; border: 1px dashed palette(mid); border-radius: 6px;")
        return banner

    def _build_module_button(self, title, tooltip, enabled):
        btn = QPushButton(title)
        btn.setMinimumHeight(48)
        btn.setEnabled(enabled)
        btn.setToolTip(tooltip if enabled else f"{tooltip} (no disponible todavía)")
        return btn
