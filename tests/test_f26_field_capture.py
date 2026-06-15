"""
Pruebas de F2.6: campos nuevos del nucleo CFDI 4.0, IEDU, y captura
por-concepto/por-renglon (ROADMAP.md Sec.13/14, D25).
"""
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.parsers.xml_parser_40 import parse_cfdi_40_invoice  # noqa: E402
from cfdi_app.exporters.excel_exporter import export_to_excel  # noqa: E402
from cfdi_app.constants import EDU_PROD_SERV_CODES, INTERNAL_ONLY_FIELDS  # noqa: E402

FIXTURE_DIR = os.path.join(REPO_ROOT, "XML-Test")
IEDU_FIXTURE = os.path.join(
    FIXTURE_DIR, "52CF2574-F68C-40EE-AAD0-DFE8E85807CD@0000000000XX0.xml")
NOMINA_FIXTURE = os.path.join(
    FIXTURE_DIR, "1EFD576E-42DC-41C1-91E7-B5A9E221773B@0000000000XX0.xml")

MINIMAL_INFO_GLOBAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Version="4.0" Fecha="2026-01-15T10:00:00" Sello="x" NoCertificado="00001"
    Certificado="x" SubTotal="100" Total="116" Moneda="MXN"
    TipoDeComprobante="I" Exportacion="01" LugarExpedicion="45000">
  <cfdi:InformacionGlobal Periodicidad="04" Meses="01" Año="2026"/>
  <cfdi:Emisor Rfc="AAA010101AA1" Nombre="Emisor Prueba" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="XAXX010101000" Nombre="Publico en general"
      DomicilioFiscalReceptor="45000" RegimenFiscalReceptor="616" UsoCFDI="S01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" ClaveUnidad="ACT"
        Descripcion="Venta general" ValorUnitario="100" Importe="100" ObjetoImp="02"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="CCCCCCCC-1111-2222-3333-666666666666"
        FechaTimbrado="2026-01-15T10:05:00" NoCertificadoSAT="00002"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""

MINIMAL_TIPO_RELACION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Version="4.0" Fecha="2026-01-15T10:00:00" Sello="x" NoCertificado="00001"
    Certificado="x" SubTotal="100" Total="116" Moneda="MXN"
    TipoDeComprobante="E" Exportacion="01" LugarExpedicion="45000">
  <cfdi:CfdiRelacionados TipoRelacion="01">
    <cfdi:CfdiRelacionado UUID="DDDDDDDD-1111-2222-3333-777777777777"/>
  </cfdi:CfdiRelacionados>
  <cfdi:Emisor Rfc="AAA010101AA1" Nombre="Emisor Prueba" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BB2" Nombre="Receptor Prueba"
      DomicilioFiscalReceptor="45000" RegimenFiscalReceptor="601" UsoCFDI="G03"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" ClaveUnidad="ACT"
        Descripcion="Nota de credito" ValorUnitario="100" Importe="100" ObjetoImp="02"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="EEEEEEEE-1111-2222-3333-888888888888"
        FechaTimbrado="2026-01-15T10:05:00" NoCertificadoSAT="00002"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


def _parse_inline(xml_text):
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "f.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml_text)
        return parse_cfdi_40_invoice(path)


class TestInformacionGlobal(unittest.TestCase):
    def test_present_marks_comprobante_global(self):
        data = _parse_inline(MINIMAL_INFO_GLOBAL_XML)
        self.assertEqual(data["Comprobante Global"], "Si")
        self.assertEqual(data["Periodicidad Global"], "04")
        self.assertEqual(data["Meses Global"], "01")
        self.assertEqual(data["Año Global"], "2026")

    def test_absent_defaults_to_no(self):
        data = parse_cfdi_40_invoice(IEDU_FIXTURE)  # fixture real, sin InformacionGlobal
        self.assertEqual(data["Comprobante Global"], "No")
        self.assertIsNone(data["Periodicidad Global"])


class TestTipoRelacion(unittest.TestCase):
    def test_captures_official_code(self):
        data = _parse_inline(MINIMAL_TIPO_RELACION_XML)
        self.assertEqual(data["Tipo Relacion"], "01")

    def test_absent_is_none(self):
        data = parse_cfdi_40_invoice(IEDU_FIXTURE)  # sin CfdiRelacionados
        self.assertIsNone(data["Tipo Relacion"])


