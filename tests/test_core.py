"""
Pruebas del pipeline core (carpeta -> parseo -> resultado).

Verifican que core.process_path recorra los fixtures de XML-Test, los clasifique
por tipo y produzca un nombre de archivo coherente, SIN abrir ninguna UI.

Ejecutar con:
    python -m unittest discover -s tests
"""
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app import core  # noqa: E402

FIXTURE_DIR = os.path.join(REPO_ROOT, "XML-Test")


class TestProcessPath(unittest.TestCase):
    def setUp(self):
        self.result = core.process_path(FIXTURE_DIR)

    def test_produces_data(self):
        self.assertTrue(self.result.has_data)
        self.assertGreater(self.result.processed_count, 0)

    def test_records_split_into_known_buckets(self):
        # Cada registro parseado debe caer en invoice, nomina o pago.
        total_buckets = (
            len(self.result.invoice_data)
            + len(self.result.nomina_data)
            + len(self.result.pagos_data)
        )
        self.assertEqual(total_buckets, len(self.result.all_parsed_data))

    def test_fixtures_include_invoice_and_nomina(self):
        # Los fixtures actuales (4.0) traen Facturas y Nomina.
        self.assertTrue(self.result.invoice_data, "Se esperaban Facturas en los fixtures.")
        self.assertTrue(self.result.nomina_data, "Se esperaba Nomina en los fixtures.")

    def test_default_filename_shape(self):
        name = core.build_default_filename(self.result.all_parsed_data)
        self.assertTrue(name.endswith(".xlsx"))
        # Formato {RFC}_{Tipo}_{Fecha}.xlsx -> al menos dos separadores '_'.
        self.assertGreaterEqual(name.count("_"), 2)

    def test_no_errors_on_clean_fixtures(self):
        self.assertEqual(self.result.errors, [])
        self.assertEqual(self.result.error_count, 0)


class TestProcessPathInvalid(unittest.TestCase):
    def test_invalid_path_returns_empty_result(self):
        result = core.process_path(os.path.join(REPO_ROOT, "no_such_dir_xyz"))
        self.assertFalse(result.has_data)
        self.assertEqual(result.processed_count, 0)


class TestProcessPathErrorsPerFile(unittest.TestCase):
    """ROADMAP.md Sec.6.5/6.9: los errores deben quedar listados por archivo,
    no solo contados. Antes de F2, parse_xml_file_by_version devolvia None sin
    registrar la causa."""

    def test_corrupt_xml_is_listed_with_reason(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_path = os.path.join(tmp_dir, "corrupto.xml")
            with open(bad_path, "w", encoding="utf-8") as f:
                f.write("<Comprobante Version='4.0'><SinCerrar>")

            result = core.process_path(tmp_dir)

            self.assertFalse(result.has_data)
            self.assertEqual(result.error_count, 1)
            self.assertEqual(len(result.errors), 1)
            label, reason = result.errors[0]
            self.assertEqual(label, bad_path)
            self.assertIn("malformado", reason.lower())

    def test_unsupported_version_is_listed_with_reason(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            xml_path = os.path.join(tmp_dir, "no_soportado.xml")
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write('<Comprobante Version="1.0" TipoDeComprobante="I"/>')

            result = core.process_path(tmp_dir)

            self.assertFalse(result.has_data)
            self.assertEqual(result.error_count, 1)
            label, reason = result.errors[0]
            self.assertEqual(label, xml_path)
            self.assertIn("no soportado", reason.lower())

    def test_corrupt_zip_does_not_crash_the_whole_run(self):
        """Un .zip danado ya no debe tumbar todo process_path (defecto previo:
        BadZipFile se propagaba sin control)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_zip = os.path.join(tmp_dir, "corrupto.zip")
            with open(bad_zip, "wb") as f:
                f.write(b"esto no es un zip valido")

            result = core.process_path(tmp_dir)  # no debe lanzar excepcion

            self.assertEqual(result.error_count, 1)
            label, reason = result.errors[0]
            self.assertEqual(label, "corrupto.zip")
            self.assertIn("zip", reason.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
