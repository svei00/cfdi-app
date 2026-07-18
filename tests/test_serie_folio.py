"""
Prueba de Task B2 (docs/design-f2.8-combustible-fix-y-ux.md): Serie y Folio
como campos separados, ademas de Factura (que debe quedar byte-identico -
D11, lo usan los INDEX/MATCH del dueno contra ERPs).
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.parsers.xml_parser_40 import parse_cfdi_40_invoice  # noqa: E402
from cfdi_app.constants import INVOICE_COLUMN_ORDER  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_fixtures")


def _write_invoice(path, serie=None, folio=None):
    serie_attr = f' Serie="{serie}"' if serie else ""
    folio_attr = f' Folio="{folio}"' if folio else ""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0"
  {serie_attr}{folio_attr} Fecha="2026-06-15T10:00:00" SubTotal="100.00" Total="116.00"
  Moneda="MXN" TipoDeComprobante="I" Exportacion="01" LugarExpedicion="64000">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="EMISOR" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="GOOH841231EPA" Nombre="CLIENTE" DomicilioFiscalReceptor="64000"
    RegimenFiscalReceptor="612" UsoCFDI="G03"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" ClaveUnidad="H87"
      Descripcion="SERVICIO" ValorUnitario="100" Importe="100" ObjetoImp="02"/>
  </cfdi:Conceptos>
</cfdi:Comprobante>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)


class TestSerieFolio(unittest.TestCase):
    def setUp(self):
        os.makedirs(FIXTURES, exist_ok=True)

    def test_serie_and_folio_both_present(self):
        path = os.path.join(FIXTURES, "_sf_both.xml")
        _write_invoice(path, serie="A", folio="123")
        try:
            data = parse_cfdi_40_invoice(path)
            self.assertEqual(data["Serie"], "A")
            self.assertEqual(data["Folio"], "123")
            self.assertEqual(data["Factura"], "A-123")  # byte-identico, D11
        finally:
            os.remove(path)

    def test_folio_only(self):
        path = os.path.join(FIXTURES, "_sf_folio_only.xml")
        _write_invoice(path, folio="456")
        try:
            data = parse_cfdi_40_invoice(path)
            self.assertIsNone(data["Serie"])
            self.assertEqual(data["Folio"], "456")
            self.assertEqual(data["Factura"], "456")  # byte-identico, D11
        finally:
            os.remove(path)

    def test_neither_present(self):
        path = os.path.join(FIXTURES, "_sf_neither.xml")
        _write_invoice(path)
        try:
            data = parse_cfdi_40_invoice(path)
            self.assertIsNone(data["Serie"])
            self.assertIsNone(data["Folio"])
            self.assertIsNone(data["Factura"])  # byte-identico, D11
        finally:
            os.remove(path)

    def test_serie_and_folio_adjacent_to_factura_in_column_order(self):
        idx_factura = INVOICE_COLUMN_ORDER.index("Factura")
        self.assertEqual(INVOICE_COLUMN_ORDER[idx_factura + 1], "Serie")
        self.assertEqual(INVOICE_COLUMN_ORDER[idx_factura + 2], "Folio")


if __name__ == "__main__":
    unittest.main(verbosity=2)
