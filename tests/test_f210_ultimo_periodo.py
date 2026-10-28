"""
Pruebas de F2.10: Reportes recuerda el ultimo periodo procesado.
Parte pura: settings.get/set_last_load y vault.describe_load (la etiqueta que
se le muestra al usuario). La parte de ventana se prueba en
test_f210_reportes_page_ui.py.
"""
import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app import paths, settings, vault  # noqa: E402


class _AppDirAislado(unittest.TestCase):
    """Redirige paths.* a una carpeta temporal (mismo patron que test_settings)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = {k: getattr(paths, k) for k in
                      ("BASE_APP_DIR", "REPORTS_DIR", "LAST_USED_DIR_FILE")}
        paths.BASE_APP_DIR = self._tmp.name
        paths.REPORTS_DIR = os.path.join(self._tmp.name, "Reports")
        paths.LAST_USED_DIR_FILE = os.path.join(
            paths.REPORTS_DIR, "last_used_directory.txt")

    def tearDown(self):
        for k, v in self._orig.items():
            setattr(paths, k, v)
        self._tmp.cleanup()


class TestUltimaCarga(_AppDirAislado):
    def test_sin_nada_guardado(self):
        self.assertEqual(settings.get_last_load(), ([], ""))

    def test_guardar_y_leer(self):
        settings.set_last_load(["/a/b", "/a/c"], "GOOH · Recibidas · 2026-06")
        self.assertEqual(settings.get_last_load(),
                         (["/a/b", "/a/c"], "GOOH · Recibidas · 2026-06"))

    def test_lista_vacia_no_borra_lo_guardado(self):
        settings.set_last_load(["/a/b"], "uno")
        settings.set_last_load([], "nada")
        self.assertEqual(settings.get_last_load(), (["/a/b"], "uno"))

    def test_el_ultimo_guardado_gana(self):
        settings.set_last_load(["/a/b"], "uno")
        settings.set_last_load(["/x/y"], "dos")
        self.assertEqual(settings.get_last_load(), (["/x/y"], "dos"))

    def test_no_pisa_las_demas_preferencias(self):
        settings.set_last_save_dir("/guardados")
        settings.set_last_load(["/a/b"], "uno")
        self.assertEqual(settings.get_last_save_dir(), "/guardados")

    def test_settings_json_editado_a_mano_no_truena(self):
        for basura in ("texto", 5, None, {"folders": "no-lista"},
                       {"folders": [1, None, ""], "label": 7}):
            with self.subTest(basura=basura):
                with open(os.path.join(paths.BASE_APP_DIR, "settings.json"),
                          "w", encoding="utf-8") as f:
                    json.dump({"last_load": basura}, f)
                folders, label = settings.get_last_load()
                self.assertEqual(folders, [])
                self.assertIsInstance(label, str)


class TestDescribeLoad(unittest.TestCase):
    ROOT = os.path.join(os.sep, "data", "BovedaCFDI")

    def _f(self, *partes):
        return os.path.join(self.ROOT, *partes)

    def test_meses_de_un_rfc(self):
        etiqueta, en_boveda = vault.describe_load(
            [self._f("GOOH841231EPA", "Recibidas", "2026", "06"),
             self._f("GOOH841231EPA", "Recibidas", "2026", "07")], self.ROOT)
        self.assertEqual(
            etiqueta, "GOOH841231EPA · Recibidas · 2026-06, 2026-07")
        self.assertTrue(en_boveda)

    def test_un_año_completo(self):
        etiqueta, _ = vault.describe_load(
            [self._f("GOOH841231EPA", "Emitidas", "2026")], self.ROOT)
        self.assertEqual(etiqueta, "GOOH841231EPA · Emitidas · 2026")

    def test_muchos_periodos_se_resumen(self):
        etiqueta, _ = vault.describe_load(
            [self._f("X", "Recibidas", "2026", f"{m:02d}") for m in range(1, 13)],
            self.ROOT)
        self.assertEqual(
            etiqueta, "X · Recibidas · 2026-01 … 2026-12 (12 periodos)")

    def test_carpeta_fuera_de_la_boveda(self):
        etiqueta, en_boveda = vault.describe_load(
            [os.path.join(os.sep, "otra", "carpeta")], self.ROOT)
        self.assertEqual(etiqueta, os.path.join(os.sep, "otra", "carpeta"))
        self.assertFalse(en_boveda)

    def test_varias_carpetas_fuera_de_la_boveda(self):
        etiqueta, en_boveda = vault.describe_load(
            [os.path.join(os.sep, "a"), os.path.join(os.sep, "b")], self.ROOT)
        self.assertEqual(etiqueta, "2 carpetas")
        self.assertFalse(en_boveda)

    def test_sin_carpetas(self):
        self.assertEqual(vault.describe_load([], self.ROOT), ("", False))
        self.assertEqual(vault.describe_load(None, self.ROOT), ("", False))

    def test_sin_ruta_de_boveda_conocida(self):
        etiqueta, en_boveda = vault.describe_load(["/x/y"], "")
        self.assertEqual(etiqueta, "/x/y")
        self.assertFalse(en_boveda)


if __name__ == "__main__":
    unittest.main()
