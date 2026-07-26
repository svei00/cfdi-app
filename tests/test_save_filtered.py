"""
Pruebas de F2.7 "Guardar filtrado…" (ROADMAP.md D29/§16) a nivel MainWindow:
habilitado/deshabilitado del boton, flujo de guardado completo, y que
"Guardar Excel…" (el boton normal) siga comportandose EXACTAMENTE igual que
antes (criterio de aceptacion 5, §16.6) - esa regresion es la que este
archivo existe para prevenir.

Corre en modo offscreen (CI / entorno sin pantalla).
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PySide6.QtWidgets import QApplication  # noqa: E402

from cfdi_app import core, paths  # noqa: E402
from cfdi_app.ui.main_window import MainWindow  # noqa: E402
from cfdi_app.ui.state import AppState  # noqa: E402

FIXTURE_DIR = os.path.join(REPO_ROOT, "XML-Test")

_app = QApplication.instance() or QApplication([])


class _SaveFilteredTestCase(unittest.TestCase):
    """Arranca la ventana YA en estado DONE con un resultado real cargado -
    el punto de partida natural para probar los botones de guardado."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = {
            "BASE_APP_DIR": paths.BASE_APP_DIR,
            "BOVEDA_XML_DIR": paths.BOVEDA_XML_DIR,
            "REPORTS_DIR": paths.REPORTS_DIR,
            "LOGS_DIR": paths.LOGS_DIR,
            "LAST_USED_DIR_FILE": paths.LAST_USED_DIR_FILE,
            "ASSETS_DIR": paths.ASSETS_DIR,
        }
        paths.BASE_APP_DIR = self._tmp.name
        paths.BOVEDA_XML_DIR = os.path.join(self._tmp.name, "BovedaCFDI")
        paths.REPORTS_DIR = os.path.join(self._tmp.name, "Reports")
        paths.LOGS_DIR = os.path.join(self._tmp.name, "Logs")
        paths.LAST_USED_DIR_FILE = os.path.join(paths.REPORTS_DIR, "last.txt")
        paths.ASSETS_DIR = os.path.join(self._tmp.name, "assets_vacios")

        self.window = MainWindow()
        self.result = core.process_path(FIXTURE_DIR)
        self.window._last_result = self.result
        self.window.results_view.set_result(self.result)
        self.window._apply_state(AppState.DONE)

    def tearDown(self):
        self.window.deleteLater()
        for key, value in self._orig.items():
            setattr(paths, key, value)
        self._tmp.cleanup()


class TestSaveFilteredButtonEnablement(_SaveFilteredTestCase):
    def test_disabled_with_no_active_filter(self):
        # Criterio de aceptacion 4 (§16.6).
        self.assertFalse(self.window.save_filtered_btn.isEnabled())

    def test_enables_live_when_user_types_in_a_search_box(self):
        invoice_panel = self.window.results_view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")
        self.assertTrue(self.window.save_filtered_btn.isEnabled())

    def test_disables_again_when_query_is_cleared(self):
        invoice_panel = self.window.results_view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")
        invoice_panel.search_box.setText("")
        self.assertFalse(self.window.save_filtered_btn.isEnabled())

    def test_disabled_outside_done_state(self):
        invoice_panel = self.window.results_view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")
        self.window._apply_state(AppState.PROCESSING)
        self.assertFalse(self.window.save_filtered_btn.isEnabled())


class TestSaveFilteredFlow(_SaveFilteredTestCase):
    def test_clicking_saves_only_filtered_rows_with_derived_filename(self):
        invoice_panel = self.window.results_view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")
        expected_path = os.path.join(self._tmp.name, "salida.xlsx")

        with patch("cfdi_app.ui.main_window.QFileDialog.getSaveFileName",
                    return_value=(expected_path, "")) as mock_dialog:
            self.window.on_save_filtered_clicked()

        # El nombre PROPUESTO al dialogo debe llevar el sufijo derivado.
        proposed_path = mock_dialog.call_args[0][2]
        self.assertIn("_Filtrado_pintura", proposed_path)

        self.assertTrue(os.path.exists(expected_path))
        self.assertEqual(self.window._last_saved_path, expected_path)
        self.assertTrue(self.window.open_btn.isEnabled())
        self.assertTrue(self.window.open_folder_btn.isEnabled())

    def test_cancelling_the_dialog_does_not_save_or_change_state(self):
        invoice_panel = self.window.results_view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")

        with patch("cfdi_app.ui.main_window.QFileDialog.getSaveFileName",
                    return_value=("", "")):
            self.window.on_save_filtered_clicked()

        self.assertIsNone(self.window._last_saved_path)
        self.assertFalse(self.window.open_btn.isEnabled())

    def test_does_nothing_without_an_active_filter(self):
        # Defensivo: el boton deberia estar deshabilitado, pero si algo lo
        # dispara igual (p. ej. atajo de teclado futuro), no debe abrir dialogo.
        with patch("cfdi_app.ui.main_window.QFileDialog.getSaveFileName") as mock_dialog:
            self.window.on_save_filtered_clicked()
        mock_dialog.assert_not_called()


class TestNormalSaveIsUnaffected(_SaveFilteredTestCase):
    """Criterio de aceptacion 5 (§16.6): 'Guardar Excel…' se comporta
    EXACTAMENTE igual que antes de F2.7, filtro activo o no."""

    def test_normal_save_ignores_active_filters_and_exports_everything(self):
        invoice_panel = self.window.results_view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")  # filtro activo, a proposito
        expected_path = os.path.join(self._tmp.name, "completo.xlsx")

        with patch("cfdi_app.ui.main_window.QFileDialog.getSaveFileName",
                    return_value=(expected_path, "")):
            self.window.on_save_clicked()

        import pandas as pd
        df = pd.read_excel(expected_path, sheet_name="Invoices")
        self.assertEqual(len(df), len(self.result.invoice_data))

    def test_normal_save_button_stays_enabled_regardless_of_filters(self):
        self.assertTrue(self.window.save_btn.isEnabled())
        invoice_panel = self.window.results_view._panels["invoice_data"]
        invoice_panel.search_box.setText("pintura")
        self.assertTrue(self.window.save_btn.isEnabled())


if __name__ == "__main__":
    unittest.main(verbosity=2)
