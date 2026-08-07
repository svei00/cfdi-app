"""
Pruebas de la capa PURA de curacion CSV (F2.9 correcciones, ROADMAP.md
D46-D48). Sin Excel, sin Qt: solo transformaciones de valores y agregaciones
sobre dicts con los mismos nombres de campo que producen los parsers.
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.reports import csv_curation as cur  # noqa: E402


class TestReformatDate(unittest.TestCase):
    def test_date_only_to_iso(self):
        self.assertEqual(cur.reformat_date("15/07/2026"), "2026-07-15")

    def test_datetime_to_iso(self):
        self.assertEqual(
            cur.reformat_date("15/07/2026 12:30:00"), "2026-07-15 12:30:00")

    def test_already_iso_is_left_untouched(self):
        # Fecha Inicial Pago/Fecha Final Pago de Nomina ya vienen ISO.
        self.assertEqual(cur.reformat_date("2026-07-15"), "2026-07-15")

    def test_empty_and_none_pass_through(self):
        self.assertEqual(cur.reformat_date(""), "")
        self.assertIsNone(cur.reformat_date(None))

    def test_garbage_passes_through_unchanged(self):
        self.assertEqual(cur.reformat_date("no es fecha"), "no es fecha")


class TestFormatMoney(unittest.TestCase):
    def test_forces_two_decimals(self):
        self.assertEqual(cur.format_money(65.0), "65.00")
        self.assertEqual(cur.format_money(6.9), "6.90")
        self.assertEqual(cur.format_money(1.0), "1.00")
        self.assertEqual(cur.format_money(393.44), "393.44")

    def test_rounds_extra_precision(self):
        self.assertEqual(cur.format_money(1.005), "1.00")  # banker's/float quirk ok

    def test_empty_and_none_pass_through(self):
        self.assertEqual(cur.format_money(""), "")
        self.assertIsNone(cur.format_money(None))

    def test_non_numeric_text_passes_through(self):
        self.assertEqual(cur.format_money("N/A"), "N/A")


class TestNormalizeUuid(unittest.TestCase):
    def test_forces_uppercase(self):
        self.assertEqual(
            cur.normalize_uuid("0a16de27-0ac7-4152-8d5c-20e245bc12a2"),
            "0A16DE27-0AC7-4152-8D5C-20E245BC12A2")

    def test_already_uppercase_unchanged(self):
        self.assertEqual(cur.normalize_uuid("ABC-123"), "ABC-123")

    def test_empty_passes_through(self):
        self.assertEqual(cur.normalize_uuid(""), "")
        self.assertIsNone(cur.normalize_uuid(None))


class TestTipoConCodigo(unittest.TestCase):
    def test_factura_becomes_i(self):
        self.assertEqual(cur.tipo_con_codigo("Factura"), "I - Factura")

    def test_notacredito_becomes_e(self):
        self.assertEqual(cur.tipo_con_codigo("NotaCredito"), "E - NotaCredito")

    def test_nomina_becomes_n(self):
        self.assertEqual(cur.tipo_con_codigo("Nómina"), "N - Nómina")

    def test_pago_becomes_p(self):
        self.assertEqual(cur.tipo_con_codigo("Pago"), "P - Pago")

    def test_unknown_label_passes_through(self):
        self.assertEqual(cur.tipo_con_codigo("Desconocido"), "Desconocido")

    def test_empty_passes_through(self):
        self.assertIsNone(cur.tipo_con_codigo(None))


class TestCurateValue(unittest.TestCase):
    def test_dispatches_tipo_field(self):
        self.assertEqual(cur.curate_value("Tipo", "Factura"), "I - Factura")
        self.assertEqual(cur.curate_value("TipoComprobante", "Pago"), "P - Pago")

    def test_dispatches_uuid_fields(self):
        self.assertEqual(cur.curate_value("UUID", "abc-123"), "ABC-123")
        self.assertEqual(cur.curate_value("UUID Relacion", "abc"), "ABC")
        self.assertEqual(cur.curate_value("UUID CFDI", "abc"), "ABC")
        self.assertEqual(
            cur.curate_value("IdDocumento Relacionado", "abc"), "ABC")

    def test_dispatches_fecha_fields_by_substring(self):
        self.assertEqual(cur.curate_value("Fecha Emision", "15/07/2026"), "2026-07-15")
        self.assertEqual(cur.curate_value("Fecha Timbrado", "15/07/2026 09:00:00"),
                         "2026-07-15 09:00:00")

    def test_dispatches_money_fields_by_hint(self):
        self.assertEqual(cur.curate_value("SubTotal", 100.0), "100.00")
        self.assertEqual(cur.curate_value("Tipo De Cambio", 1.0), "1.00")
        self.assertEqual(cur.curate_value("IVA 16 Base", 335.34), "335.34")

    def test_unrelated_field_passes_through(self):
        self.assertEqual(cur.curate_value("RFC Emisor", "AAA010101AAA"),
                         "AAA010101AAA")


class TestCurateRow(unittest.TestCase):
    def test_restricts_to_given_columns_in_order(self):
        row = {"A": "1", "B": "2", "C": "3"}
        curated = cur.curate_row(row, ["C", "A"])
        self.assertEqual(list(curated.keys()), ["C", "A"])
        self.assertEqual(curated, {"C": "3", "A": "1"})

    def test_missing_field_becomes_none(self):
        curated = cur.curate_row({"A": "1"}, ["A", "Z"])
        self.assertIsNone(curated["Z"])


class TestComputeIvaBases(unittest.TestCase):
    def _concepto(self, base, tasa=None, tipo_factor="Tasa", impuesto="002"):
        return {"Impuestos": {"Traslados": [
            {"Impuesto": impuesto, "TipoFactor": tipo_factor,
             "TasaOCuota": tasa, "Base": base}
        ]}}

    def test_sums_base_by_rate(self):
        conceptos = [self._concepto("1000.00", "0.160000"),
                    self._concepto("500.00", "0.160000")]
        bases = cur.compute_iva_bases(conceptos)
        self.assertEqual(bases["IVA 16 Base"], 1500.0)

    def test_separates_different_rates(self):
        conceptos = [self._concepto("1000.00", "0.160000"),
                    self._concepto("200.00", "0.080000"),
                    self._concepto("50.00", "0.000000")]
        bases = cur.compute_iva_bases(conceptos)
        self.assertEqual(bases["IVA 16 Base"], 1000.0)
        self.assertEqual(bases["IVA 8 Base"], 200.0)
        self.assertEqual(bases["IVA Cero Base"], 50.0)

    def test_exento_goes_to_its_own_bucket(self):
        conceptos = [self._concepto("300.00", tasa=None, tipo_factor="Exento")]
        bases = cur.compute_iva_bases(conceptos)
        self.assertEqual(bases["IVA Exenta Base"], 300.0)

    def test_ieps_traslado_is_ignored(self):
        conceptos = [self._concepto("100.00", "0.080000", impuesto="003")]  # IEPS
        bases = cur.compute_iva_bases(conceptos)
        self.assertEqual(sum(bases.values()), 0.0)

    def test_empty_conceptos_returns_all_zero(self):
        bases = cur.compute_iva_bases([])
        self.assertEqual(set(bases.values()), {0.0})

    def test_concepto_without_impuestos_node_contributes_nothing(self):
        bases = cur.compute_iva_bases([{"ClaveProdServ": "01010101"}])
        self.assertEqual(set(bases.values()), {0.0})


class TestRelatedDocumentJoin(unittest.TestCase):
    def setUp(self):
        self.batch = [
            {"UUID": "aaa-111", "Serie": "A", "Folio": "1",
             "Fecha Emision": "10/06/2026"},
            {"UUID": "BBB-222", "Serie": "B", "Folio": "2",
             "Fecha Emision": "12/06/2026"},
        ]
        self.index = cur.build_uuid_index(self.batch)

    def test_index_is_case_insensitive(self):
        self.assertIn("AAA-111", self.index)
        self.assertIn("BBB-222", self.index)

    def test_resolves_when_original_is_in_the_batch(self):
        serie, folio, fecha = cur.related_document_fields("aaa-111", self.index)
        self.assertEqual((serie, folio, fecha), ("A", "1", "2026-06-10"))

    def test_uuid_case_does_not_matter_for_lookup(self):
        serie, folio, fecha = cur.related_document_fields("AAA-111", self.index)
        self.assertEqual(serie, "A")

    def test_missing_original_returns_empty_strings_not_none(self):
        result = cur.related_document_fields("ZZZ-999", self.index)
        self.assertEqual(result, ("", "", ""))

    def test_empty_uuid_returns_empty_strings(self):
        self.assertEqual(cur.related_document_fields("", self.index), ("", "", ""))
        self.assertEqual(cur.related_document_fields(None, self.index), ("", "", ""))


class TestHoistConstantColumns(unittest.TestCase):
    def test_constant_column_is_hoisted(self):
        rows = [{"RFC Receptor": "AAA", "Total": "100"},
                {"RFC Receptor": "AAA", "Total": "200"}]
        constantes, restantes, filas = cur.hoist_constant_columns(
            rows, ["RFC Receptor", "Total"])
        self.assertEqual(constantes, {"RFC Receptor": "AAA"})
        self.assertEqual(restantes, ["Total"])
        self.assertEqual(filas, [{"Total": "100"}, {"Total": "200"}])

    def test_varying_column_stays_in_the_table(self):
        rows = [{"RFC Emisor": "AAA"}, {"RFC Emisor": "BBB"}]
        constantes, restantes, _ = cur.hoist_constant_columns(rows, ["RFC Emisor"])
        self.assertEqual(constantes, {})
        self.assertEqual(restantes, ["RFC Emisor"])

    def test_direction_inverts_automatically_emitidas_vs_recibidas(self):
        # Recibidas: Receptor constante (el sujeto), Emisor varia (proveedores).
        recibidas = [{"RFC Emisor": "PROV1", "RFC Receptor": "YO"},
                    {"RFC Emisor": "PROV2", "RFC Receptor": "YO"}]
        c, r, _ = cur.hoist_constant_columns(
            recibidas, ["RFC Emisor", "RFC Receptor"])
        self.assertEqual(c, {"RFC Receptor": "YO"})
        self.assertEqual(r, ["RFC Emisor"])

        # Emitidas: Emisor constante (el sujeto), Receptor varia (clientes).
        emitidas = [{"RFC Emisor": "YO", "RFC Receptor": "CLI1"},
                   {"RFC Emisor": "YO", "RFC Receptor": "CLI2"}]
        c2, r2, _ = cur.hoist_constant_columns(
            emitidas, ["RFC Emisor", "RFC Receptor"])
        self.assertEqual(c2, {"RFC Emisor": "YO"})
        self.assertEqual(r2, ["RFC Receptor"])

    def test_single_row_batch_hoists_nothing(self):
        # min_rows=2 por defecto: una sola fila haria "todo" constante.
        rows = [{"RFC Emisor": "AAA", "Total": "100"}]
        constantes, restantes, filas = cur.hoist_constant_columns(
            rows, ["RFC Emisor", "Total"])
        self.assertEqual(constantes, {})
        self.assertEqual(restantes, ["RFC Emisor", "Total"])
        self.assertEqual(filas, rows)

    def test_empty_rows_hoists_nothing(self):
        constantes, restantes, filas = cur.hoist_constant_columns([], ["A"])
        self.assertEqual((constantes, restantes, filas), ({}, ["A"], []))

    def test_column_order_of_remaining_is_preserved(self):
        rows = [{"A": "x", "B": "1", "C": "y"}, {"A": "x", "B": "2", "C": "y"}]
        _, restantes, _ = cur.hoist_constant_columns(rows, ["A", "B", "C"])
        self.assertEqual(restantes, ["B"])


class TestBuildPreambleLines(unittest.TestCase):
    def test_one_line_per_field(self):
        lines = cur.build_preamble_lines({"RFC Receptor": "AAA", "Nombre Receptor": "X"})
        self.assertEqual(lines, ["# RFC Receptor: AAA", "# Nombre Receptor: X"])

    def test_empty_dict_yields_no_lines(self):
        self.assertEqual(cur.build_preamble_lines({}), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
