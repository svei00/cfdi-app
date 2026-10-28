"""
Pruebas de F2.10 etapa 1 (docs/design-f2.10-desglose-conceptos.md, D49):
captura del complemento EstadoDeCuentaCombustible 1.2 en el parser 4.0.

Fixtures: tests/fixtures/edenred/ (XML reales de Edenred, ANONIMIZADOS). No
viven en XML-Test/ porque core.process_path recorre esa carpeta completa y
cambiaria los conteos de las demas pruebas.
"""
import os
import sys
import unittest
from decimal import Decimal

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.parsers.xml_parser_40 import parse_cfdi_40_invoice  # noqa: E402
from cfdi_app.constants import INTERNAL_ONLY_FIELDS  # noqa: E402

EDENRED_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "edenred")
XML_TEST_DIR = os.path.join(REPO_ROOT, "XML-Test")

ECC_JUNIO = os.path.join(
    EDENRED_DIR, "3358E192-7DAB-45A3-AEBE-30EADA074BDC.xml")
ECC_AGOSTO = os.path.join(
    EDENRED_DIR, "46613D69-8126-672B-547F-3F98CD5132A6.xml")
TELEPEAJE = os.path.join(
    EDENRED_DIR, "29D10416-3337-404A-BF21-8488E8BC522D.xml")
TAG_CERO = os.path.join(
    EDENRED_DIR, "57A56A0B-7D60-490C-B92E-073D80B706C0.xml")


def _suma(lineas, campo):
    return sum((Decimal(l[campo]) for l in lineas), Decimal("0"))


def _suma_iva(lineas):
    return sum((Decimal(t["Importe"]) for l in lineas
                for t in l["Traslados"] if t["Impuesto"] == "IVA"),
               Decimal("0"))


class TestEccJunio(unittest.TestCase):
    """UUID 3358E192 (jun-2026): 33 cargas, cuadra al centavo con el SAT."""

    @classmethod
    def setUpClass(cls):
        cls.data = parse_cfdi_40_invoice(ECC_JUNIO)
        cls.ecc = cls.data["EstadoCuentaCombustible"]

    def test_encabezado_del_complemento(self):
        self.assertEqual(self.ecc["Version"], "1.2")
        self.assertEqual(self.ecc["TipoOperacion"], "Tarjeta")
        self.assertEqual(self.ecc["SubTotal"], "24393.77")
        self.assertEqual(self.ecc["Total"], "28185.69")

    def test_33_cargas(self):
        self.assertEqual(len(self.ecc["Conceptos"]), 33)

    def test_importe_iva_y_litros_cuadran_con_lo_declarado(self):
        lineas = self.ecc["Conceptos"]
        self.assertEqual(_suma(lineas, "Importe"), Decimal("24393.77"))
        self.assertEqual(_suma_iva(lineas), Decimal("3791.92"))
        self.assertEqual(_suma(lineas, "Cantidad"), Decimal("1127.97"))
        self.assertEqual(
            _suma(lineas, "Importe") + _suma_iva(lineas),
            Decimal(self.ecc["Total"]))

    def test_campos_de_una_carga(self):
        carga = next(l for l in self.ecc["Conceptos"]
                     if l["FolioOperacion"] == "543884498")
        self.assertEqual(carga["Fecha"], "2026-06-24T08:19:17")
        self.assertEqual(carga["Rfc"], "OMC100818GZ7")
        self.assertEqual(carga["ClaveEstacion"], "11990")
        self.assertEqual(carga["TipoCombustible"], "1")
        self.assertEqual(carga["NombreCombustible"], "Magna")
        self.assertEqual(carga["Unidad"], "01")
        self.assertEqual(carga["Cantidad"], "60.27")
        self.assertEqual(carga["ValorUnitario"], "20.763")
        self.assertEqual(carga["Importe"], "1251.39")
        self.assertEqual(carga["Traslados"], [
            {"Impuesto": "IVA", "TasaOCuota": "0.160000", "Importe": "194.49"}])

    def test_cinco_tarjetas_anonimizadas_y_consistentes(self):
        tarjetas = {l["Identificador"] for l in self.ecc["Conceptos"]}
        self.assertEqual(len(tarjetas), 5)
        for t in tarjetas:
            self.assertTrue(t.startswith("999900000000"), t)

    def test_el_concepto_del_cfdi_sigue_siendo_solo_la_comision(self):
        # La columna plana no cambia: la gasolina NO se mezcla en ella.
        self.assertEqual(self.data["Conceptos"], "COMISION SOBRE PEDIDOS")
        self.assertEqual(len(self.data["ConceptosDetalle"]), 1)
        self.assertAlmostEqual(self.data["Total"], 1078.80)
        self.assertEqual(self.data["Combustible"], "No")


