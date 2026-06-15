"""
Pruebas del parser de Pagos 2.0 (F2.6, ROADMAP.md Sec.13.5/D23).

No hay fixtures reales de Pagos en XML-Test/ (gap de cobertura ya documentado
en test_parsers.py), asi que se construye un XML sintetico minimo pero valido
contra el esquema oficial (docs/pagos20.xsd) para probar puntualmente el bug
del typo de atributo.
"""
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.parsers.pagos_parser_20 import parse_cfdi_pago_20  # noqa: E402

MINIMAL_PAGO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    xmlns:pago20="http://www.sat.gob.mx/Pagos20"
    Version="4.0" Fecha="2026-01-15T10:00:00" Sello="x" NoCertificado="00001"
    Certificado="x" SubTotal="0" Total="0" Moneda="XXX"
    TipoDeComprobante="P" Exportacion="01" LugarExpedicion="45000">
  <cfdi:Emisor Rfc="AAA010101AA1" Nombre="Emisor Prueba" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BB2" Nombre="Receptor Prueba"
      DomicilioFiscalReceptor="45000" RegimenFiscalReceptor="601" UsoCFDI="CP01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111506" Cantidad="1" ClaveUnidad="ACT"
        Descripcion="Pago" ValorUnitario="0" Importe="0" ObjetoImp="01"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="AAAAAAAA-1111-2222-3333-444444444444"
        FechaTimbrado="2026-01-15T10:05:00" NoCertificadoSAT="00002"/>
    <pago20:Pagos Version="2.0">
      <pago20:Totales MontoTotalPagos="11600.00"
          TotalTrasladosBaseIVAExento="9500.00" TotalRetencionesIVA="500.00"/>
      <pago20:Pago FechaPago="2026-01-15T12:00:00" FormaDePagoP="03"
          MonedaP="MXN" Monto="11600.00" NumOperacion="OP-42">
        <pago20:DoctoRelacionado IdDocumento="BBBBBBBB-1111-2222-3333-555555555555"
            MonedaDR="MXN" NumParcialidad="1" ImpSaldoAnt="11600.00"
            ImpPagado="11600.00" ImpSaldoInsoluto="0.00" ObjetoImpDR="02"/>
      </pago20:Pago>
    </pago20:Pagos>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


class TestPagosTypoFix(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "pago.xml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(MINIMAL_PAGO_XML)
            self.rows = parse_cfdi_pago_20(path)

    def test_total_traslados_base_iva_exento_is_read_correctly(self):
        """BUG del typo (Sec.13.5): antes leia el atributo mal escrito y esta
        columna siempre salia 0.00 aunque el XML trajera el dato real."""
        self.assertEqual(len(self.rows), 1)
        self.assertAlmostEqual(self.rows[0]["TotalTrasladosBaseIVAExento"], 9500.00)

    def test_totales_fields_survive_the_per_pago_merge(self):
        """BUG ESTRUCTURAL (hallado al probar el fix del typo): TODOS los
        campos de pago20:Totales se ponian en None al fusionarse con los
        datos del nodo pago20:Pago, no solo el que tenia el typo."""
        self.assertAlmostEqual(self.rows[0]["MontoTotalPagos"], 11600.00)
        self.assertAlmostEqual(self.rows[0]["TotalRetencionesIVA"], 500.00)

    def test_version_pago_is_captured_from_the_pagos_node(self):
        """'Version Pago' vive en pago20:Pagos, no en Totales ni en Pago -
        antes nunca se leia de ningun lado (mismo bug estructural)."""
        self.assertEqual(self.rows[0]["Version Pago"], "2.0")

    def test_per_pago_fields_still_work_after_the_fix(self):
        """El arreglo no debe romper los campos que SI pertenecen a
        pago20:Pago (para evitar un regreso al problema opuesto)."""
        self.assertEqual(self.rows[0]["NumOperacion"], "OP-42")
        self.assertAlmostEqual(self.rows[0]["Monto Pago"], 11600.00)
        self.assertIn("Transferencia", self.rows[0]["FormaDePagoP"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
