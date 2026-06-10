"""
Pruebas del visor de resultados (ROADMAP.md D13/D15/Sec.11): modelo Qt,
proxy de filtrado y el widget ResultsView completo.

Corre en modo offscreen si no hay pantalla disponible (CI / este entorno de
desarrollo); en la maquina real de Windows usa la normal si ya esta definida.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from cfdi_app import core  # noqa: E402
from cfdi_app.ui.results_model import RecordTableModel  # noqa: E402
from cfdi_app.ui.results_proxy import RecordFilterProxyModel  # noqa: E402
from cfdi_app.ui.results_view import ResultsView  # noqa: E402

FIXTURE_DIR = os.path.join(REPO_ROOT, "XML-Test")

_app = QApplication.instance() or QApplication([])


class TestRecordTableModel(unittest.TestCase):
    def setUp(self):
        self.records = [
            {"RFC Emisor": "AAA010101AAA", "Total": 1234.5},
            {"RFC Emisor": "BBB020202BBB", "Total": None},
        ]
        self.columns = ["RFC Emisor", "Total"]
        self.model = RecordTableModel(self.records, self.columns)

    def test_row_and_column_count(self):
        self.assertEqual(self.model.rowCount(), 2)
        self.assertEqual(self.model.columnCount(), 2)

    def test_float_is_formatted_with_thousands_and_two_decimals(self):
        index = self.model.index(0, 1)
        self.assertEqual(self.model.data(index), "1,234.50")

    def test_missing_value_renders_as_empty_string(self):
        index = self.model.index(1, 1)
        self.assertEqual(self.model.data(index), "")

    def test_header_data_shows_column_names(self):
        self.assertEqual(self.model.headerData(0, Qt.Horizontal), "RFC Emisor")

    def test_record_at_returns_original_dict(self):
        self.assertEqual(self.model.record_at(0), self.records[0])


class TestRecordFilterProxyModel(unittest.TestCase):
    def setUp(self):
        self.records = [
            {"RFC Emisor": "AAA010101AAA", "Conceptos": "Venta de tela", "Total": 100.0},
            {"RFC Emisor": "BBB020202BBB", "Conceptos": "Papeleria", "Total": 5000.0},
        ]
        self.model = RecordTableModel(self.records, ["RFC Emisor", "Conceptos", "Total"])
        self.proxy = RecordFilterProxyModel(
            text_fields=["RFC Emisor", "Conceptos"],
            amount_fields={"total": "Total"},
            default_amount_field="Total",
        )
        self.proxy.setSourceModel(self.model)

    def test_no_query_shows_all_rows(self):
        self.assertEqual(self.proxy.rowCount(), 2)

    def test_text_query_filters_rows(self):
        self.proxy.set_query("tela")
        self.assertEqual(self.proxy.rowCount(), 1)

    def test_amount_query_filters_rows(self):
        self.proxy.set_query(">1000")
        self.assertEqual(self.proxy.rowCount(), 1)


class TestResultsView(unittest.TestCase):
    def setUp(self):
        self.result = core.process_path(FIXTURE_DIR)
        self.view = ResultsView()

    def test_set_result_populates_invoice_and_nomina_tabs(self):
        self.view.set_result(self.result)
        invoice_panel = self.view._panels["invoice_data"]
        nomina_panel = self.view._panels["nomina_data"]
        self.assertEqual(invoice_panel.model.rowCount(), len(self.result.invoice_data))
        self.assertEqual(nomina_panel.model.rowCount(), len(self.result.nomina_data))

    def test_filtering_by_concepto_updates_totals_label(self):
        self.view.set_result(self.result)
        invoice_panel = self.view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")
        self.assertIn("de 8 registro(s)", invoice_panel.totals_label.text())
        self.assertLess(invoice_panel.proxy.rowCount(), len(self.result.invoice_data))

    def test_clear_empties_all_tabs(self):
        self.view.set_result(self.result)
        self.view.clear()
        for panel in self.view._panels.values():
            self.assertEqual(panel.model.rowCount(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
