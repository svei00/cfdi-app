"""
Prueba del catalogo de claves de combustible (F2.6, ROADMAP.md Sec.13.5/D23).

Antes tenia 4 claves hardcodeadas, una de las cuales (15101501) NO existe en
el catalogo oficial c_ClaveProdServ del SAT, y le faltaban 31 claves reales
incluido el diesel (15101505).
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.constants import FUEL_PROD_SERV_CODES  # noqa: E402


class TestFuelCodes(unittest.TestCase):
    def test_has_all_35_official_codes(self):
        self.assertEqual(len(FUEL_PROD_SERV_CODES), 35)

    def test_dead_code_removed(self):
        # 15101501 no existe en el catalogo oficial c_ClaveProdServ.
        self.assertNotIn("15101501", FUEL_PROD_SERV_CODES)

    def test_diesel_code_present(self):
        self.assertIn("15101505", FUEL_PROD_SERV_CODES)

    def test_all_codes_start_with_family_1510(self):
        self.assertTrue(all(code.startswith("1510") for code in FUEL_PROD_SERV_CODES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
