# --- cfdi_app/ui/reportes_page.py ---
"""Página "Reportes" (B3-R2, ampliación 2026-07-19).

Hoy la app YA genera archivos Excel (el botón "Guardar Excel…" del módulo).
Antes esta opción de la carátula estaba muerta ("próximamente"), ignorando
esos archivos que ya existen. Ahora es una página real con dos cosas:

1. Un botón que abre la carpeta donde caen los reportes Excel
   (`Documents\\CFDI-Processor\\Reports` por defecto - es UNA sola carpeta,
   no se separa por Emitidas/Recibidas; ahí aterrizan todos).
2. El módulo fiscal de "papeles de trabajo" (F2.8), que sí sigue pendiente,
   como entrada deshabilitada honesta - no se esconde, se anuncia.

No conoce el motor ni el estado de la app; solo emite `open_reports_folder`
(clic directo del usuario → abrir carpeta es legítimo) y `go_home`.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

_CARD_STYLESHEET = (
    "QFrame#reportes_card {"
    "  background-color: palette(base);"
    "  border: 1px solid palette(mid);"
    "  border-radius: 12px;"
    "}"
)

_PRIMARY_BTN_STYLESHEET = (
    "QPushButton#reportes_btn_primary {"
    "  text-align: left; padding: 16px 20px; border-radius: 8px; border: none;"
    "  background-color: palette(highlight); color: palette(highlighted-text);"
    "  font-size: 14px; font-weight: 600;"
    "}"
    "QPushButton#reportes_btn_primary:hover { background-color: palette(link); }"
)

_ACTION_BTN_STYLESHEET = (
    "QPushButton#reportes_btn_desglose {"
    "  text-align: left; padding: 16px 20px; border-radius: 8px;"
    "  border: 1px solid palette(highlight); background-color: transparent;"
    "  font-size: 14px; font-weight: 600;"
    "}"
    "QPushButton#reportes_btn_desglose:hover { background-color: palette(alternate-base); }"
    "QPushButton#reportes_btn_desglose:disabled {"
    "  border: 1px solid palette(mid); color: palette(placeholder-text);"
    "}"
)

_SECONDARY_BTN_STYLESHEET = (
    "QPushButton#reportes_btn_secondary {"
    "  text-align: left; padding: 16px 20px; border-radius: 8px;"
    "  border: 1px solid palette(mid); background-color: transparent;"
    "  color: palette(placeholder-text); font-size: 13px;"
    "}"
)


class ReportesPage(QWidget):
    """Carátula de reportes: abrir carpeta de Excel + papeles de trabajo."""

    open_reports_folder = Signal()
    open_desglose = Signal()
    go_home = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        header = QHBoxLayout()
        self.home_btn = QPushButton("⌂ Inicio")
        self.home_btn.setToolTip("Volver a la carátula")
        self.home_btn.clicked.connect(self.go_home.emit)
        header.addWidget(self.home_btn)
        header.addStretch(1)
        outer.addLayout(header)

        outer.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self._build_card())
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(2)

    def set_desglose_available(self, available, cargando=False,
                               ultimo_periodo=""):
        """Refleja el estado del lote en la pagina. El boton NUNCA se
        deshabilita: un boton gris que no explica nada parece roto. Sin lote,
        un aviso visible dice que hacer (y, si hay un periodo recordado, que
        se cargara al pulsar)."""
        self.desglose_btn.setEnabled(True)
        self.desglose_btn.setToolTip(
            "Excel con una línea por concepto de cada CFDI del lote: por "
            "proveedor, mes, ejercicio y concepto, con hoja de IVA")
        if available:
            texto = ""
        elif cargando:
            texto = ("Cargando el periodo… en cuanto termine se abre el "
                     "desglose.")
        elif ultimo_periodo:
            texto = (f"Sin periodo cargado. Último usado: {ultimo_periodo}. "
                     "Al pulsar el botón te ofrezco cargarlo.")
        else:
            texto = ("Primero carga y procesa un periodo en el Administrador "
                     "de Bóveda; después vuelve aquí.")
        self.desglose_hint.setText(texto)
        self.desglose_hint.setVisible(bool(texto))

    def _build_card(self):
        card = QFrame()
        card.setObjectName("reportes_card")
        card.setStyleSheet(_CARD_STYLESHEET)
        card.setMaximumWidth(560)
        card.setMinimumWidth(560)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Reportes")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignHCenter)
        subtitle = QLabel(
            "Aquí encuentras los archivos de Excel que has generado, el "
            "desglose de conceptos y, próximamente, los papeles de trabajo "
            "fiscales.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignHCenter)
        subtitle.setStyleSheet("color: palette(placeholder-text);")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        self.open_folder_btn = QPushButton("Abrir carpeta de reportes Excel")
        self.open_folder_btn.setObjectName("reportes_btn_primary")
        self.open_folder_btn.setStyleSheet(_PRIMARY_BTN_STYLESHEET)
        self.open_folder_btn.setMinimumHeight(52)
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.setToolTip(
            "Abre la carpeta donde se guardan tus archivos de Excel")
        self.open_folder_btn.clicked.connect(self.open_reports_folder.emit)
        layout.addWidget(self.open_folder_btn)

        self.desglose_btn = QPushButton("Desglose de conceptos…")
        self.desglose_btn.setObjectName("reportes_btn_desglose")
        self.desglose_btn.setStyleSheet(_ACTION_BTN_STYLESHEET)
        self.desglose_btn.setMinimumHeight(52)
        self.desglose_btn.setCursor(Qt.PointingHandCursor)
        self.desglose_btn.clicked.connect(self.open_desglose.emit)
        layout.addWidget(self.desglose_btn)

        self.desglose_hint = QLabel(
            "Primero carga y procesa un periodo en el Administrador de "
            "Bóveda; después vuelve aquí.")
        self.desglose_hint.setWordWrap(True)
        self.desglose_hint.setStyleSheet(
            "color: palette(placeholder-text); padding-left: 4px;")
        layout.addWidget(self.desglose_hint)
        self.set_desglose_available(False)

        self.work_papers_btn = QPushButton("Papeles de trabajo y reportes fiscales")
        self.work_papers_btn.setObjectName("reportes_btn_secondary")
        self.work_papers_btn.setStyleSheet(_SECONDARY_BTN_STYLESHEET)
        self.work_papers_btn.setMinimumHeight(52)
        self.work_papers_btn.setEnabled(False)
        self.work_papers_btn.setToolTip(
            "Papeles de trabajo PUE/PPD/REP — disponible en una fase futura")
        layout.addWidget(self.work_papers_btn)

        return card
