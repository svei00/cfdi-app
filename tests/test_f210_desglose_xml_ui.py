"""
Pruebas de UI de F2.10 etapa 3: menu contextual "Ver desglose de este XML" y
dialogo DesgloseXmlDialog. Se OMITEN si PySide6 no se puede cargar (por
ejemplo un contenedor sin libEGL); en la maquina del dueño corren normales.
"""
import glob
import os
import sys
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication, QDialog
except ImportError as exc:  # pragma: no cover - depende del entorno
    raise unittest.SkipTest(f"PySide6 no disponible: {exc}")

from cfdi_app.parsers.xml_parser_40 import parse_cfdi_40_invoice  # noqa: E402
from cfdi_app.reports import desglose_conceptos as dc  # noqa: E402
from cfdi_app.ui.desglose_xml_dialog import DesgloseXmlDialog  # noqa: E402
from cfdi_app.ui.results_view import ResultsView  # noqa: E402

EDENRED_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "edenred")
UUID_JUNIO = "3358E192-7DAB-45A3-AEBE-30EADA074BDC"

_app = QApplication.instance() or QApplication([])


def _registros():
    return [parse_cfdi_40_invoice(f)
            for f in sorted(glob.glob(os.path.join(EDENRED_DIR, "*.xml")))]


class TestDesgloseXmlDialog(unittest.TestCase):
    def setUp(self):
        registros = [r for r in _registros() if r["UUID"] == UUID_JUNIO]
        self.lineas = dc.aplanar_lote(registros)
        self.dialog = DesgloseXmlDialog(self.lineas, dc.cuadre(registros)[0])

    def test_una_fila_por_linea(self):
        self.assertEqual(self.dialog.table.rowCount(), 34)

    def test_encabezados_incluyen_columnas_de_combustible(self):
        encabezados = [self.dialog.table.horizontalHeaderItem(j).text()
                       for j in range(self.dialog.table.columnCount())]
        self.assertIn("Tarjeta", encabezados)

    def test_semaforo_de_cuadre_ok(self):
        self.assertTrue(self.dialog.cuadre_label.text().startswith("Cuadre: OK"))

    def test_exportar_cierra_aceptando_y_marca_la_bandera(self):
        self.assertFalse(self.dialog.wants_export)
        self.dialog.export_btn.click()
        self.assertTrue(self.dialog.wants_export)
        self.assertEqual(self.dialog.result(), QDialog.Accepted)

    def test_cerrar_no_pide_exportar(self):
        self.dialog.reject()
        self.assertFalse(self.dialog.wants_export)


class TestMenuContextualFacturas(unittest.TestCase):
    def setUp(self):
        self.registros = _registros()
        self.view = ResultsView()
        self.view.set_result(SimpleNamespace(
            invoice_data=self.registros, nomina_data=[], pagos_data=[]))
        self.panel = self.view._panels["invoice_data"]
        self.view.resize(1200, 600)
        self.view.show()
        _app.processEvents()

    def tearDown(self):
        self.view.close()

    def test_registro_bajo_el_cursor_da_su_uuid(self):
        index = self.panel.proxy.index(0, 0)
        pos = self.panel.table.visualRect(index).center()
        record = self.panel._record_at_pos(pos)
        self.assertIsNotNone(record)
        esperado = self.panel.model.record_at(self.panel.proxy.mapToSource(index).row())
        self.assertEqual(record["UUID"], esperado["UUID"])

    def test_clic_fuera_de_las_filas_no_da_registro(self):
        self.assertIsNone(self.panel._record_at_pos(QPoint(-50, -50)))

    def test_la_senal_del_panel_llega_al_visor(self):
        recibidos = []
        self.view.desglose_requested.connect(recibidos.append)
        self.panel.desglose_requested.emit(UUID_JUNIO)
        self.assertEqual(recibidos, [UUID_JUNIO])


if __name__ == "__main__":
    unittest.main()
