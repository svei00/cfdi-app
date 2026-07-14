"""
Pruebas de navegacion carátula <-> módulo (cfdi_app.ui.main_window, D36 /
B3-R2). Corren en modo offscreen (CI / entorno sin pantalla).

Aisla paths.BASE_APP_DIR (y ASSETS_DIR) a un temp dir para no tocar la
carpeta real de datos del usuario ni depender de banners que pueda tener
instalados.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PySide6.QtWidgets import QApplication, QLabel, QMessageBox  # noqa: E402

from cfdi_app import paths, settings  # noqa: E402
from cfdi_app.ui.main_window import MainWindow, PAGE_INICIO, PAGE_MODULO  # noqa: E402

_app = QApplication.instance() or QApplication([])


class _NavigationTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = {
            "BASE_APP_DIR": paths.BASE_APP_DIR,
            "BOVEDA_XML_DIR": paths.BOVEDA_XML_DIR,
            "REPORTS_DIR": paths.REPORTS_DIR,
            "LOGS_DIR": paths.LOGS_DIR,
            "LAST_USED_DIR_FILE": paths.LAST_USED_DIR_FILE,
            "ASSETS_DIR": paths.ASSETS_DIR,
        }
        paths.BASE_APP_DIR = self._tmp.name
        paths.BOVEDA_XML_DIR = os.path.join(self._tmp.name, "BovedaCFDI")
        paths.REPORTS_DIR = os.path.join(self._tmp.name, "Reports")
        paths.LOGS_DIR = os.path.join(self._tmp.name, "Logs")
        paths.LAST_USED_DIR_FILE = os.path.join(paths.REPORTS_DIR, "last.txt")
        paths.ASSETS_DIR = os.path.join(self._tmp.name, "assets_vacios")

        self.window = MainWindow()

    def tearDown(self):
        self.window.deleteLater()
        for key, value in self._orig.items():
            setattr(paths, key, value)
        self._tmp.cleanup()


class TestInitialPage(_NavigationTestCase):
    def test_starts_on_inicio_page(self):
        self.assertEqual(self.window._stack.currentIndex(), PAGE_INICIO)


class TestModuleButtonsDisabled(_NavigationTestCase):
    def test_vault_module_button_is_enabled(self):
        self.assertTrue(self.window.inicio_page.vault_module_btn.isEnabled())

    def test_download_and_reports_buttons_are_disabled(self):
        self.assertFalse(self.window.inicio_page.download_module_btn.isEnabled())
        self.assertFalse(self.window.inicio_page.reports_module_btn.isEnabled())


class TestBannerPlaceholder(_NavigationTestCase):
    def test_placeholder_shown_when_no_banner_asset_exists(self):
        banner = self.window.inicio_page.findChild(QLabel, "banner_placeholder")
        self.assertIsNotNone(banner)
        self.assertIn("Excel Solutions", banner.text())


class TestNavigationFlow(_NavigationTestCase):
    def test_clicking_vault_module_button_navigates_to_module(self):
        self.window.inicio_page.vault_module_btn.click()
        self.assertEqual(self.window._stack.currentIndex(), PAGE_MODULO)

    def test_home_button_returns_to_inicio(self):
        self.window.show_module_page()
        self.assertEqual(self.window._stack.currentIndex(), PAGE_MODULO)
        self.window.admin_page.home_btn.click()
        self.assertEqual(self.window._stack.currentIndex(), PAGE_INICIO)

    def test_ctrl_b_menu_action_opens_module(self):
        self.window.open_module_action.trigger()
        self.assertEqual(self.window._stack.currentIndex(), PAGE_MODULO)

    def test_no_dock_widget_and_no_ver_menu(self):
        # D36: el QDockWidget desaparece; D40: el menu Ver se elimina.
        self.assertFalse(hasattr(self.window, "vault_dock"))
        menu_titles = [a.text().replace("&", "") for a in self.window.menuBar().actions()]
        self.assertNotIn("Ver", menu_titles)


class TestAdoptVault(_NavigationTestCase):
    """D41: apuntar la boveda a una carpeta EXISTENTE sin mover archivos -
    distinto de "mover boveda" (que si reubica fisicamente, D39)."""

    def _make_existing_vault(self, name="MiAdminXML"):
        existing = os.path.join(self._tmp.name, name, "BovedaCFDI")
        os.makedirs(os.path.join(existing, "AAA010101AAA", "Emitidas", "2025", "01"))
        return existing

    def test_adopting_existing_folder_sets_vault_root_without_moving_anything(self):
        existing = self._make_existing_vault()

        with patch("cfdi_app.ui.main_window.QFileDialog.getExistingDirectory",
                    return_value=existing), \
             patch("cfdi_app.ui.main_window.QMessageBox.question",
                    return_value=QMessageBox.Yes):
            self.window.on_adopt_vault_clicked()

        self.assertEqual(settings.get_vault_root(), existing)
        self.assertTrue(os.path.isdir(os.path.join(existing, "AAA010101AAA")))
        self.assertIn("AAA010101AAA", self.window.vault_source.rfcs())

    def test_cancelling_the_folder_dialog_does_not_change_vault_root(self):
        original = settings.get_vault_root()
        with patch("cfdi_app.ui.main_window.QFileDialog.getExistingDirectory",
                    return_value=""):
            self.window.on_adopt_vault_clicked()
        self.assertEqual(settings.get_vault_root(), original)

    def test_declining_the_confirmation_does_not_change_vault_root(self):
        existing = self._make_existing_vault()
        original = settings.get_vault_root()

        with patch("cfdi_app.ui.main_window.QFileDialog.getExistingDirectory",
                    return_value=existing), \
             patch("cfdi_app.ui.main_window.QMessageBox.question",
                    return_value=QMessageBox.No):
            self.window.on_adopt_vault_clicked()

        self.assertEqual(settings.get_vault_root(), original)

    def test_adopting_folder_without_valid_rfcs_still_allowed_after_confirm(self):
        empty_folder = os.path.join(self._tmp.name, "carpeta_vacia")
        os.makedirs(empty_folder)

        with patch("cfdi_app.ui.main_window.QFileDialog.getExistingDirectory",
                    return_value=empty_folder), \
             patch("cfdi_app.ui.main_window.QMessageBox.question",
                    return_value=QMessageBox.Yes):
            self.window.on_adopt_vault_clicked()

        self.assertEqual(settings.get_vault_root(), empty_folder)


if __name__ == "__main__":
    unittest.main(verbosity=2)
