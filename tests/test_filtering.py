"""
Pruebas del filtro incremental del visor (ROADMAP.md D15).

cfdi_app.ui.filtering es logica pura (sin Qt) - se prueba igual que cualquier
funcion normal, sin necesitar una QApplication ni una ventana.
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.ui.filtering import matches_search, filter_records, compute_totals  # noqa: E402

TEXT_FIELDS = ["RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
              "Factura", "UUID", "Conceptos"]
AMOUNT_FIELDS = {"total": "Total", "subtotal": "SubTotal"}
DEFAULT_AMOUNT_FIELD = "Total"

SAMPLE_RECORDS = [
    {"RFC Emisor": "AAA010101AAA", "Nombre Emisor": "Constructora del Norte",
     "RFC Receptor": "BBB020202BBB", "Nombre Receptor": "Cliente Uno",
     "Factura": "A-100", "UUID": "AAAA1111-...", "Conceptos": "Venta de tela azul",
     "SubTotal": 1500.0, "Total": 1740.0},
    {"RFC Emisor": "CCC030303CCC", "Nombre Emisor": "Papeleria del Sur",
     "RFC Receptor": "BBB020202BBB", "Nombre Receptor": "Cliente Uno",
     "Factura": "B-200", "UUID": "BBBB2222-...", "Conceptos": "Hojas y engrapadoras",
     "SubTotal": 2500.0, "Total": 2900.0},
    {"RFC Emisor": "DDD040404DDD", "Nombre Emisor": "Ferreteria Central",
     "RFC Receptor": "EEE050505EEE", "Nombre Receptor": "Cliente Dos",
     "Factura": "C-300", "UUID": "CCCC3333-...", "Conceptos": "Cemento gris CPC 30R",
     "SubTotal": 500.0, "Total": 580.0},
]


def _search(query, records=SAMPLE_RECORDS):
    return filter_records(records, query, TEXT_FIELDS, AMOUNT_FIELDS, DEFAULT_AMOUNT_FIELD)


class TestEmptyQuery(unittest.TestCase):
    def test_empty_or_blank_matches_everything(self):
        self.assertEqual(len(_search("")), 3)
        self.assertEqual(len(_search("   ")), 3)


class TestTextSearch(unittest.TestCase):
    def test_matches_by_concepto(self):
        # Caso real pedido por el dueno: buscar "tela" sin saber RFC/nombre.
        result = _search("tela")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Factura"], "A-100")

    def test_matches_by_nombre_emisor_case_insensitive(self):
        result = _search("papeleria")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Factura"], "B-200")

    def test_matches_by_rfc_receptor_shared_by_two_records(self):
        result = _search("BBB020202BBB")
        self.assertEqual(len(result), 2)

    def test_no_match_returns_empty(self):
        self.assertEqual(_search("no existe esto en nada"), [])


class TestAmountFilterDefaultsToTotal(unittest.TestCase):
    """D15: sin nombre de campo, el operador aplica sobre Total (no Subtotal)."""

    def test_less_than_total_default(self):
        # Totales: A-100=1740, B-200=2900, C-300=580 -> <2000 excluye solo B-200.
        result = _search("<2000")
        self.assertEqual({r["Factura"] for r in result}, {"A-100", "C-300"})

    def test_greater_than_total_default(self):
        result = _search(">2000")
        self.assertEqual({r["Factura"] for r in result}, {"B-200"})

    def test_greater_or_equal(self):
        result = _search(">=1740")
        self.assertEqual({r["Factura"] for r in result}, {"A-100", "B-200"})

    def test_less_or_equal(self):
        result = _search("<=580")
        self.assertEqual({r["Factura"] for r in result}, {"C-300"})


class TestAmountFilterExplicitField(unittest.TestCase):
    def test_subtotal_alias_overrides_default(self):
        # Con "subtotal<600" solo debe calificar el registro de Subtotal 500.
        result = _search("subtotal<600")
        self.assertEqual({r["Factura"] for r in result}, {"C-300"})

    def test_unknown_field_alias_degrades_to_text_search(self):
        # "montoraro<2000" no es un alias conocido -> se trata como texto
        # literal (no debe crashear ni matchear nada por accidente).
        result = _search("montoraro<2000")
        self.assertEqual(result, [])


class TestComputeTotals(unittest.TestCase):
    def test_sums_all_records(self):
        totals = compute_totals(SAMPLE_RECORDS, AMOUNT_FIELDS)
        self.assertAlmostEqual(totals["Total"], 1740.0 + 2900.0 + 580.0)
        self.assertAlmostEqual(totals["SubTotal"], 1500.0 + 2500.0 + 500.0)

    def test_sums_only_filtered_subset(self):
        visible = _search("<2000")  # A-100 (1740) + C-300 (580)
        totals = compute_totals(visible, AMOUNT_FIELDS)
        self.assertAlmostEqual(totals["Total"], 1740.0 + 580.0)

    def test_empty_records_gives_zero(self):
        totals = compute_totals([], AMOUNT_FIELDS)
        self.assertEqual(totals["Total"], 0.0)
        self.assertEqual(totals["SubTotal"], 0.0)

    def test_missing_or_non_numeric_field_counts_as_zero(self):
        records = [{"Total": "no-es-numero"}, {"Total": None}, {}]
        totals = compute_totals(records, {"total": "Total"})
        self.assertEqual(totals["Total"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