class TestRegimenFiscalEmisorReachesData(unittest.TestCase):
    def test_captured_in_output_dict(self):
        data = parse_cfdi_40_invoice(IEDU_FIXTURE)
        self.assertTrue(data["RegimenFiscal Emisor"])


class TestIeduExtraFields(unittest.TestCase):
    def test_autRVOE_and_rfc_pago_captured(self):
        data = parse_cfdi_40_invoice(IEDU_FIXTURE)
        self.assertEqual(data["autRVOE"], "P20101458")
        self.assertEqual(data["RFC Pago Colegiatura"], "EAGE740505UP5")


class TestConceptosDetalle(unittest.TestCase):
    def test_official_xsd_keys_present(self):
        data = parse_cfdi_40_invoice(IEDU_FIXTURE)
        detalle = data["ConceptosDetalle"]
        self.assertEqual(len(detalle), 1)
        item = detalle[0]
        for key in ("ClaveProdServ", "Cantidad", "ClaveUnidad", "Descripcion",
                   "ValorUnitario", "Importe", "ObjetoImp"):
            self.assertIn(key, item)

    def test_colegiatura_detectable_by_official_clave(self):
        data = parse_cfdi_40_invoice(IEDU_FIXTURE)
        clave = data["ConceptosDetalle"][0]["ClaveProdServ"]
        self.assertIn(clave, EDU_PROD_SERV_CODES)

    def test_iedu_complemento_nested_in_concepto(self):
        data = parse_cfdi_40_invoice(IEDU_FIXTURE)
        complemento = data["ConceptosDetalle"][0]["Complemento"]
        self.assertEqual(complemento["tipo"], "iedu")
        self.assertEqual(complemento["autRVOE"], "P20101458")
        self.assertEqual(complemento["rfcPago"], "EAGE740505UP5")

    def test_count_matches_number_of_conceptos_in_xml(self):
        # El fixture de nomina tiene un solo Concepto generico.
        data = parse_cfdi_40_invoice(NOMINA_FIXTURE)
        self.assertEqual(len(data["ConceptosDetalle"]), 1)


class TestNominaDetalle(unittest.TestCase):
    def setUp(self):
        self.data = parse_cfdi_40_invoice(NOMINA_FIXTURE)

    def test_percepciones_detalle_matches_real_fixture(self):
        self.assertEqual(len(self.data["PercepcionesDetalle"]), 3)
        self.assertEqual(
            self.data["PercepcionesDetalle"][0]["Concepto"],
            "Sueldos, Salarios Rayas y Jornales")

    def test_deducciones_detalle_matches_real_fixture(self):
        self.assertEqual(len(self.data["DeduccionesDetalle"]), 4)
        self.assertEqual(self.data["DeduccionesDetalle"][0]["TipoDeduccion"], "002")

    def test_otros_pagos_detalle_matches_real_fixture(self):
        self.assertEqual(len(self.data["OtrosPagosDetalle"]), 1)

    def test_invoice_type_has_empty_nomina_detalle_lists(self):
        invoice_data = parse_cfdi_40_invoice(IEDU_FIXTURE)
        self.assertEqual(invoice_data["PercepcionesDetalle"], [])
        self.assertEqual(invoice_data["DeduccionesDetalle"], [])


class TestInternalFieldsExcludedFromExcel(unittest.TestCase):
    """D25: los campos *Detalle son internos y no deben aparecer en el Excel."""

    def test_internal_fields_absent_from_invoices_and_nomina_sheets(self):
        invoice_data = [parse_cfdi_40_invoice(IEDU_FIXTURE)]
        nomina_data = [parse_cfdi_40_invoice(NOMINA_FIXTURE)]

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "salida.xlsx")
            export_to_excel(invoice_data, nomina_data, [], output_path)

            import openpyxl
            wb = openpyxl.load_workbook(output_path)
            for sheet_name in ("Invoices", "Nomina"):
                headers = [cell.value for cell in wb[sheet_name][1]]
                for internal_field in INTERNAL_ONLY_FIELDS:
                    self.assertNotIn(
                        internal_field, headers,
                        f"{internal_field} no deberia aparecer en la hoja {sheet_name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
