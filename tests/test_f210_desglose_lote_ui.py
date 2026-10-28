"""
Pruebas de UI del visor "Desglose del lote" (F2.10, arbol RFC -> factura ->
conceptos con filtro). Se OMITEN si PySide6 no se puede cargar (p. ej. un
contenedor sin libEGL); en la maquina del dueño corren normales.
"""
import glob
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

from cfdi_app.parsers.xml_parser_40 import parse_cfdi_40_invoice  # noqa: E402
from cfdi_app.reports import desglose_conceptos as dc  # noqa: E402
from cfdi_app.ui.desglose_lote_dialog import DesgloseLoteDialog  # noqa: E402

EDENRED_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "edenred")
UUID_JUNIO = "3358E192-7DAB-45A3-AEBE-30EADA074BDC"

_app = QApplication.instance() or QApplication([])


def _lineas():
    registros = [parse_cfdi_40_invoice(f)
                 for f in sorted(glob.glob(os.path.join(EDENRED_DIR, "*.xml")))]
    return dc.aplanar_lote(registros)


class TestDesgloseLoteDialog(unittest.TestCase):
    def setUp(self):
        self.lineas = _lineas()
        self.dialog = DesgloseLoteDialog(self.lineas)

    def tearDown(self):
        self.dialog.close()

    def _buscar(self, texto):
        self.dialog.search_box.setText(texto)
        self.dialog._aplicar_filtro()  # sin esperar el retraso del temporizador

    def _factura(self, uuid):
        prov = self.dialog.tree.topLevelItem(0)
        for i in range(prov.childCount()):
            item = prov.child(i)
            if uuid in item.text(0):
                return item
        self.fail(f"no hay nodo de factura para {uuid}")

    def test_sin_filtro_un_proveedor_con_sus_cinco_facturas(self):
        self.assertEqual(self.dialog.tree.topLevelItemCount(), 1)
        prov = self.dialog.tree.topLevelItem(0)
        self.assertIn("ASE930924SS7", prov.text(0))
        self.assertEqual(prov.childCount(), 5)

    def test_las_lineas_se_crean_al_expandir_la_factura(self):
        item = self._factura(UUID_JUNIO)
        self.assertEqual(item.childCount(), 1)  # solo el marcador
        item.setExpanded(True)
        self.assertEqual(item.childCount(), 34)  # comision + 33 cargas

    def test_el_filtro_deja_solo_la_factura_y_la_linea_que_la_contienen(self):
        self._buscar("omc100818gz7")  # RFC de una estacion
        self.assertEqual(len(self.dialog.visible_lines), 1)
        prov = self.dialog.tree.topLevelItem(0)
        self.assertEqual(prov.childCount(), 1)
        factura = prov.child(0)
        self.assertIn("TCGE-000004231229", factura.text(0))
        self.assertTrue(factura.isExpanded())  # con filtro se expande todo
        self.assertEqual(factura.childCount(), 1)
        self.assertIn("OMC100818GZ7", factura.child(0).text(0))

    def test_resumen_y_boton_de_exportar_siguen_al_filtro(self):
        self._buscar("magna")
        self.assertIn(f"de {len(self.lineas)} líneas", self.dialog.summary_label.text())
        self.assertTrue(self.dialog.export_btn.isEnabled())
        self._buscar("tornillo")
        self.assertEqual(self.dialog.tree.topLevelItemCount(), 0)
        self.assertFalse(self.dialog.export_btn.isEnabled())

    def test_doble_clic_en_una_factura_pide_su_desglose(self):
        recibidos = []
        self.dialog.desglose_requested.connect(recibidos.append)
        self.dialog._on_double_click(self._factura(UUID_JUNIO), 0)
        self.assertEqual(recibidos, [UUID_JUNIO])

    def test_doble_clic_en_el_proveedor_no_pide_nada(self):
        recibidos = []
        self.dialog.desglose_requested.connect(recibidos.append)
        self.dialog._on_double_click(self.dialog.tree.topLevelItem(0), 0)
        self.assertEqual(recibidos, [])

    def test_exportar_deja_las_lineas_visibles_y_el_texto_buscado(self):
        self._buscar("magna")
        self.dialog.export_btn.click()
        self.assertTrue(self.dialog.wants_export)
        self.assertEqual(self.dialog.query, "magna")
        self.assertTrue(all(l["descripcion"] == "Magna"
                            for l in self.dialog.visible_lines))


if __name__ == "__main__":
    unittest.main()