class TestEccAgosto(unittest.TestCase):
    """UUID 46613D69 (ago-2026): mismo TipoCombustible con nombres de marca."""

    @classmethod
    def setUpClass(cls):
        cls.ecc = parse_cfdi_40_invoice(ECC_AGOSTO)["EstadoCuentaCombustible"]

    def test_37_cargas_y_totales(self):
        lineas = self.ecc["Conceptos"]
        self.assertEqual(len(lineas), 37)
        self.assertEqual(_suma(lineas, "Importe"), Decimal("35005.60"))
        self.assertEqual(_suma_iva(lineas), Decimal("5441.49"))
        self.assertEqual(_suma(lineas, "Cantidad"), Decimal("1603.79"))

    def test_magna_y_bp_regu_comparten_tipo_combustible(self):
        # Por eso el reporte agrupa por TipoCombustible y no por el nombre.
        tipo_1 = {l["NombreCombustible"] for l in self.ecc["Conceptos"]
                  if l["TipoCombustible"] == "1"}
        tipo_2 = {l["NombreCombustible"] for l in self.ecc["Conceptos"]
                  if l["TipoCombustible"] == "2"}
        self.assertEqual(tipo_1, {"Magna", "BP REGU"})
        self.assertEqual(tipo_2, {"Premium", "BP PREM"})


class TestSinComplemento(unittest.TestCase):
    """Regresion D11: sin el complemento nada cambia y el campo vale None."""

    def test_telepeaje_y_tag_no_traen_complemento(self):
        for ruta in (TELEPEAJE, TAG_CERO):
            with self.subTest(ruta=os.path.basename(ruta)):
                data = parse_cfdi_40_invoice(ruta)
                self.assertIn("EstadoCuentaCombustible", data)
                self.assertIsNone(data["EstadoCuentaCombustible"])

    def test_todos_los_fixtures_de_xml_test_dan_none(self):
        revisados = 0
        for nombre in sorted(os.listdir(XML_TEST_DIR)):
            if not nombre.lower().endswith(".xml"):
                continue
            data = parse_cfdi_40_invoice(os.path.join(XML_TEST_DIR, nombre))
            if data is None:  # fixtures que no son CFDI 4.0
                continue
            revisados += 1
            with self.subTest(xml=nombre):
                self.assertIsNone(data["EstadoCuentaCombustible"])
        self.assertGreater(revisados, 0)

    def test_telepeaje_conserva_su_concepto(self):
        data = parse_cfdi_40_invoice(TELEPEAJE)
        self.assertEqual(data["Conceptos"], "MOVIMIENTOS TELEPEAJE")
        self.assertEqual(data["ConceptosDetalle"][0]["Cantidad"], "37.00")

    def test_tag_con_descuento_total_cero_no_truena(self):
        data = parse_cfdi_40_invoice(TAG_CERO)
        self.assertAlmostEqual(data["Total"], 0.0)
        self.assertEqual(data["ConceptosDetalle"][0]["Descuento"], "1884.00")


class TestCampoInterno(unittest.TestCase):
    def test_esta_declarado_como_interno(self):
        # Asi core.py y excel_exporter.py lo excluyen de columnas y Excel.
        self.assertIn("EstadoCuentaCombustible", INTERNAL_ONLY_FIELDS)


if __name__ == "__main__":
    unittest.main()
