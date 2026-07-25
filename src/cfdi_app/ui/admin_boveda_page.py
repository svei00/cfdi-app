# --- cfdi_app/ui/admin_boveda_page.py ---
"""Página "Administrador de Bóveda" (Task B3-R2, D36).

Absorbe TODO lo que antes vivía en el central widget + el QDockWidget (ya
eliminado): árbol de la bóveda, controles de proceso, barra de progreso,
visor de resultados y log. Es EL espacio de trabajo de procesamiento -
venga la carga de bóveda (VaultSidebar) o de una carpeta suelta ad-hoc
(D11), todo pasa por aquí.

Los hilos y señales de procesamiento siguen viviendo en MainWindow (regla de
oro de ui/main_window.py: ningún slot de worker abre diálogos modales); esta
clase solo construye y expone los widgets para que MainWindow los conecte.

D38(c): los atajos de teclado de periodo viven aquí (no en VaultSidebar)
porque su alcance debe ser "solo mientras el módulo está visible" -
QShortcut con contexto WidgetWithChildrenShortcut solo dispara si esta
página (o un hijo suyo) tiene el foco, lo cual es imposible mientras la
carátula está al frente (QStackedWidget oculta esta página por completo).
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton,
    QSplitter, QVBoxLayout, QWidget,
)

from cfdi_app.ui.results_view import ResultsView
from cfdi_app.ui.vault_sidebar import VaultSidebar


class AdminBovedaPage(QWidget):
    """Bóveda (izquierda) + controles/resultados/log (derecha)."""

    def __init__(self, vault_source, parent=None):
        super().__init__(parent)
        self.vault_sidebar = VaultSidebar(vault_source)
        self._shortcuts = []
        self._build_ui()
        self._build_shortcuts()

    # --- Construccion de la UI ---------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 4)
        self.home_btn = QPushButton("⌂ Inicio")
        self.home_btn.setToolTip("Volver a la carátula")
        header.addWidget(self.home_btn)
        # "Mi Bóveda" en el header/pestaña (corto, D36 ampliacion 2026-07-19:
        # "Administrador de Bóveda" era largo para un titulo de pagina). El
        # boton de la caratula que navega aqui SI conserva el nombre largo
        # descriptivo (inicio_page.py) - solo el titulo dentro del modulo cambia.
        module_title = QLabel("Mi Bóveda")
        module_title.setStyleSheet("font-weight: bold;")
        header.addWidget(module_title)
        header.addStretch(1)
        outer.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.vault_sidebar)
        splitter.addWidget(self._build_work_area())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        # Proporcion inicial sensata (la bóveda no necesita medio ancho de
        # ventana) - el usuario puede arrastrar el divisor si quiere mas.
        splitter.setSizes([300, 800])
        outer.addWidget(splitter, stretch=1)

    def _build_work_area(self):
        work_area = QWidget()
        layout = QVBoxLayout(work_area)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        folder_row = QHBoxLayout()
        self.folder_label = QLabel(
            "Usa la Bóveda (izquierda) o «Abrir XMLs sueltos…»")
        self.folder_label.setStyleSheet(
            "padding: 6px; border: 1px solid palette(mid); border-radius: 4px;")
        folder_row.addWidget(self.folder_label, stretch=1)
        # D11 ampliado 2026-07-19: el flujo ad-hoc (carpeta de XMLs fuera de
        # la boveda) vivia SOLO en el menu Archivo y el dueño no lo encontraba
        # - la tabla/arbol de la boveda son "el corazon" de esta pantalla, asi
        # que el boton para la ruta alterna vive AQUI, junto al path que
        # describe. El menu Archivo sigue teniendo la accion tambien (D11).
        self.open_loose_xml_btn = QPushButton("Abrir XMLs sueltos…")
        self.open_loose_xml_btn.setToolTip(
            "Procesar una carpeta de XMLs fuera de la bóveda")
        folder_row.addWidget(self.open_loose_xml_btn)
        layout.addLayout(folder_row)

        action_row = QHBoxLayout()
        self.process_btn = QPushButton("Procesar")
        self.save_btn = QPushButton("Guardar Excel…")
        self.open_btn = QPushButton("Abrir archivo")
        self.open_btn.setEnabled(False)
        self.open_folder_btn = QPushButton("Abrir carpeta")
        self.open_folder_btn.setEnabled(False)
        action_row.addWidget(self.process_btn)
        action_row.addWidget(self.save_btn)
        action_row.addWidget(self.open_btn)
        action_row.addWidget(self.open_folder_btn)
        layout.addLayout(action_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        layout.addWidget(QLabel("Resultados:"))
        self.results_view = ResultsView()
        layout.addWidget(self.results_view, stretch=2)

        layout.addWidget(QLabel("Registro:"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, stretch=1)

        return work_area

    # --- Atajos de periodo (D38(c)) -----------------------------------------
    def _build_shortcuts(self):
        sb = self.vault_sidebar

        def add_shortcut(sequence, handler):
            sc = QShortcut(QKeySequence(sequence), self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(handler)
            self._shortcuts.append(sc)

        for i in range(1, 7):
            add_shortcut(f"Ctrl+{i}", lambda i=i: sb.trigger_bimestre(i))
        for i in range(1, 5):
            add_shortcut(f"Ctrl+Shift+{i}", lambda i=i: sb.trigger_trimestre(i))
        for i in range(1, 3):
            add_shortcut(f"Ctrl+Alt+{i}", lambda i=i: sb.trigger_semestre(i))
        add_shortcut("Ctrl+0", sb.trigger_full_year)
        add_shortcut("F5", sb.reload)
