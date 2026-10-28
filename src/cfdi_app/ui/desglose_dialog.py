# --- cfdi_app/ui/desglose_dialog.py ---
"""Dialogo del reporte "Desglose de conceptos" (F2.10, diseño §3.4).

Solo recoge la eleccion del usuario (proveedor + hojas); NO escribe el Excel
ni conoce el motor: quien lo abre (main_window) le pasa los proveedores del
lote ya calculados y lee `selected_provider` / `selected_sheets` al aceptar.
"""
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout,
)

# Texto del combo para "sin filtro de proveedor".
TODOS = "Todos los proveedores"


class DesgloseDialog(QDialog):
    """proveedores: [(rfc, nombre, n_cfdi)]; hojas: nombres a ofrecer (todas
    marcadas). hay_combustible=False deshabilita la hoja Combustible."""

    def __init__(self, proveedores, hojas, hay_combustible, hoja_combustible,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desglose de conceptos")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel(
            "Genera un Excel con una línea por concepto de cada CFDI cargado "
            "(y, en estados de cuenta de combustible, una línea por carga)."))

        layout.addWidget(QLabel("Proveedor:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem(TODOS, None)
        for rfc, nombre, n_cfdi in proveedores:
            self.provider_combo.addItem(f"{rfc} – {nombre} ({n_cfdi})", rfc)
        layout.addWidget(self.provider_combo)

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
        self.buttons.button(QDialogButtonBox.Save).setText("Guardar Excel…")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        for check in self.sheet_checks.values():
            check.toggled.connect(self._update_save_enabled)
        self._update_save_enabled()

    def _update_save_enabled(self, *_):
        any_sheet = any(c.isChecked() for c in self.sheet_checks.values())
        self.buttons.button(QDialogButtonBox.Save).setEnabled(any_sheet)

    @property
    def selected_provider(self):
        """RFC del proveedor elegido, o None si son todos."""
        return self.provider_combo.currentData()

    @property
    def selected_sheets(self):
        return {n for n, c in self.sheet_checks.items() if c.isChecked()}
