"""Pruebas de sat_status (F7-lite): consulta de estatus ante el SAT, con
transporte falso (nunca toca la red) y cache SQLite temporal."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app import sat_status as ss  # noqa: E402


def _respuesta(estado, cancelable="Cancelable sin aceptación", estcanc=""):
    return ('<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
            '<ConsultaResponse><ConsultaResult xmlns:a="http://schemas.datacontract.org/2004/07/Sat.Cfdi.Negocio.ConsultaCfdi.Servicio">'
            '<a:CodigoEstatus>S - Comprobante obtenido satisfactoriamente.</a:CodigoEstatus>'
            f'<a:EsCancelable>{cancelable}</a:EsCancelable><a:Estado>{estado}</a:Estado>'
            f'<a:EstatusCancelacion>{estcanc}</a:EstatusCancelacion>'
            '</ConsultaResult></ConsultaResponse></s:Body></s:Envelope>')


class FakeTransport:
    def __init__(self, estados):
        self.estados = estados      # {uuid_mayusculas: estado}
        self.calls = []

    def __call__(self, expression):
        self.calls.append(expression)
        uuid = expression.split("&id=")[1].upper()
        return _respuesta(self.estados.get(uuid, ss.VIGENTE))


class TestProtocolo(unittest.TestCase):
    def test_expresion_formatea_total_a_17_enteros_y_6_decimales(self):
        self.assertEqual(
            ss.build_expression("abc", "AAA010101AAA", "BBB020202BBB", 198.73),
            "?re=AAA010101AAA&rr=BBB020202BBB&tt=0000000198.730000&id=abc")

    def test_ampersand_en_el_rfc_se_escapa(self):
        """Caso real: 'ER&0412152P0' sin escapar daba 'No Encontrado'."""
        expr = ss.build_expression("u", "ER&0412152P0", "GOOH841231EPA", 1)
        self.assertIn("re=ER&amp;0412152P0&rr=", expr)

    def test_parse_response(self):
        r = ss.parse_response(_respuesta("Cancelado", estcanc="Cancelado sin aceptación"))
        self.assertEqual(r["estado"], ss.CANCELADO)
        self.assertEqual(r["estatus_cancelacion"], "Cancelado sin aceptación")

    def test_respuesta_ilegible_es_error_y_no_inventa_estado(self):
        self.assertEqual(ss.parse_response("<html>502</html>")["estado"], ss.ERROR)
        self.assertEqual(ss.parse_response("")["estado"], ss.ERROR)

    def test_query_status_no_lanza_si_la_red_falla(self):
        def roto(_expr):
            raise OSError("sin red")
        r = ss.query_status("u", "A", "B", 1, transport=roto, retries=0)
        self.assertEqual(r["estado"], ss.ERROR)


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = ss.StatusCache(os.path.join(self.tmp.name, "c.sqlite"))
        self.t0 = datetime(2026, 11, 1, 12, 0)

    def tearDown(self):
        self.tmp.cleanup()

    def _put(self, estado):
        self.cache.put("abc", {"estado": estado, "es_cancelable": "", "estatus_cancelacion": ""},
                       now=self.t0)

    def test_vigente_vale_1_hora(self):
        self._put(ss.VIGENTE)
        self.assertIsNotNone(self.cache.get("ABC", now=self.t0 + timedelta(minutes=30)))
        self.assertIsNone(self.cache.get("ABC", now=self.t0 + timedelta(hours=2)))

    def test_cancelado_nunca_caduca(self):
        self._put(ss.CANCELADO)
        self.assertIsNotNone(self.cache.get("abc", now=self.t0 + timedelta(days=900)))

    def test_no_encontrado_vale_1_hora(self):
        self._put(ss.NO_ENCONTRADO)
        self.assertIsNone(self.cache.get("abc", now=self.t0 + timedelta(hours=2)))

    def test_error_no_se_guarda(self):
        self._put(ss.ERROR)
        self.assertIsNone(self.cache.get("abc", now=self.t0))


class TestVerifyRecords(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = ss.StatusCache(os.path.join(self.tmp.name, "c.sqlite"))

    def tearDown(self):
        self.tmp.cleanup()

    def _records(self):
        return [
            {"UUID": "aaaa", "RFC Emisor": "E1", "RFC Receptor": "R1", "Total": 100.0},
            {"UUID": "BBBB", "RFC Emisor": "E2", "RFC Receptor": "R1", "Total": 50.0},
            # REP con 3 documentos: 3 filas, UNA consulta
            {"UUID CFDI": "cccc", "RFC Emisor CFDI": "E3", "RFC Receptor CFDI": "R1"},
            {"UUID CFDI": "CCCC", "RFC Emisor CFDI": "E3", "RFC Receptor CFDI": "R1"},
            {"UUID CFDI": "cccc", "RFC Emisor CFDI": "E3", "RFC Receptor CFDI": "R1"},
        ]

    def test_llena_estado_sat_y_resume(self):
        records = self._records()
        transport = FakeTransport({"BBBB": ss.CANCELADO})
        resumen = ss.verify_records(records, self.cache, transport=transport)
        self.assertEqual(len(transport.calls), 3)            # 3 UUID distintos
        self.assertEqual(records[0]["Estado SAT"], ss.VIGENTE)
        self.assertEqual(records[1]["Estado SAT"], ss.CANCELADO)
        self.assertEqual({r["Estado SAT"] for r in records[2:]}, {ss.VIGENTE})
        self.assertEqual((resumen["vigente"], resumen["cancelado"]), (2, 1))
        self.assertEqual(resumen["problemas"], [("BBBB", ss.CANCELADO)])

    def test_segunda_corrida_usa_cache(self):
        transport = FakeTransport({})
        ss.verify_records(self._records(), self.cache, transport=transport)
        transport2 = FakeTransport({})
        resumen = ss.verify_records(self._records(), self.cache, transport=transport2)
        self.assertEqual(transport2.calls, [])
        self.assertEqual(resumen["de_cache"], 3)

    def test_force_ignora_el_cache(self):
        ss.verify_records(self._records(), self.cache, transport=FakeTransport({}))
        transport2 = FakeTransport({})
        ss.verify_records(self._records(), self.cache, transport=transport2, force=True)
        self.assertEqual(len(transport2.calls), 3)

    def test_fallo_de_red_no_se_cachea_y_se_reintenta(self):
        def roto(_expr):
            raise OSError("sin red")
        records = self._records()[:1]
        orig = ss.query_status
        ss.query_status = lambda *a, **k: orig(*a, **{**k, "retries": 0})
        try:
            resumen = ss.verify_records(records, self.cache, transport=roto)
        finally:
            ss.query_status = orig
        self.assertEqual(resumen["error"], 1)
        self.assertEqual(records[0]["Estado SAT"], ss.ERROR)
        self.assertIsNone(self.cache.get("AAAA"))

    def test_progreso_llega_al_total(self):
        avances = []
        ss.verify_records(self._records(), self.cache, transport=FakeTransport({}),
                          on_progress=lambda h, t: avances.append((h, t)))
        self.assertEqual(avances[-1], (3, 3))


if __name__ == "__main__":
    unittest.main()
