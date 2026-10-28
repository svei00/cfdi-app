# --- cfdi_app/ui/desglose_dialog.py ---
"""Dialogo del reporte "Desglose de conceptos" (F2.10, diseño §3.4).

Solo recoge la eleccion del usuario (proveedor + hojas); NO escribe el Excel
ni conoce el motor: quien lo abre (main_window) le pasa los proveedores del
lote ya calculados y lee `selected_provider` / `selected_sheets` al aceptar.

El proveedor se elige en una LISTA con caja de busqueda (como los filtros del
visor): al escribir un RFC o parte de la razon social la lista se reduce sola,
sin tener que navegar ni hacer scroll. La busqueda vive en
reports/desglose_conceptos.filtrar_proveedores (logica pura).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QVBoxLayout,
)

from cfdi_app.reports import desglose_conceptos as dc

# Texto de la fila fija para "sin filtro de proveedor".
TODOS = "Todos los proveedores"


class DesgloseDialog(QDialog):
    """proveedores: [(rfc, nombre, n_cfdi)]; hojas: nombres a ofrecer (todas
    marcadas). hay_combustible=False deshabilita la hoja Combustible."""

    def __init__(self, proveedores, hojas, hay_combustible, hoja_combustible,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desglose de conceptos")
        self.setMinimumWidth(500)
        self._proveedores = list(proveedores)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel(
            "Genera un Excel con una línea por concepto de cada CFDI cargado "
            "(y, en estados de cuenta de combustible, una línea por carga)."))

        layout.addWidget(QLabel("Proveedor:"))
        self.provider_filter = QLineEdit()
        self.provider_filter.setClearButtonEnabled(True)
        self.provider_filter.setPlaceholderText(
            "Buscar por RFC o razón social…")
        self.provider_filter.textChanged.connect(self._filtrar_proveedores)
        self.provider_filter.returnPressed.connect(self._elegir_primero_visible)
        layout.addWidget(self.provider_filter)

        self.provider_list = QListWidget()
        self.provider_list.setMinimumHeight(170)
        todos = QListWidgetItem(TODOS)
        todos.setData(Qt.UserRole, None)
        self.provider_list.addItem(todos)
        for rfc, nombre, n_cfdi in self._proveedores:
            item = QListWidgetItem(f"{rfc} – {nombre} ({n_cfdi})")
            item.setData(Qt.UserRole, rfc)
            self.provider_list.addItem(item)
        self.provider_list.setCurrentRow(0)
        layout.addWidget(self.provider_list)

        self.provider_count = QLabel()
        self.provider_count.setStyleSheet("color: palette(placeholder-text);")
        layout.addWidget(self.provider_count)
        self._actualizar_conteo(len(self._proveedores))

        layout.addWidget(QLabel("Hojas a incluir:"))
        self.sheet_checks = {}
        for nombre in hojas:
            check = QCheckBox(nombre)
            check.setChecked(True)
            if nombre == hoja_combustible and not hay_combustible:
                check.setChecked(False)
                check.setEnabled(False)
                check.setToolTip("El lote no trae estados de cuenta de combustible.")
            self.sheet_checks[nombre] = check
            layout.addWidget(check)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        guardar = self.buttons.button(QDialogButtonBox.Save)
        guardar.setText("Guardar Excel…")
        # Enter en la caja de busqueda NO debe guardar: solo elige proveedor.
        guardar.setAutoDefault(False)
        self.buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        for check in self.sheet_checks.values():
            check.toggled.connect(self._update_save_enabled)
        self._update_save_enabled()

    # --- filtro de proveedor -----------------------------------------------
    def _filtrar_proveedores(self, texto):
        visibles = {p[0] for p in dc.filtrar_proveedores(self._proveedores, texto)}
        for i in range(1, self.provider_list.count()):  # la fila 0 es "Todos"
            item = self.provider_list.item(i)
            item.setHidden(item.data(Qt.UserRole) not in visibles)
        self._actualizar_conteo(len(visibles))

        actual = self.provider_list.currentItem()
        unico = next((self.provider_list.item(i)
                      for i in range(1, self.provider_list.count())
                      if not self.provider_list.item(i).isHidden()), None)
        if texto.strip() and len(visibles) == 1 and unico is not None:
            self.provider_list.setCurrentItem(unico)  # un solo resultado: elegido
        elif actual is None or actual.isHidden():
            self.provider_list.setCurrentRow(0)  # lo elegido quedo oculto: Todos

    def _elegir_primero_visible(self):
        for i in range(1, self.provider_list.count()):
            item = self.provider_list.item(i)
            if not item.isHidden():
                self.provider_list.setCurrentItem(item)
                return

    def _actualizar_conteo(self, visibles):
        total = len(self._proveedores)
        self.provider_count.setText(
            f"{visibles} de {total} proveedores"
            if visibles != total else f"{total} proveedores")

    def _update_save_enabled(self, *_):
        any_sheet = any(c.isChecked() for c in self.sheet_checks.values())
        self.buttons.button(QDialogButtonBox.Save).setEnabled(any_sheet)

    @property
    def selected_provider(self):
        """RFC del proveedor elegido, o None si son todos."""
        item = self.provider_list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    @property
    def selected_sheets(self):
        return {n for n, c in self.sheet_checks.items() if c.isChecked()}
