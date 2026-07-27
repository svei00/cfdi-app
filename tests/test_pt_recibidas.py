"""
Pruebas de la capa PURA del Papel de Trabajo - Recibidas (F2.8 etapa 1,
ROADMAP §17). Sin Excel, sin Qt: solo clasificacion fiscal y agregacion
mensual sobre dicts con los mismos nombres de campo que producen los parsers.

Cubre criterios de aceptacion §17.9: 2 (PPD con/sin REP), 3 (combustible en
efectivo), 4 (umbral $2,000 y forma de pago), 5 (nota de credito netea).
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.reports import pt_recibidas as pt  # noqa: E402

SUJETO = "AAA010101AAA"        # RFC del cliente analizado
PROVEEDOR = "BBB020202BBB"


def factura(uuid="U1", total=1000.0, iva=160.0, metodo="PUE", forma="03",
            fecha="15/06/2026", receptor=SUJETO, subtotal=None,
            conceptos=None, tipo_cambio=1.0):
    """Construye un dict de factura recibida (tipo I) minimo pero con los
    nombres de campo REALES del parser 4.0."""
    metodo_txt = {"PUE": "PUE - Pago en una sola exhibición",
                  "PPD": "PPD - Pago en parcialidades"}.get(metodo, metodo)
    return {
        "CFDI_Type": "Invoice",
        "Tipo": "Factura",
        "UUID": uuid,
        "RFC Emisor": PROVEEDOR,
        "Nombre Emisor": "Proveedor SA",
        "RFC Receptor": receptor,
        "Metodo de Pago": metodo_txt,
        "FormaDePago": f"{forma} - x" if forma else None,
        "Fecha Emision": fecha,
        "SubTotal": subtotal if subtotal is not None else total - iva,
        "IVA 16%": iva,
        "Total": total,
        "Tipo De Cambio": tipo_cambio,
        "ConceptosDetalle": conceptos or [{"ClaveProdServ": "01010101"}],
    }


def nota_credito(uuid="NC1", total=116.0, iva=16.0, fecha="20/06/2026",
                 tipo_rel="01", uuid_rel="U1", receptor=SUJETO):
    return {
        "CFDI_Type": "Invoice",
        "Tipo": "NotaCredito",
        "UUID": uuid,
        "RFC Emisor": PROVEEDOR,
        "RFC Receptor": receptor,
        "Fecha Emision": fecha,
        "SubTotal": total - iva,
        "IVA 16%": iva,
        "Total": total,
        "Tipo De Cambio": 1.0,
        "Tipo Relacion": tipo_rel,
        "UUID Relacion": uuid_rel,
    }


def rep(uuid_factura="U1", imp_pagado=1160.0, iva=160.0, forma="03",
        fecha="10/07/2026"):
    return {
        "CFDI_Type": "Pago",
        "IdDocumento Relacionado": uuid_factura,
        "ImpPagado": imp_pagado,
        "IVA 16 Importe": iva,
        "FormaDePagoP": f"{forma} - x",
        "FechaPago": f"{fecha} 12:00:00",
        "TipoCambioDR": 1.0,
        "NumParcialidad": "1",
        "ImpSaldoInsoluto": 0.0,
    }


class TestHelpers(unittest.TestCase):
    def test_codigo_extrae_prefijo(self):
        self.assertEqual(pt._codigo("PUE - Pago en una..."), "PUE")
        self.assertEqual(pt._codigo("01 - Efectivo"), "01")
        self.assertIsNone(pt._codigo(None))
        self.assertIsNone(pt._codigo(""))

    def test_mes_de_factura_y_rep(self):
        self.assertEqual(pt._mes_de("15/06/2026"), (2026, 6))
        self.assertEqual(pt._mes_de("10/07/2026 12:00:00"), (2026, 7))
        self.assertIsNone(pt._mes_de(""))
        self.assertIsNone(pt._mes_de("basura"))

    def test_es_bancarizada(self):
        self.assertTrue(pt.es_bancarizada("03"))
        self.assertTrue(pt.es_bancarizada("28"))
        self.assertFalse(pt.es_bancarizada("01"))
        self.assertFalse(pt.es_bancarizada("99"))

    def test_es_combustible_familia_1510(self):
        self.assertTrue(pt.es_combustible([{"ClaveProdServ": "15101514"}]))
        self.assertFalse(pt.es_combustible([{"ClaveProdServ": "01010101"}]))
        self.assertFalse(pt.es_combustible([]))


class TestDeterminarSujeto(unittest.TestCase):
    def test_rfc_presente_en_todos_gana(self):
        lote = [factura(receptor=SUJETO), factura(uuid="U2", receptor=SUJETO)]
        self.assertEqual(pt.determinar_rfc_sujeto(lote), SUJETO)

    def test_lote_vacio_devuelve_none(self):
        self.assertIsNone(pt.determinar_rfc_sujeto([]))

    def test_xaxx_nunca_gana_como_sujeto(self):
        # Escenario ad-hoc realista (correo/autofacturacion sin filtro del
        # SAT): 1 factura bien dirigida al sujeto + 3 misdirigidas a XAXX por
        # TRES proveedores distintos (para que ninguno domine por otra via).
        # Sin el candado, XAXX ganaria (3 veces receptor > 1 del sujeto).
        lote = [
            factura(uuid="U1", receptor=SUJETO),
            factura(uuid="U2", receptor="XAXX010101000"),
        ]
        lote[1]["RFC Emisor"] = "CCC030303CCC"
        lote.append(factura(uuid="U3", receptor="XAXX010101000"))
        lote[2]["RFC Emisor"] = "DDD040404DDD"
        lote.append(factura(uuid="U4", receptor="XAXX010101000"))
        lote[3]["RFC Emisor"] = "EEE050505EEE"
        self.assertEqual(pt.determinar_rfc_sujeto(lote), SUJETO)


class TestClasificacion(unittest.TestCase):
    def _clasif(self, fac, pagos=None):
        indice = pt.indexar_pagos_por_uuid(pagos or [])
        return pt.clasificar_recibida(fac, indice)

    def test_receptor_generico_xaxx_no_deducible(self):
        reg = self._clasif(factura(receptor="XAXX010101000", forma="03"))
        self.assertEqual(reg["estatus"], pt.ESTATUS_NO_DED_GENERICO)
        self.assertEqual(reg["nivel"], pt.NIVEL_ROJO)

    def test_combustible_en_efectivo_no_deducible_sin_umbral(self):
        # Criterio §17.9.3: combustible familia 1510, forma 01, aunque valga $500.
        reg = self._clasif(factura(
            total=500.0, forma="01",
            conceptos=[{"ClaveProdServ": "15101514"}]))
        self.assertEqual(reg["estatus"], pt.ESTATUS_NO_DED_COMBUSTIBLE)

    def test_efectivo_mayor_2000_no_deducible(self):
        # Criterio §17.9.4 parte 1.
        reg = self._clasif(factura(total=2500.0, forma="01"))
        self.assertEqual(reg["estatus"], pt.ESTATUS_NO_DED_EFECTIVO)

    def test_mismo_monto_bancarizado_si_deducible(self):
        # Criterio §17.9.4 parte 2: $2,500 con forma 03 -> deducible.
        reg = self._clasif(factura(total=2500.0, forma="03"))
        self.assertEqual(reg["estatus"], pt.ESTATUS_DEDUCIBLE)
        self.assertEqual(reg["nivel"], pt.NIVEL_VERDE)

    def test_efectivo_hasta_2000_deducible(self):
        reg = self._clasif(factura(total=1500.0, forma="01"))
        self.assertEqual(reg["estatus"], pt.ESTATUS_DEDUCIBLE)

    def test_ppd_sin_rep_provisionado(self):
        # Criterio §17.9.2 parte 2.
        reg = self._clasif(factura(metodo="PPD", forma=None))
        self.assertEqual(reg["estatus"], pt.ESTATUS_PROVISIONADO)
        self.assertEqual(reg["nivel"], pt.NIVEL_AMBAR)
        self.assertFalse(reg["tiene_rep"])

    def test_ppd_con_rep_usa_forma_del_rep(self):
        # Criterio §17.9.2 parte 1: con REP deja de estar provisionado.
        reg = self._clasif(factura(uuid="U1", metodo="PPD", forma=None),
                           pagos=[rep(uuid_factura="U1", forma="03")])
        self.assertTrue(reg["tiene_rep"])
        self.assertEqual(reg["forma_efectiva"], "03")
        self.assertEqual(reg["estatus"], pt.ESTATUS_DEDUCIBLE)

    def test_ppd_con_rep_en_efectivo_grande_no_deducible(self):
        reg = self._clasif(
            factura(uuid="U9", total=5000.0, metodo="PPD", forma=None),
            pagos=[rep(uuid_factura="U9", imp_pagado=5000.0, forma="01")])
        self.assertEqual(reg["estatus"], pt.ESTATUS_NO_DED_EFECTIVO)

    def test_forma_99_pue_indeterminado(self):
        reg = self._clasif(factura(forma="99"))
        self.assertEqual(reg["estatus"], pt.ESTATUS_INDETERMINADO)


class TestResumenMensual(unittest.TestCase):
    def test_pue_bancarizado_suma_en_mes_de_emision(self):
        lote = [factura(total=1160.0, iva=160.0, forma="03", fecha="15/06/2026")]
        resumen = pt.construir_resumen_mensual(lote, rfc_sujeto=SUJETO)
        self.assertEqual(len(resumen), 1)
        fila = resumen[0]
        self.assertEqual(fila["mes"], "2026-06")
        self.assertAlmostEqual(fila["pue_bancarizado"], 1160.0)
        self.assertAlmostEqual(fila["iva_acreditable_estimado"], 160.0)

    def test_ppd_pagado_cae_en_mes_del_rep_no_de_emision(self):
        # Emision junio, pago julio: facturado en junio, pagado en julio.
        lote = [factura(uuid="U1", total=1160.0, iva=160.0, metodo="PPD",
                        forma=None, fecha="15/06/2026"),
                rep(uuid_factura="U1", imp_pagado=1160.0, iva=160.0,
                    fecha="10/07/2026")]
        resumen = {f["mes"]: f for f in
                   pt.construir_resumen_mensual(lote, rfc_sujeto=SUJETO)}
        self.assertAlmostEqual(resumen["2026-06"]["ppd_facturado"], 1160.0)
        self.assertAlmostEqual(resumen["2026-06"]["ppd_provisionado"], 0.0)
        self.assertAlmostEqual(resumen["2026-07"]["ppd_pagado"], 1160.0)
        self.assertAlmostEqual(
            resumen["2026-07"]["iva_acreditable_estimado"], 160.0)

    def test_ppd_sin_rep_queda_provisionado_en_su_mes(self):
        lote = [factura(uuid="U1", total=1160.0, metodo="PPD", forma=None,
                        fecha="15/06/2026")]
        resumen = pt.construir_resumen_mensual(lote, rfc_sujeto=SUJETO)[0]
        self.assertAlmostEqual(resumen["ppd_provisionado"], 1160.0)
        self.assertAlmostEqual(resumen["ppd_pagado"], 0.0)

    def test_nota_credito_netea_en_su_mes(self):
        # Criterio §17.9.5: NC visible como columna propia y netea totales.
        lote = [factura(uuid="U1", total=1160.0, iva=160.0, forma="03",
                        fecha="10/06/2026"),
                nota_credito(total=116.0, iva=16.0, uuid_rel="U1",
                             fecha="20/06/2026")]
        fila = pt.construir_resumen_mensual(lote, rfc_sujeto=SUJETO)[0]
        self.assertAlmostEqual(fila["nc_recibidas"], 116.0)
        self.assertAlmostEqual(fila["total_neto"], 1160.0 - 116.0)
        self.assertAlmostEqual(fila["iva_neto"], 160.0 - 16.0)
        # El IVA restituido reduce el acreditable (R5).
        self.assertAlmostEqual(fila["iva_acreditable_estimado"], 160.0 - 16.0)

    def test_nota_credito_tipo_relacion_07_no_netea(self):
        lote = [factura(uuid="U1", total=1160.0, forma="03", fecha="10/06/2026"),
                nota_credito(total=116.0, tipo_rel="07", uuid_rel="U1",
                             fecha="20/06/2026")]
        fila = pt.construir_resumen_mensual(lote, rfc_sujeto=SUJETO)[0]
        self.assertAlmostEqual(fila["nc_recibidas"], 0.0)


class TestSepararRecibidas(unittest.TestCase):
    """2026-07-25 (feedback real): un gasto facturado por error a XAXX/XEXX
    (proveedor que le facturo a 'publico en general' en vez de al RFC del
    sujeto) NO debe desaparecer del PT solo porque no llego via descarga del
    SAT (autofacturacion CFE, correo del proveedor, correo sin filtrar) -
    debe rescatarse y marcarse en rojo, no ocultarse."""

    def test_receptor_normal_es_recibida(self):
        facturas, _ = pt.separar_recibidas([factura(receptor=SUJETO)], SUJETO)
        self.assertEqual(len(facturas), 1)

    def test_gasto_facturado_a_xaxx_por_tercero_se_rescata(self):
        # El proveedor (emisor) NO es el sujeto: es un gasto del sujeto mal
        # facturado, no una factura global emitida por el.
        lote = [factura(uuid="U1", receptor="XAXX010101000")]
        facturas, _ = pt.separar_recibidas(lote, SUJETO)
        self.assertEqual(len(facturas), 1)
        self.assertEqual(facturas[0]["UUID"], "U1")

    def test_gasto_rescatado_a_xaxx_sale_clasificado_no_deducible(self):
        # Extremo a extremo: el rescate + la clasificacion ya existente.
        lote = [factura(uuid="U1", receptor="XAXX010101000", forma="03")]
        detalle = pt.construir_detalle(lote, rfc_sujeto=SUJETO)
        self.assertEqual(len(detalle), 1)
        self.assertEqual(detalle[0]["estatus"], pt.ESTATUS_NO_DED_GENERICO)
        self.assertEqual(detalle[0]["nivel"], pt.NIVEL_ROJO)

    def test_propia_global_emitida_por_el_sujeto_no_se_cuela_como_recibida(self):
        # El SUJETO es el EMISOR (el vendio a publico en general) - eso es
        # ingreso, jamas debe aparecer como gasto en Recibidas.
        lote = [factura(uuid="U1", receptor="XAXX010101000")]
        lote[0]["RFC Emisor"] = SUJETO  # el sujeto factura, no recibe
        facturas, _ = pt.separar_recibidas(lote, SUJETO)
        self.assertEqual(facturas, [])

    def test_xexx_extranjero_tambien_se_rescata(self):
        lote = [factura(uuid="U1", receptor="XEXX010101000")]
        facturas, _ = pt.separar_recibidas(lote, SUJETO)
        self.assertEqual(len(facturas), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
