# --- cfdi_app/ui/results_view.py ---
# Widget del "Visor de resultados" (ROADMAP.md Sec.11 / D13 / D15).
#
# Autocontenido a proposito (ver Sec.5.3 del ROADMAP): no conoce MainWindow,
# solo recibe un core.ProcessResult via set_result(). Esto permite colgarlo
# despues de un shell/dashboard sin reescribirlo, y que F4 conecte un modelo
# respaldado en SQLite a la MISMA vista para el modo historial.
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QTableView, QTabWidget, QVBoxLayout, QWidget,
)

from cfdi_app.ui import filtering
from cfdi_app.ui.results_model import RecordTableModel
from cfdi_app.ui.results_proxy import RecordFilterProxyModel


@dataclass(frozen=True)
class TabConfig:
    key: str              # "invoice_data" / "nomina_data" / "pagos_data" en ProcessResult
    title: str
    display_columns: list
    text_fields: list
    amount_fields: dict    # alias en minusculas -> clave real, para "campo<numero"
    default_amount_field: str  # clave real usada cuando no se nombra campo
    total_columns: list    # claves reales a sumar en la fila de totales


INVOICE_TAB = TabConfig(
    key="invoice_data",
    title="Facturas",
    display_columns=["Factura", "RFC Emisor", "Nombre Emisor", "RFC Receptor",
                     "Nombre Receptor", "Fecha Emision", "SubTotal", "Descuento",
                     "IVA 16%", "Total", "UUID"],
    text_fields=["RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
                "Factura", "UUID", "Conceptos"],
    amount_fields={"total": "Total", "subtotal": "SubTotal", "descuento": "Descuento",
                  "iva": "IVA 16%"},
    default_amount_field="Total",
    total_columns=["SubTotal", "Descuento", "IVA 16%", "Total"],
)

NOMINA_TAB = TabConfig(
    key="nomina_data",
    title="Nómina",
    display_columns=["Factura", "RFC Emisor", "Nombre Emisor", "RFC Receptor",
                     "Nombre Receptor", "Fecha Emision", "SubTotal",
                     "Total Deducciones", "Total", "UUID"],
    text_fields=["RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
                "Factura", "UUID", "Conceptos"],
    amount_fields={"total": "Total", "subtotal": "SubTotal",
                  "deducciones": "Total Deducciones"},
    default_amount_field="Total",
    total_columns=["SubTotal", "Total Deducciones", "Total"],
)

PAGOS_TAB = TabConfig(
    key="pagos_data",
    title="Pagos",
    display_columns=["Serie CFDI", "Folio CFDI", "RFC Emisor CFDI", "Nombre Emisor CFDI",
                     "RFC Receptor CFDI", "Nombre Receptor CFDI", "FechaPago",
                     "MontoTotalPagos", "UUID CFDI"],
    text_fields=["RFC Emisor CFDI", "Nombre Emisor CFDI", "RFC Receptor CFDI",
                "Nombre Receptor CFDI", "Serie CFDI", "Folio CFDI", "UUID CFDI"],
    amount_fields={"total": "MontoTotalPagos", "monto": "Monto Pago"},
    default_amount_field="MontoTotalPagos",
    total_columns=["MontoTotalPagos"],
)

ALL_TABS = [INVOICE_TAB, NOMINA_TAB, PAGOS_TAB]


class _ResultsTabPanel(QWidget):
    """Una pestaña: caja de busqueda + tabla + fila de totales."""

    def __init__(self, config: TabConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._records = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Buscar por RFC, nombre, folio, UUID, concepto...  o  <2000 / total>=5000")
        self.search_box.textChanged.connect(self._on_query_changed)
        layout.addWidget(self.search_box)

        self.model = RecordTableModel([], config.display_columns)
        self.proxy = RecordFilterProxyModel(
            config.text_fields, config.amount_fields, config.default_amount_field)
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, stretch=1)

        self.totals_label = QLabel()
        self.totals_label.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self.totals_label)

        self._update_totals_label()

    def set_records(self, records):
        self._records = records
        self.model = RecordTableModel(records, self.config.display_columns)
        self.proxy.setSourceModel(self.model)
        self._update_totals_label()

    def _on_query_changed(self, text):
        self.proxy.set_query(text)
        self._update_totals_label()

    def _update_totals_label(self):
        query = self.search_box.text()
        visible = filtering.filter_records(
            self._records, query, self.config.text_fields,
            self.config.amount_fields, self.config.default_amount_field)
        totals = filtering.compute_totals(visible, {c: c for c in self.config.total_columns})
        parts = [f"{col}: ${totals[col]:,.2f}" for col in self.config.total_columns]
        count_part = f"{len(visible)} de {len(self._records)} registro(s)"
        self.totals_label.setText(f"{count_part}   —   " + "   ".join(parts))


class ResultsView(QTabWidget):
    """Visor de resultados: una pestaña por tipo de documento (D13/D15)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panels = {}
        for config in ALL_TABS:
            panel = _ResultsTabPanel(config)
            self._panels[config.key] = panel
            self.addTab(panel, config.title)

    def set_result(self, result):
        """Puebla las 3 pestañas a partir de un core.ProcessResult (o None para vaciar)."""
        for config in ALL_TABS:
            records = getattr(result, config.key, []) if result is not None else []
            self._panels[config.key].set_records(records)

    def clear(self):
        self.set_result(None)
