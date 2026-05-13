"""
Pruebas basicas (smoke tests) para los parsers de CFDI.

Objetivo de Step 0: una red de seguridad ANTES de construir la GUI.
Si la GUI (u otro cambio) rompe un parser, estas pruebas lo detectan
de inmediato, separando "bug del parser" de "bug de la GUI".

Se ejecutan SIN dependencias extra:
    python -m unittest discover -s tests

Las pruebas reflejan la logica de despacho real de
main.parse_xml_file_by_version, pero importan los parsers directamente
para no acoplar las pruebas a Tkinter / la UI.

NOTA DE COBERTURA: los fixtures en XML-Test/ son todos CFDI 4.0
(Invoice y Nomina). Aun NO hay fixtures de CFDI 3.3 ni de Pagos 2.0,
asi que esos parsers no estan cubiertos. Agregar fixtures cuando se
tengan XMLs de muestra (anonimizados) de esas variantes.
"""
import os
import sys
import unittest
import xml.etree.ElementTree as ET

# Permitir importar los modulos del parser que viven en la raiz del repo.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from xml_parser_40 import parse_cfdi_40_invoice  # noqa: E402
from xml_parser_33 import parse_cfdi_33_invoice  # noqa: E402
from pagos_parser_20 import parse_cfdi_pago_20    # noqa: E402

FIXTURE_DIR = os.path.join(REPO_ROOT, "XML-Test")


def dispatch(xml_file_path):
    """Replica main.parse_xml_file_by_version sin importar la UI."""
    root = ET.parse(xml_file_path).getroot()
    version = root.get("Version")
    tipo = root.get("TipoDeComprobante")
    if tipo == "P" and version == "4.0":
        return parse_cfdi_pago_20(xml_file_path)
    if version == "3.3":
        return parse_cfdi_33_invoice(xml_file_path)
    if version == "4.0":
        return parse_cfdi_40_invoice(xml_file_path)
    return None


def all_fixtures():
    return [
        os.path.join(FIXTURE_DIR, f)
        for f in os.listdir(FIXTURE_DIR)
        if f.lower().endswith(".xml")
    ]


class TestFixturesPresent(unittest.TestCase):
    def test_fixture_directory_has_xmls(self):
        self.assertTrue(
            all_fixtures(),
            "No se encontraron XMLs en XML-Test/ - se necesitan fixtures para probar.",
        )


class TestCfdi40Parsing(unittest.TestCase):
    """Cada fixture 4.0 debe parsear a un registro coherente."""

    def setUp(self):
        self.fixtures = all_fixtures()

    def test_every_fixture_parses_without_error(self):
        for path in self.fixtures:
            with self.subTest(fixture=os.path.basename(path)):
                result = dispatch(path)
                self.assertIsNotNone(
                    result, f"El parser devolvio None para {os.path.basename(path)}"
                )

    def test_invoice_and_nomina_have_expected_shape(self):
        for path in self.fixtures:
            root = ET.parse(path).getroot()
            if root.get("Version") != "4.0" or root.get("TipoDeComprobante") == "P":
                continue
            with self.subTest(fixture=os.path.basename(path)):
                data = parse_cfdi_40_invoice(path)
                self.assertIsInstance(data, dict)
                self.assertEqual(data.get("Version"), "4.0")
                self.assertIn(
                    data.get("CFDI_Type"),
                    {"Invoice", "Nomina"},
                    "CFDI_Type debe ser 'Invoice' o 'Nomina'",
                )
                self.assertTrue(
                    data.get("UUID"),
                    "Todo CFDI timbrado debe tener UUID (TimbreFiscalDigital).",
                )

    def test_nomina_fixtures_classified_as_nomina(self):
        """Un XML con el complemento nomina12:Nomina debe clasificarse como Nomina."""
        ns_marker = "{http://www.sat.gob.mx/nomina12}Nomina"
        for path in self.fixtures:
            tree = ET.parse(path)
            has_nomina = any(el.tag == ns_marker for el in tree.iter())
            if not has_nomina:
                continue
            with self.subTest(fixture=os.path.basename(path)):
                data = parse_cfdi_40_invoice(path)
                self.assertEqual(
                    data.get("CFDI_Type"),
                    "Nomina",
                    "Un CFDI con complemento de nomina debe clasificarse como 'Nomina'.",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
