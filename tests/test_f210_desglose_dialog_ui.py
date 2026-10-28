"""
Pruebas de UI del dialogo "Desglose de conceptos" (F2.10): filtro de proveedor
por RFC o razon social. Se OMITEN si PySide6 no carga (contenedor sin libEGL);
en la maquina del dueño corren normales.
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

from cfdi_app.exporters import desglose_exporter as dx  # noqa: E402
from cfdi_app.ui.desglose_dialog import DesgloseDialog  # noqa: E402

PROVS = [("ASE930924SS7", "EDENRED MEXICO", 5),
         ("WMT970714R10", "NUEVA WAL MART DE MÉXICO", 12),
         ("HDM001017AS1", "HOME DEPOT MEXICO", 3)]

_app = QApplication.instance() or QApplication([])


class TestFiltroDeProveedorEnElDialogo(unittest.TestCase):
    def setUp(self):
        self.dialog = DesgloseDialog(
            PROVS, dx.HOJAS_DISPONIBLES, True, dx.HOJA_COMBUSTIBLE)

    def tearDown(self):
        self.dialog.close()

    def _visibles(self):
        lista = self.dialog.provider_list
        return [lista.item(i).data(0x0100) for i in range(lista.count())
                if not lista.item(i).isHidden()]  # 0x0100 = Qt.UserRole

    def test_por_defecto_son_todos_los_proveedores(self):
        self.assertIsNone(self.dialog.selected_provider)
        self.assertEqual(len(self._visibles()), 4)  # Todos + 3

    def test_escribir_reduce_la_lista_y_elige_el_unico_resultado(self):
        self.dialog.provider_filter.setText("depot")
        self.assertEqual(self._visibles(), [None, "HDM001017AS1"])
        self.assertEqual(self.dialog.selected_provider, "HDM001017AS1")

    def test_busca_por_rfc(self):
        self.dialog.provider_filter.setText("wmt97")
        self.assertEqual(self.dialog.selected_provider, "WMT970714R10")

    def test_varios_resultados_no_eligen_en_silencio(self):
        self.dialog.provider_filter.setText("mexico")
        self.assertEqual(len(self._visibles()), 4)  # Todos + 3 coinciden
        self.assertIsNone(self.dialog.selected_provider)

    def test_si_lo_elegido_queda_oculto_se_regresa_a_todos(self):
        self.dialog.provider_filter.setText("depot")      # elige Home Depot
        self.dialog.provider_filter.setText("edenred")    # lo oculta
        self.assertEqual(self.dialog.selected_provider, "ASE930924SS7")
        self.dialog.provider_filter.setText("zzz")        # nadie coincide
        self.assertIsNone(self.dialog.selected_provider)

    def test_enter_elige_el_primer_visible(self):
        self.dialog.provider_filter.setText("mexico")
        self.dialog.provider_filter.returnPressed.emit()
        self.assertEqual(self.dialog.selected_provider, "ASE930924SS7")

    def test_borrar_el_filtro_muestra_todos_otra_vez(self):
        self.dialog.provider_filter.setText("depot")
        self.dialog.provider_filter.clear()
        self.assertEqual(len(self._visibles()), 4)
        self.assertEqual(self.dialog.selected_provider, "HDM001017AS1")

    def test_enter_en_la_caja_no_cierra_ni_guarda(self):
        self.assertFalse(
            self.dialog.buttons.button(self.dialog.buttons.Save).autoDefault())


if __name__ == "__main__":
    unittest.main()
