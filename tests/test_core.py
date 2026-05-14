"""
Pruebas del pipeline core (carpeta -> parseo -> resultado).

Verifican que core.process_path recorra los fixtures de XML-Test, los clasifique
por tipo y produzca un nombre de archivo coherente, SIN abrir ninguna UI.

Ejecutar con:
    python -m unittest discover -s tests
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import core  # noqa: E402

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


class TestProcessPathInvalid(unittest.TestCase):
    def test_invalid_path_returns_empty_result(self):
        result = core.process_path(os.path.join(REPO_ROOT, "no_such_dir_xyz"))
        self.assertFalse(result.has_data)
        self.assertEqual(result.processed_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
