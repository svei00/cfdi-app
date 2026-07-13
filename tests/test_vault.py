"""
Pruebas de la capa de acceso a la boveda (cfdi_app.vault, Task B3).

Cubren la enumeracion de carpetas (RFC/tipo/año/mes), la construccion de la
lista de carpetas para el pipeline y la REGLA DURA de un solo RFC por carga.
Solo tocan carpetas temporales; no dependen de la boveda real del usuario.
"""
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app import vault  # noqa: E402


def _make_vault(root, tree):
    """tree = {rfc: {tipo: {year: [months]}}} -> crea las carpetas."""
    for rfc, tipos in tree.items():
        for tipo, years in tipos.items():
            for year, months in years.items():
                for month in months:
                    os.makedirs(os.path.join(root, rfc, tipo, year, month))


class _VaultTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()


class TestFolderVaultSourceEnumeration(_VaultTestCase):
    def test_empty_vault_has_no_rfcs(self):
        src = vault.FolderVaultSource(self.root)
        self.assertEqual(src.rfcs(), [])

    def test_missing_root_has_no_rfcs(self):
        src = vault.FolderVaultSource(os.path.join(self.root, "no_existe"))
        self.assertEqual(src.rfcs(), [])

    def test_lists_rfcs_sorted(self):
        _make_vault(self.root, {
            "BBB020202BBB": {"Emitidas": {"2025": ["01"]}},
            "AAA010101AAA": {"Emitidas": {"2025": ["01"]}},
        })
        src = vault.FolderVaultSource(self.root)
        self.assertEqual(src.rfcs(), ["AAA010101AAA", "BBB020202BBB"])

    def test_tipos_are_canonically_ordered(self):
        # En disco puede aparecer Recibidas antes que Emitidas; se normaliza.
        _make_vault(self.root, {
            "AAA010101AAA": {"Recibidas": {"2025": ["01"]}, "Emitidas": {"2025": ["01"]}},
        })
        src = vault.FolderVaultSource(self.root)
        self.assertEqual(src.tipos("AAA010101AAA"), ["Emitidas", "Recibidas"])

    def test_years_filters_non_year_dirs(self):
        _make_vault(self.root, {"AAA010101AAA": {"Emitidas": {"2025": ["01"], "2024": ["12"]}}})
        os.makedirs(os.path.join(self.root, "AAA010101AAA", "Emitidas", "basura"))
        src = vault.FolderVaultSource(self.root)
        self.assertEqual(src.years("AAA010101AAA", "Emitidas"), ["2024", "2025"])

    def test_months_filters_invalid_months(self):
        _make_vault(self.root, {"AAA010101AAA": {"Emitidas": {"2025": ["01", "12"]}}})
        os.makedirs(os.path.join(self.root, "AAA010101AAA", "Emitidas", "2025", "13"))
        os.makedirs(os.path.join(self.root, "AAA010101AAA", "Emitidas", "2025", "xx"))
        src = vault.FolderVaultSource(self.root)
        self.assertEqual(src.months("AAA010101AAA", "Emitidas", "2025"), ["01", "12"])

    def test_folders_for_resolves_each_level(self):
        _make_vault(self.root, {"AAA010101AAA": {"Emitidas": {"2025": ["01"]}}})
        src = vault.FolderVaultSource(self.root)
        month = src.folders_for("AAA010101AAA", "Emitidas", "2025", "01")
        year = src.folders_for("AAA010101AAA", "Emitidas", "2025")
        tipo = src.folders_for("AAA010101AAA", "Emitidas")
        self.assertEqual(month, [os.path.join(self.root, "AAA010101AAA", "Emitidas", "2025", "01")])
        self.assertEqual(year, [os.path.join(self.root, "AAA010101AAA", "Emitidas", "2025")])
        self.assertEqual(tipo, [os.path.join(self.root, "AAA010101AAA", "Emitidas")])

    def test_folders_for_missing_returns_empty(self):
        src = vault.FolderVaultSource(self.root)
        self.assertEqual(src.folders_for("NADA", "Emitidas", "2025", "01"), [])


class TestBuildLoadFolders(_VaultTestCase):
    def setUp(self):
        super().setUp()
        _make_vault(self.root, {
            "AAA010101AAA": {"Emitidas": {"2025": ["01", "02", "03"]}},
        })
        self.src = vault.FolderVaultSource(self.root)

    def test_builds_folder_list_for_selected_months(self):
        sels = [
            ("AAA010101AAA", "Emitidas", "2025", "01"),
            ("AAA010101AAA", "Emitidas", "2025", "02"),
        ]
        folders = vault.build_load_folders(self.src, sels)
        self.assertEqual(len(folders), 2)

    def test_deduplicates_overlapping_selections(self):
        # El año completo y un mes suelto del mismo año se solapan.
        sels = [
            ("AAA010101AAA", "Emitidas", "2025", None),   # todo el año
            ("AAA010101AAA", "Emitidas", "2025", "01"),   # y ademas enero
        ]
        folders = vault.build_load_folders(self.src, sels)
        # Rutas distintas (año vs mes) pero sin duplicar la MISMA ruta.
        self.assertEqual(len(folders), len(set(os.path.normcase(f) for f in folders)))

    def test_single_rfc_allows_multiple_periods(self):
        sels = [
            ("AAA010101AAA", "Emitidas", "2025", "01"),
            ("AAA010101AAA", "Emitidas", "2025", "03"),
        ]
        # No debe lanzar: comparar periodos del MISMO RFC esta permitido.
        folders = vault.build_load_folders(self.src, sels)
        self.assertEqual(len(folders), 2)

    def test_multiple_rfcs_raises(self):
        _make_vault(self.root, {"BBB020202BBB": {"Emitidas": {"2025": ["01"]}}})
        sels = [
            ("AAA010101AAA", "Emitidas", "2025", "01"),
            ("BBB020202BBB", "Emitidas", "2025", "01"),
        ]
        with self.assertRaises(vault.MultipleRfcError) as ctx:
            vault.build_load_folders(self.src, sels)
        self.assertEqual(ctx.exception.rfcs, ["AAA010101AAA", "BBB020202BBB"])

    def test_empty_selection_yields_empty_list(self):
        self.assertEqual(vault.build_load_folders(self.src, []), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
