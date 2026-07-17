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

from cfdi_app.constants import (  # noqa: E402
    FUEL_PROD_SERV_CODES, is_combustible_concepto)


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


class TestCombustibleDetection(unittest.TestCase):
    """Regresion del falso positivo F2.8 (docs/design-f2.8-...-Task A)."""

    def test_cargas_descargas_e48_not_fuel(self):
        # El caso real: flete "CARGAS Y DESCARGAS-1TON", unidad E48, clave de
        # servicio de flete (78121601). Antes se marcaba combustible por el
        # substring "GAS" dentro de "carGAS"/"descarGAS". Ahora NO.
        self.assertFalse(is_combustible_concepto(
            "78121601", "E48", "CARGAS Y DESCARGAS-1TON"))

    def test_steel_bars_kgm_not_fuel(self):
        # Solera de acero (30102304), unidad KGM. Nunca fue combustible.
        self.assertFalse(is_combustible_concepto(
            "30102304", "KGM", "SOLERA 1/4 X 1 1/2"))

    def test_substring_gas_words_not_fuel(self):
        # Palabras que CONTIENEN "gas" como substring pero no son combustible.
        for desc in ["GASTOS DE ENVIO", "ENGASTE DE PIEDRA", "DESCARGAS ELECTRICAS"]:
            self.assertFalse(
                is_combustible_concepto("01010101", "E48", desc), desc)
            self.assertFalse(
                is_combustible_concepto("01010101", "LTR", desc), desc)

    def test_prodserv_1510_is_fuel_regardless(self):
        # Senal dura: clave de la familia 1510 -> combustible sin importar texto.
        self.assertTrue(is_combustible_concepto("15101505", "E48", "lo que sea"))
        self.assertTrue(is_combustible_concepto("15101514", "LTR", ""))

    def test_volumetric_unit_with_weak_keyword_is_fuel(self):
        # Unidad volumetrica + palabra laxa: si es combustible (respaldo).
        self.assertTrue(is_combustible_concepto("99999999", "LTR", "GAS LP"))
        self.assertTrue(is_combustible_concepto("99999999", "LTR", "COMBUSTIBLE"))
        self.assertTrue(is_combustible_concepto("99999999", "LTR", "GASOLINA MAGNA"))

    def test_e48_with_strong_keyword_is_fuel(self):
        # Gasolinera que factura con unidad de servicio E48 pero con palabra
        # inequivoca en la descripcion: SI cuenta como combustible.
        self.assertTrue(is_combustible_concepto("99999999", "E48", "GASOLINA MAGNA"))
        self.assertTrue(is_combustible_concepto("99999999", "E48", "DIESEL"))

    def test_expanded_volumetric_units_detect_fuel(self):
        # Ampliacion 2026-07-14: GLL/GLI (galon), MTQ (m3), BLL (barril) -
        # claves reales de c_ClaveUnidad, mismos importadores/mayoristas que
        # no facturan en litros.
        for unidad in ["GLL", "GLI", "MTQ", "BLL"]:
            self.assertTrue(
                is_combustible_concepto("99999999", unidad, "DIESEL"), unidad)
            self.assertTrue(
                is_combustible_concepto("99999999", unidad, "GAS LP"), unidad)

    def test_expanded_volumetric_units_still_respect_whole_word(self):
        # La ampliacion no reabre el bug original: "CARGAS" sigue sin empatar.
        for unidad in ["GLL", "GLI", "MTQ", "BLL"]:
            self.assertFalse(is_combustible_concepto(
                "78121601", unidad, "CARGAS Y DESCARGAS-1TON"), unidad)

    def test_e48_with_weak_keyword_only_is_not_fuel(self):
        # E48 + solo palabra laxa "GAS"/"COMBUSTIBLE" NO basta (evita falsos+).
        self.assertFalse(is_combustible_concepto("99999999", "E48", "GAS"))
        self.assertFalse(is_combustible_concepto("99999999", "E48", "SERVICIO COMBUSTIBLE"))

    def test_non_fuel_unit_does_not_trigger_text_heuristic(self):
        # Unidad que no es ni volumetrica ni de servicio: la heuristica de texto
        # no dispara aunque el texto traiga "GASOLINA".
        self.assertFalse(is_combustible_concepto("99999999", "KGM", "GASOLINA"))

    def test_empty_inputs_are_safe(self):
        self.assertFalse(is_combustible_concepto("", "", ""))
        self.assertFalse(is_combustible_concepto(None, None, None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
