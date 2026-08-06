"""
Pruebas de F2.9 "Exportar pestaña a CSV..." (ROADMAP.md D43-D45/§18).

Cubre tres capas: csv_exporter.export_rows_to_csv (formato de archivo),
core.build_csv_filename/full_columns_for_tab (nombre y columnas), y
core.export_tab_csv (costura). La capa de ResultsView.active_tab_export_data
se prueba en test_results_view.py; el flujo end-to-end de MainWindow en
test_save_filtered.py.

Cubre criterios de aceptacion §18.7: 3 (columnas visor vs todas), 4 (ida y
vuelta con coma en concepto), 5 (BOM + LF).
"""
import csv
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app import core  # noqa: E402
from cfdi_app.exporters.csv_exporter import export_rows_to_csv  # noqa: E402


class TestExportRowsToCsv(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = os.path.join(self._tmp.name, "salida.csv")

    def tearDown(self):
        self._tmp.cleanup()

    def test_writes_header_and_rows_in_column_order(self):
        rows = [{"RFC Emisor": "AAA010101AAA", "Total": 1160.0}]
        export_rows_to_csv(rows, ["RFC Emisor", "Total"], self.out)
        with open(self.out, encoding="utf-8-sig", newline="") as f:
            reader = list(csv.reader(f))
        self.assertEqual(reader[0], ["RFC Emisor", "Total"])
        self.assertEqual(reader[1], ["AAA010101AAA", "1160.0"])

    def test_extra_fields_not_in_columns_are_ignored(self):
        rows = [{"RFC Emisor": "AAA010101AAA", "ConceptosDetalle": [{"x": 1}]}]
        export_rows_to_csv(rows, ["RFC Emisor"], self.out)  # no debe lanzar
        with open(self.out, encoding="utf-8-sig") as f:
            content = f.read()
        self.assertNotIn("ConceptosDetalle", content)

    def test_missing_field_in_a_row_writes_empty_cell(self):
        rows = [{"RFC Emisor": "AAA010101AAA"}]  # sin "Total"
        export_rows_to_csv(rows, ["RFC Emisor", "Total"], self.out)
        with open(self.out, encoding="utf-8-sig", newline="") as f:
            reader = list(csv.reader(f))
        self.assertEqual(reader[1], ["AAA010101AAA", ""])

    def test_comma_in_field_survives_round_trip(self):
        # Criterio §18.7.4: los conceptos CFDI SI traen comas.
        original = "PINTURA DE 4 PLATAFORMAS, LIMPIEZA Y RETIRO DE ESCOMBROS"
        rows = [{"Conceptos": original}]
        export_rows_to_csv(rows, ["Conceptos"], self.out)
        with open(self.out, encoding="utf-8-sig", newline="") as f:
            reader = list(csv.DictReader(f))
        self.assertEqual(reader[0]["Conceptos"], original)

    def test_file_has_utf8_bom(self):
        # Criterio §18.7.5: Excel en Windows necesita el BOM para acentos/ñ.
        export_rows_to_csv([{"Nombre": "José Peña"}], ["Nombre"], self.out)
        with open(self.out, "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))

    def test_accented_characters_round_trip_correctly(self):
        export_rows_to_csv([{"Nombre": "José María Peña Ñuñez"}], ["Nombre"], self.out)
        with open(self.out, encoding="utf-8-sig", newline="") as f:
            reader = list(csv.DictReader(f))
        self.assertEqual(reader[0]["Nombre"], "José María Peña Ñuñez")

    def test_lines_end_with_lf_not_crlf(self):
        # Criterio §18.7.5: LF explicito, no CRLF (default del modulo csv).
        export_rows_to_csv(
            [{"A": "1"}, {"A": "2"}], ["A"], self.out)
        with open(self.out, "rb") as f:
            raw = f.read()
        self.assertNotIn(b"\r\n", raw)
        self.assertIn(b"\n", raw)

    def test_empty_rows_still_writes_header(self):
        export_rows_to_csv([], ["RFC Emisor", "Total"], self.out)
        with open(self.out, encoding="utf-8-sig", newline="") as f:
            reader = list(csv.reader(f))
        self.assertEqual(reader, [["RFC Emisor", "Total"]])

    def test_creates_missing_output_directory(self):
        nested = os.path.join(self._tmp.name, "sub", "carpeta", "salida.csv")
        export_rows_to_csv([{"A": "1"}], ["A"], nested)
        self.assertTrue(os.path.exists(nested))


class TestFullColumnsForTab(unittest.TestCase):
    def test_invoice_uses_the_fixed_excel_order(self):
        cols = core.full_columns_for_tab("invoice_data", [])
        self.assertNotIn("CFDI_Type", cols)
        self.assertIn("Factura", cols)
        self.assertGreater(len(cols), 40)  # las 70 del Excel completo

    def test_pagos_uses_the_fixed_excel_order(self):
        cols = core.full_columns_for_tab("pagos_data", [])
        self.assertNotIn("CFDI_Type", cols)
        self.assertGreater(len(cols), 40)

    def test_nomina_derives_columns_from_rows_first_seen_order(self):
        rows = [
            {"CFDI_Type": "Nomina", "RFC Emisor": "A", "Total": 100.0,
             "ConceptosDetalle": [{}]},
            {"CFDI_Type": "Nomina", "RFC Emisor": "A", "Total": 200.0, "NSS": "123"},
        ]
        cols = core.full_columns_for_tab("nomina_data", rows)
        self.assertEqual(cols, ["RFC Emisor", "Total", "NSS"])
        self.assertNotIn("CFDI_Type", cols)
        self.assertNotIn("ConceptosDetalle", cols)

    def test_nomina_with_no_rows_returns_empty_list(self):
        self.assertEqual(core.full_columns_for_tab("nomina_data", []), [])


class TestBuildCsvFilename(unittest.TestCase):
    def setUp(self):
        self.result = core.process_path(os.path.join(REPO_ROOT, "XML-Test"))
        self.parsed = self.result.all_parsed_data

    def test_includes_tab_title_and_csv_extension(self):
        name = core.build_csv_filename(self.parsed, "Facturas", "")
        self.assertTrue(name.endswith(".csv"))
        self.assertIn("_Facturas", name)
        self.assertNotIn("_Filtrado", name)

    def test_includes_filter_suffix_when_query_present(self):
        # Criterio §18.7.1: nombre con pestaña + sufijo de filtro.
        name = core.build_csv_filename(self.parsed, "Facturas", "tela")
        self.assertTrue(name.endswith("_Facturas_Filtrado_tela.csv"))

    def test_tab_title_with_accent_is_sanitized(self):
        name = core.build_csv_filename(self.parsed, "Nómina", "")
        self.assertIn("_Nomina", name)  # sin acento en el nombre de archivo


class TestExportTabCsv(unittest.TestCase):
    def test_writes_only_the_given_rows_and_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "salida.csv")
            core.export_tab_csv(
                [{"RFC Emisor": "AAA010101AAA", "Total": 1160.0, "Extra": "x"}],
                ["RFC Emisor", "Total"], out)
            with open(out, encoding="utf-8-sig", newline="") as f:
                reader = list(csv.DictReader(f))
            self.assertEqual(reader[0], {"RFC Emisor": "AAA010101AAA", "Total": "1160.0"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
