"""
Pruebas de la mudanza de boveda completa (cfdi_app.vault, D39 / B3-R2).

Cubren la validacion de destino (dentro de la propia boveda, destino ya
ocupado, sin permisos) y el movimiento feliz por sub-RFC. Solo tocan
carpetas temporales; no dependen de la boveda real del usuario.
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
    for rfc, tipos in tree.items():
        for tipo, years in tipos.items():
            for year, months in years.items():
                for month in months:
                    os.makedirs(os.path.join(root, rfc, tipo, year, month))


class _VaultMoveTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.current_root = os.path.join(self._tmp.name, "BovedaCFDI")
        _make_vault(self.current_root, {
            "AAA010101AAA": {"Emitidas": {"2025": ["01", "02"]}},
            "BBB020202BBB": {"Emitidas": {"2025": ["01"]}},
        })

    def tearDown(self):
        self._tmp.cleanup()


class TestValidateVaultMove(_VaultMoveTestCase):
    def test_valid_destination_returns_new_root(self):
        dest_parent = os.path.join(self._tmp.name, "OtroDisco")
        os.makedirs(dest_parent)
        new_root = vault.validate_vault_move(self.current_root, dest_parent)
        self.assertEqual(new_root, os.path.join(dest_parent, "BovedaCFDI"))

    def test_nonexistent_destination_raises(self):
        dest_parent = os.path.join(self._tmp.name, "no_existe")
        with self.assertRaises(vault.VaultMoveError):
            vault.validate_vault_move(self.current_root, dest_parent)

    def test_destination_inside_current_vault_raises(self):
        dest_parent = os.path.join(self.current_root, "AAA010101AAA")
        with self.assertRaises(vault.VaultMoveError):
            vault.validate_vault_move(self.current_root, dest_parent)

    def test_destination_is_current_vault_itself_raises(self):
        with self.assertRaises(vault.VaultMoveError):
            vault.validate_vault_move(self.current_root, self.current_root)

    def test_destination_with_nonempty_boveda_already_raises(self):
        dest_parent = os.path.join(self._tmp.name, "Ocupado")
        _make_vault(os.path.join(dest_parent, "BovedaCFDI"), {
            "CCC030303CCC": {"Emitidas": {"2025": ["01"]}},
        })
        with self.assertRaises(vault.VaultMoveError):
            vault.validate_vault_move(self.current_root, dest_parent)

    def test_destination_with_empty_boveda_folder_is_allowed(self):
        dest_parent = os.path.join(self._tmp.name, "CasiVacio")
        os.makedirs(os.path.join(dest_parent, "BovedaCFDI"))  # existe pero vacia
        new_root = vault.validate_vault_move(self.current_root, dest_parent)
        self.assertEqual(new_root, os.path.join(dest_parent, "BovedaCFDI"))


class TestMoveVault(_VaultMoveTestCase):
    def test_moves_all_rfcs_and_reports_progress(self):
        dest_parent = os.path.join(self._tmp.name, "OtroDisco")
        os.makedirs(dest_parent)

        progress_calls = []
        log_calls = []
        new_root = vault.move_vault(
            self.current_root, dest_parent,
            on_progress=lambda c, t, n: progress_calls.append((c, t, n)),
            on_log=log_calls.append,
        )

        self.assertEqual(new_root, os.path.join(dest_parent, "BovedaCFDI"))
        self.assertTrue(os.path.isdir(os.path.join(new_root, "AAA010101AAA")))
        self.assertTrue(os.path.isdir(os.path.join(new_root, "BBB020202BBB")))
        self.assertEqual(len(progress_calls), 2)
        self.assertEqual(progress_calls[-1][1], 2)  # total = 2 RFCs
        self.assertEqual(len(log_calls), 2)

    def test_source_folder_removed_after_successful_move(self):
        dest_parent = os.path.join(self._tmp.name, "OtroDisco")
        os.makedirs(dest_parent)
        vault.move_vault(self.current_root, dest_parent)
        self.assertFalse(os.path.isdir(self.current_root))

    def test_new_vault_source_reads_moved_folders(self):
        dest_parent = os.path.join(self._tmp.name, "OtroDisco")
        os.makedirs(dest_parent)
        new_root = vault.move_vault(self.current_root, dest_parent)
        src = vault.FolderVaultSource(new_root)
        self.assertEqual(src.rfcs(), ["AAA010101AAA", "BBB020202BBB"])
        self.assertEqual(src.months("AAA010101AAA", "Emitidas", "2025"), ["01", "02"])

    def test_invalid_destination_raises_before_moving_anything(self):
        dest_parent = os.path.join(self.current_root, "AAA010101AAA")
        with self.assertRaises(vault.VaultMoveError):
            vault.move_vault(self.current_root, dest_parent)
        # nada se movio: la boveda original sigue intacta.
        self.assertTrue(os.path.isdir(os.path.join(self.current_root, "AAA010101AAA")))
        self.assertTrue(os.path.isdir(os.path.join(self.current_root, "BBB020202BBB")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
