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

    def test_vertical_header_stays_sequential_after_sorting(self):
        # Bug reportado por el dueno: al ordenar, el numero de fila quedaba
        # "pegado" a la posicion ORIGINAL (comportamiento por defecto de
        # QSortFilterProxyModel) en vez de mostrar 1..N en el orden visual.
        self.proxy.sort(2, Qt.AscendingOrder)  # columna "Total": 100.0, luego 5000.0
        headers = [
            self.proxy.headerData(row, Qt.Vertical, Qt.DisplayRole)
            for row in range(self.proxy.rowCount())
        ]
        self.assertEqual(headers, ["1", "2"])


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

    def test_can_filter_invoices_by_uso_cfdi(self):
        # A peticion del dueno (2026-07-05): UsoCFDI (p.ej. D10 = colegiaturas)
        # ya era columna visible en Facturas pero no era buscable.
        self.view.set_result(self.result)
        invoice_panel = self.view._panels["invoice_data"]
        invoice_panel.search_box.setText("D10")
        self.assertEqual(invoice_panel.proxy.rowCount(), 1)

    def test_can_filter_invoices_by_metodo_de_pago(self):
        self.view.set_result(self.result)
        invoice_panel = self.view._panels["invoice_data"]
        invoice_panel.search_box.setText("PUE")
        self.assertGreater(invoice_panel.proxy.rowCount(), 0)
        self.assertLess(invoice_panel.proxy.rowCount(), len(self.result.invoice_data))


class TestResultsViewFilteredExport(unittest.TestCase):
    """F2.7 (ROADMAP.md D29/§16): exportacion filtrada "espejo del visor"."""

    def setUp(self):
        self.result = core.process_path(FIXTURE_DIR)
        self.view = ResultsView()
        self.view.set_result(self.result)

    def test_no_active_filter_reports_false(self):
        self.assertFalse(self.view.has_any_active_filter())
        self.assertEqual(self.view.active_filter_info(), [])

    def test_typing_in_one_tab_is_detected_as_active(self):
        self.view._panels["invoice_data"].search_box.setText("pintura")
        self.assertTrue(self.view.has_any_active_filter())
        self.assertEqual(self.view.active_filter_info(), [("invoice_data", "pintura")])

    def test_whitespace_only_query_does_not_count_as_active(self):
        self.view._panels["invoice_data"].search_box.setText("   ")
        self.assertFalse(self.view.has_any_active_filter())

    def test_filter_changed_signal_emits_on_text_change(self):
        received = []
        self.view.filter_changed.connect(lambda: received.append(True))
        self.view._panels["invoice_data"].search_box.setText("pintura")
        self.assertTrue(received)

    def test_filtered_tab_is_trimmed_unfiltered_tabs_stay_complete(self):
        # §16.2: cada hoja segun SU PROPIO filtro - Facturas recortada,
        # Nomina/Pagos completas al no tener filtro activo.
        self.view._panels["invoice_data"].search_box.setText("pintura")
        data = self.view.filtered_data()
        self.assertLess(len(data["invoice_data"]), len(self.result.invoice_data))
        self.assertEqual(len(data["nomina_data"]), len(self.result.nomina_data))
        self.assertEqual(len(data["pagos_data"]), len(self.result.pagos_data))

    def test_exported_rows_are_identical_to_what_the_proxy_shows(self):
        # §16.5, criterio duro: exportado == visible, misma cantidad y
        # mismos registros (no solo el conteo).
        invoice_panel = self.view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")

        visible_via_proxy = [
            invoice_panel.model.record_at(invoice_panel.proxy.mapToSource(
                invoice_panel.proxy.index(row, 0)).row())
            for row in range(invoice_panel.proxy.rowCount())
        ]
        exported = self.view.filtered_data()["invoice_data"]

        self.assertEqual(len(exported), len(visible_via_proxy))
        self.assertCountEqual(exported, visible_via_proxy)

    def test_no_filter_active_export_matches_full_dataset(self):
        # Degradacion natural (§16.2): sin filtro, exportado == completo.
        data = self.view.filtered_data()
        self.assertEqual(data["invoice_data"], self.result.invoice_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
