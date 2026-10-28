"""
Pruebas de UI de la pagina Reportes (F2.10): el boton de Desglose NUNCA queda
deshabilitado y, sin lote, muestra un aviso visible. Se OMITEN si PySide6 no
carga (contenedor sin libEGL); en la maquina del dueño corren normales.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - depende del entorno
    raise unittest.SkipTest(f"PySide6 no disponible: {exc}")

from cfdi_app.ui.reportes_page import ReportesPage  # noqa: E402

_app = QApplication.instance() or QApplication([])


class TestReportesDesglose(unittest.TestCase):
    def setUp(self):
        self.page = ReportesPage()

    def test_sin_lote_el_boton_sigue_activo_y_hay_aviso_visible(self):
        self.page.set_desglose_available(False)
        self.assertTrue(self.page.desglose_btn.isEnabled())
        self.assertFalse(self.page.desglose_hint.isHidden())
        self.assertIn("Administrador de Bóveda", self.page.desglose_hint.text())

    def test_con_lote_el_aviso_desaparece(self):
        self.page.set_desglose_available(True)
        self.assertTrue(self.page.desglose_btn.isEnabled())
        self.assertTrue(self.page.desglose_hint.isHidden())

    def test_con_ultimo_periodo_recordado_el_aviso_lo_nombra(self):
        self.page.set_desglose_available(
            False, ultimo_periodo="GOOH841231EPA · Recibidas · 2026-06")
        self.assertFalse(self.page.desglose_hint.isHidden())
        self.assertIn("GOOH841231EPA · Recibidas · 2026-06",
                      self.page.desglose_hint.text())
        self.assertIn("cargarlo", self.page.desglose_hint.text())

    def test_mientras_carga_avisa_que_el_desglose_se_abrira_solo(self):
        self.page.set_desglose_available(
            False, cargando=True, ultimo_periodo="algo")
        self.assertIn("Cargando", self.page.desglose_hint.text())
        self.assertTrue(self.page.desglose_btn.isEnabled())

    def test_pulsar_sin_lote_emite_la_señal_para_que_la_ventana_avise(self):
        recibidas = []
        self.page.open_desglose.connect(lambda: recibidas.append(1))
        self.page.set_desglose_available(False)
        self.page.desglose_btn.click()
        self.assertEqual(recibidas, [1])


if __name__ == "__main__":
    unittest.main()
