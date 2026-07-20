# --- cfdi_app/ui/inicio_page.py ---
"""Carátula de la app (Task B3-R2, D36).

Primera pantalla que ve el usuario: banner + botones grandes que navegan a
cada módulo. No conoce el motor de procesamiento ni el estado de la app -
solo emite `open_vault_module` cuando el usuario pide entrar al Administrador
de Bóveda; MainWindow decide qué hacer con eso (cambiar de página).

El contenido vive dentro de una "tarjeta" de ancho fijo, centrada horizontal
Y verticalmente en la ventana - un QVBoxLayout estirado a todo el ancho de
una ventana de escritorio se ve como un wireframe sin terminar, no como una
app profesional (feedback real del dueño sobre la primera versión).

D40 (anti-plagio): términos genéricos del dominio SAT se usan libremente,
pero NO se clona acomodo/iconografía/textos de MiAdminXML.
"""
import os

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QMovie, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from cfdi_app import paths

BANNER_URL = "https://excelsolutionsv.com"

CARD_MAX_WIDTH = 560

_CARD_STYLESHEET = (
    "QFrame#inicio_card {"
    "  background-color: palette(base);"
    "  border: 1px solid palette(mid);"
    "  border-radius: 12px;"
    "}"
)

_PRIMARY_BTN_STYLESHEET = (
    "QPushButton#module_btn_primary {"
    "  text-align: left; padding: 16px 20px; border-radius: 8px; border: none;"
    "  background-color: palette(highlight); color: palette(highlighted-text);"
    "  font-size: 14px; font-weight: 600;"
    "}"
    "QPushButton#module_btn_primary:hover { background-color: palette(link); }"
    "QPushButton#module_btn_primary:pressed { background-color: palette(dark); }"
)

_SECONDARY_BTN_STYLESHEET = (
    "QPushButton#module_btn_secondary {"
    "  text-align: left; padding: 16px 20px; border-radius: 8px;"
    "  border: 1px solid palette(mid); background-color: transparent;"
    "  color: palette(placeholder-text); font-size: 13px;"
    "}"
)

_BANNER_PLACEHOLDER_STYLESHEET = (
    "font-size: 13px; font-style: italic; color: palette(link); "
    "padding: 10px 16px; border: 1px solid palette(mid); border-radius: 8px; "
    "background-color: palette(alternate-base);"
)


class InicioPage(QWidget):
    """Carátula: banner clicable + botones de módulo, en una tarjeta centrada."""

    open_vault_module = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._banner_movie = None  # referencia viva mientras el QMovie corre
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self._build_card())
        row.addStretch(1)
        outer.addLayout(row)

        outer.addStretch(2)  # un poco mas de aire abajo que arriba

    def _build_card(self):
        card = QFrame()
        card.setObjectName("inicio_card")
        card.setStyleSheet(_CARD_STYLESHEET)
        card.setMaximumWidth(CARD_MAX_WIDTH)
        card.setMinimumWidth(CARD_MAX_WIDTH)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Procesador de CFDI XML → Excel")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignHCenter)
        title.setWordWrap(True)
        subtitle = QLabel(
            "Organiza tu bóveda de CFDI, procesa lotes de XML del SAT y "
            "genera reportes en Excel.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignHCenter)
        subtitle.setStyleSheet("color: palette(placeholder-text);")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addSpacing(4)
        layout.addWidget(self._build_banner())
        layout.addSpacing(10)

        self.vault_module_btn = self._build_module_button(
            "Administrador de Bóveda",
            "Organiza y procesa los CFDI de tu bóveda.",
            enabled=True, primary=True)
        self.vault_module_btn.clicked.connect(self.open_vault_module.emit)
        layout.addWidget(self.vault_module_btn)

        self.download_module_btn = self._build_module_button(
            "Descargar del SAT",
            "Próximamente: descarga automática con CIEC o e.firma.",
            enabled=False, primary=False)
        layout.addWidget(self.download_module_btn)

        self.reports_module_btn = self._build_module_button(
            "Reportes",
            "Próximamente: papeles de trabajo y reportes fiscales.",
            enabled=False, primary=False)
        layout.addWidget(self.reports_module_btn)

        return card

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
            banner.setPixmap(pixmap.scaledToWidth(
                CARD_MAX_WIDTH - 64, Qt.SmoothTransformation))
        else:
            # Zona lista para el banner real sin bloquear esta fase (D36 §2).
            banner.setText("Excel Solutions — soluciones contables")
            banner.setObjectName("banner_placeholder")
            banner.setStyleSheet(_BANNER_PLACEHOLDER_STYLESHEET)
        return banner

    def _build_module_button(self, title, tooltip, enabled, primary):
        btn = QPushButton(title)
        btn.setObjectName("module_btn_primary" if primary else "module_btn_secondary")
        btn.setStyleSheet(
            _PRIMARY_BTN_STYLESHEET if primary else _SECONDARY_BTN_STYLESHEET)
        btn.setMinimumHeight(52)
        btn.setEnabled(enabled)
        btn.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        btn.setToolTip(tooltip if enabled else f"{tooltip} (no disponible todavía)")
        return btn
