"""
Pruebas de cfdi_app.settings (ROADMAP.md D14).

Cada prueba apunta paths.BASE_APP_DIR a una carpeta temporal (monkeypatch),
para no tocar la carpeta real de datos del usuario ni depender de su estado.
"""
import importlib
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app import paths, settings  # noqa: E402


class _IsolatedAppDirTestCase(unittest.TestCase):
    """Redirige paths.BASE_APP_DIR/REPORTS_DIR/LAST_USED_DIR_FILE a un temp dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = {
            "BASE_APP_DIR": paths.BASE_APP_DIR,
            "REPORTS_DIR": paths.REPORTS_DIR,
            "LAST_USED_DIR_FILE": paths.LAST_USED_DIR_FILE,
        }
        paths.BASE_APP_DIR = self._tmp.name
        paths.REPORTS_DIR = os.path.join(self._tmp.name, "Reports")
        paths.LAST_USED_DIR_FILE = os.path.join(paths.REPORTS_DIR, "last_used_directory.txt")

    def tearDown(self):
        for key, value in self._orig.items():
            setattr(paths, key, value)
        self._tmp.cleanup()


class TestDefaults(_IsolatedAppDirTestCase):
    def test_defaults_are_empty_strings(self):
        self.assertEqual(settings.get_last_input_dir(), "")
        self.assertEqual(settings.get_last_save_dir(), "")


class TestSetGet(_IsolatedAppDirTestCase):
    def test_set_and_get_last_input_dir(self):
        settings.set_last_input_dir(r"C:\Facturas\Enero")
        self.assertEqual(settings.get_last_input_dir(), r"C:\Facturas\Enero")

    def test_set_and_get_last_save_dir(self):
        settings.set_last_save_dir(r"C:\Reportes\2026")
        self.assertEqual(settings.get_last_save_dir(), r"C:\Reportes\2026")

    def test_setting_one_key_does_not_erase_the_other(self):
        settings.set_last_input_dir(r"C:\Entrada")
        settings.set_last_save_dir(r"C:\Salida")
        self.assertEqual(settings.get_last_input_dir(), r"C:\Entrada")
        self.assertEqual(settings.get_last_save_dir(), r"C:\Salida")

    def test_set_and_get_last_rfc(self):
        settings.set_last_rfc("GOOH841231EPA")
        self.assertEqual(settings.get_last_rfc(), "GOOH841231EPA")

    def test_last_rfc_default_is_empty(self):
        self.assertEqual(settings.get_last_rfc(), "")

    def test_last_rfc_does_not_disturb_dirs(self):
        settings.set_last_input_dir(r"C:\Entrada")
        settings.set_last_rfc("GOOH841231EPA")
        self.assertEqual(settings.get_last_input_dir(), r"C:\Entrada")
        self.assertEqual(settings.get_last_rfc(), "GOOH841231EPA")

    def test_empty_value_is_ignored(self):
        settings.set_last_input_dir(r"C:\Real")
        settings.set_last_input_dir("")
        self.assertEqual(settings.get_last_input_dir(), r"C:\Real")

    def test_settings_file_is_created(self):
        settings.set_last_input_dir(r"C:\Algo")
        self.assertTrue(os.path.exists(os.path.join(paths.BASE_APP_DIR, "settings.json")))


class TestMigracionLegado(_IsolatedAppDirTestCase):
    def test_migrates_legacy_txt_into_last_input_dir(self):
        os.makedirs(paths.REPORTS_DIR, exist_ok=True)
        with open(paths.LAST_USED_DIR_FILE, "w", encoding="utf-8") as f:
            f.write(r"D:\Legado\BovedaCFDI")

        self.assertEqual(settings.get_last_input_dir(), r"D:\Legado\BovedaCFDI")

    def test_migration_does_not_override_existing_setting(self):
        settings.set_last_input_dir(r"C:\Nuevo")
        os.makedirs(paths.REPORTS_DIR, exist_ok=True)
        with open(paths.LAST_USED_DIR_FILE, "w", encoding="utf-8") as f:
            f.write(r"D:\Legado")

        self.assertEqual(settings.get_last_input_dir(), r"C:\Nuevo")


class TestCorruptedFile(_IsolatedAppDirTestCase):
    def test_corrupted_json_falls_back_to_defaults_without_crashing(self):
        paths.create_initial_directories()
        settings_path = os.path.join(paths.BASE_APP_DIR, "settings.json")
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write("{esto no es json valido")

        self.assertEqual(settings.get_last_input_dir(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
