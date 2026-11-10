"""
Regresiones de los bugs de agregacion hallados con datos reales de octubre 2026:
tasas "0.16", conteo de procesados, totales de Pagos inflados y REP en USD.
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
from cfdi_app.constants import normalize_tasa  # noqa: E402
from cfdi_app.parsers.xml_parser_40 import parse_cfdi_40_invoice  # noqa: E402
from cfdi_app.reports import csv_curation, pt_recibidas  # noqa: E402
from cfdi_app.ui import filtering  # noqa: E402


def _factura_xml(tasa):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Version="4.0" Fecha="2026-10-05T10:00:00" SubTotal="862.07" Total="1000.00"
    Moneda="MXN" TipoDeComprobante="E" MetodoPago="PUE" FormaPago="03">
  <cfdi:Emisor Rfc="AAA010101AA1" Nombre="E" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BB2" Nombre="R" UsoCFDI="G02"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111506" Cantidad="1" ClaveUnidad="ACT"
        Descripcion="NC" ValorUnitario="862.07" Importe="862.07" ObjetoImp="02">
      <cfdi:Impuestos><cfdi:Traslados>
        <cfdi:Traslado Base="862.07" Impuesto="002" TipoFactor="Tasa"
            TasaOCuota="{tasa}" Importe="137.93"/>
      </cfdi:Traslados></cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="137.93"/>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="CCCCCCCC-1111-2222-3333-444444444444"
        FechaTimbrado="2026-10-05T10:05:00"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


def _rep_xml(uuid, n_docs, moneda_dr="MXN", equivalencia=None):
    docs = ""
    for i in range(n_docs):
        eq = f' EquivalenciaDR="{equivalencia}"' if equivalencia else ""
        docs += (f'<pago20:DoctoRelacionado IdDocumento="BBBBBBBB-0000-0000-0000-{i:012d}" '
                 f'MonedaDR="{moneda_dr}"{eq} NumParcialidad="1" ImpSaldoAnt="100.00" '
                 'ImpPagado="100.00" ImpSaldoInsoluto="0.00" ObjetoImpDR="01"/>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    xmlns:pago20="http://www.sat.gob.mx/Pagos20"
    Version="4.0" Fecha="2026-10-15T10:00:00" SubTotal="0" Total="0" Moneda="XXX"
    TipoDeComprobante="P" Exportacion="01" LugarExpedicion="45000">
  <cfdi:Emisor Rfc="AAA010101AA1" Nombre="E" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BB2" Nombre="R" DomicilioFiscalReceptor="45000"
      RegimenFiscalReceptor="601" UsoCFDI="CP01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111506" Cantidad="1" ClaveUnidad="ACT"
        Descripcion="Pago" ValorUnitario="0" Importe="0" ObjetoImp="01"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="{uuid}" FechaTimbrado="2026-10-15T10:05:00"/>
    <pago20:Pagos Version="2.0">
      <pago20:Totales MontoTotalPagos="{100 * n_docs}.00"/>
      <pago20:Pago FechaPago="2026-10-15T12:00:00" FormaDePagoP="03"
          MonedaP="MXN" Monto="{100 * n_docs}.00">{docs}</pago20:Pago>
    </pago20:Pagos>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


class TestNormalizeTasa(unittest.TestCase):
    def test_formas_equivalentes(self):
        for raw in ("0.16", ".16", "0.160000", " 0.16 ", "0.1600"):
            self.assertEqual(normalize_tasa(raw), "0.160000", raw)

    def test_vacio_o_basura_no_coincide_con_nada(self):
        for raw in ("", None, "abc"):
            self.assertEqual(normalize_tasa(raw), "")

    def test_parser_40_reconoce_iva_con_tasa_corta(self):
        """Caso real: una NC trajo TasaOCuota="0.16" y sus 137.93 de IVA no
        entraron en la columna IVA 16%."""
        for tasa in ("0.16", ".16", "0.160000"):
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "nc.xml")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(_factura_xml(tasa))
                data = parse_cfdi_40_invoice(path)
            self.assertAlmostEqual(data["IVA 16%"], 137.93, msg=tasa)

    def test_csv_curation_reconoce_base_con_tasa_corta(self):
        detalle = [{"Impuestos": {"Traslados": [
            {"Impuesto": "002", "TipoFactor": "Tasa", "TasaOCuota": ".16",
             "Base": "100.00", "Importe": "16.00"}]}}]
        self.assertEqual(csv_curation.compute_iva_bases(detalle)["IVA 16 Base"], 100.0)


class TestProcessedCountCuentaArchivos(unittest.TestCase):
    def test_rep_con_varios_documentos_es_un_procesado(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "rep.xml"), "w", encoding="utf-8") as f:
                f.write(_rep_xml("DDDDDDDD-1111-2222-3333-444444444444", 5))
            result = core.process_path(tmp)
        self.assertEqual(len(result.pagos_data), 5)
        self.assertEqual(result.processed_count, 1)


class TestTotalesDePagosSinDuplicar(unittest.TestCase):
    def test_parser_asigna_pagokey_por_nodo_pago(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "rep.xml"), "w", encoding="utf-8") as f:
                f.write(_rep_xml("DDDDDDDD-1111-2222-3333-444444444444", 3))
            rows = core.process_path(tmp).pagos_data
        self.assertEqual({r["PagoKey"] for r in rows},
                         {"DDDDDDDD-1111-2222-3333-444444444444#1"})

    def test_compute_totals_cuenta_monto_total_una_vez_por_rep(self):
        rows = ([{"UUID CFDI": "A", "MontoTotalPagos": 1000.0, "ImpPagado": 100.0}] * 10
                + [{"UUID CFDI": "B", "MontoTotalPagos": 500.0, "ImpPagado": 500.0}])
        totales = filtering.compute_totals(
            rows, {"MontoTotalPagos": "MontoTotalPagos", "ImpPagado": "ImpPagado"},
            once_per={"MontoTotalPagos": "UUID CFDI"})
        self.assertEqual(totales["MontoTotalPagos"], 1500.0)  # no 10 500
        self.assertEqual(totales["ImpPagado"], 1500.0)        # por fila, correcto

    def test_sin_once_per_el_comportamiento_es_el_de_siempre(self):
        rows = [{"MontoTotalPagos": 5.0}, {"MontoTotalPagos": 5.0}]
        self.assertEqual(
            filtering.compute_totals(rows, ["MontoTotalPagos"])["MontoTotalPagos"], 10.0)

    def test_la_pestana_pagos_declara_su_once_per(self):
        from cfdi_app.ui.results_view import PAGOS_TAB
        self.assertEqual(PAGOS_TAB.totals_once_per["MontoTotalPagos"], "UUID CFDI")


class TestRepEnDolares(unittest.TestCase):
    def test_factor_usa_equivalenciadr(self):
        """Caso real octubre 2026: ImpPagado 685.56 USD, EquivalenciaDR
        0.0544401406, pago en MXN => 12,592.91 MXN (no 685.56)."""
        pago = {"ImpPagado": 685.56, "EquivalenciaDR": 0.0544401406,
                "TipoCambioP": 1.0}
        mxn = 685.56 * pt_recibidas.factor_a_mxn_pago(pago)
        self.assertAlmostEqual(mxn, 12592.91, places=1)

    def test_mismo_peso_en_ambos_lados_no_cambia_nada(self):
        self.assertEqual(pt_recibidas.factor_a_mxn_pago(
            {"EquivalenciaDR": 1.0, "TipoCambioP": 1.0}), 1.0)
        self.assertEqual(pt_recibidas.factor_a_mxn_pago({}), 1.0)

    def test_indice_de_pagos_convierte_a_mxn(self):
        indice = pt_recibidas.indexar_pagos_por_uuid([{
            "IdDocumento Relacionado": "x", "FechaPago": "15/10/2026 12:00:00",
            "ImpPagado": 100.0, "EquivalenciaDR": 0.05, "TipoCambioP": 1.0,
            "FormaDePagoP": "03 - Transferencia"}])
        self.assertAlmostEqual(indice["X"][0]["imp_pagado_mxn"], 2000.0)


if __name__ == "__main__":
    unittest.main()
