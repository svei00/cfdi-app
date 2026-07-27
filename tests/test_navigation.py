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
from cfdi_app.ui.main_window import (  # noqa: E402
    MainWindow, PAGE_INICIO, PAGE_MODULO, PAGE_REPORTES,
)

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

    def test_download_button_is_disabled(self):
        self.assertFalse(self.window.inicio_page.download_module_btn.isEnabled())

    def test_reports_button_is_enabled(self):
        # 2026-07-19: dejo de ser "proximamente" - la app YA genera Excel.
        self.assertTrue(self.window.inicio_page.reports_module_btn.isEnabled())


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


class TestModuleShortName(_NavigationTestCase):
    """2026-07-19: "Administrador de Bóveda" era largo para pestaña/titulo -
    el modulo ahora se llama "Mi Bóveda" ahi; el boton de la caratula que
    navega al modulo SI conserva el texto largo descriptivo."""

    def test_module_header_says_mi_boveda(self):
        titles = [w.text() for w in self.window.admin_page.findChildren(QLabel)]
        self.assertIn("Mi Bóveda", titles)

    def test_menu_action_says_mi_boveda(self):
        self.assertEqual(self.window.open_module_action.text(), "Mi Bóveda")

    def test_home_page_button_keeps_long_descriptive_label(self):
        self.assertEqual(
            self.window.inicio_page.vault_module_btn.text(), "Administrador de Bóveda")


class TestLooseXmlButton(_NavigationTestCase):
    """2026-07-19: el flujo ad-hoc (D11) ahora tambien tiene boton dentro del
    modulo, junto al path - antes solo vivia en el menu Archivo y el dueño
    no lo encontraba."""

    def test_button_exists_and_is_enabled_by_default(self):
        self.assertTrue(self.window.open_loose_xml_btn.isEnabled())

    def test_clicking_button_triggers_same_handler_as_menu_action(self):
        with patch("cfdi_app.ui.main_window.QFileDialog.getExistingDirectory",
                    return_value=""):
            self.window.open_loose_xml_btn.click()  # no debe lanzar


class TestReportesPage(_NavigationTestCase):
    """2026-07-19: "Reportes" dejo de ser un placeholder - abre la carpeta
    donde ya caen los Excel generados."""

    def test_reports_button_navigates_to_reportes_page(self):
        self.window.inicio_page.reports_module_btn.click()
        self.assertEqual(self.window._stack.currentIndex(), PAGE_REPORTES)

    def test_reportes_home_button_returns_to_inicio(self):
        self.window.show_reportes_page()
        self.window.reportes_page.home_btn.click()
        self.assertEqual(self.window._stack.currentIndex(), PAGE_INICIO)

    def test_work_papers_button_stays_disabled(self):
        self.assertFalse(self.window.reportes_page.work_papers_btn.isEnabled())

    def test_open_folder_button_opens_reports_dir(self):
        os.makedirs(paths.REPORTS_DIR, exist_ok=True)
        with patch("cfdi_app.ui.main_window.core.open_folder") as mock_open:
            self.window.reportes_page.open_folder_btn.click()
        mock_open.assert_called_once_with(paths.REPORTS_DIR)

    def test_open_folder_creates_missing_reports_dir(self):
        # MainWindow ya la crea al arrancar (paths.create_initial_directories);
        # se borra a proposito para probar la defensa del propio handler.
        os.rmdir(paths.REPORTS_DIR)
        self.assertFalse(os.path.isdir(paths.REPORTS_DIR))
        with patch("cfdi_app.ui.main_window.core.open_folder"):
            self.window.on_open_reports_folder_clicked()
        self.assertTrue(os.path.isdir(paths.REPORTS_DIR))

    def test_open_folder_failure_is_logged_not_raised(self):
        with patch("cfdi_app.ui.main_window.core.open_folder",
                    side_effect=OSError("boom")):
            self.window.on_open_reports_folder_clicked()  # no debe lanzar
        self.assertIn("No se pudo abrir", self.window.log_view.toPlainText())


class TestVaultHelp(_NavigationTestCase):
    def test_f1_shows_help_dialog(self):
        with patch("cfdi_app.ui.main_window.QMessageBox.information") as mock_info:
            self.window.vault_help_action.trigger()
        mock_info.assert_called_once()
        # El texto debe mencionar ambas acciones para que sirva de aclaracion.
        shown_text = mock_info.call_args[0][2]
        self.assertIn("Mover bóveda", shown_text)
        self.assertIn("Usar otra carpeta", shown_text)


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


class TestMultipleTiposViolation(_NavigationTestCase):
    """Bug real 2026-07-25 (D21): mezclar Emitidas y Recibidas en una carga
    debe avisar, igual que mezclar RFCs - cableado extremo a extremo desde
    la señal de vault_sidebar hasta el QMessageBox de la ventana."""

    def test_signal_triggers_warning_dialog(self):
        with patch("cfdi_app.ui.main_window.QMessageBox.warning") as mock_warn:
            self.window.on_multiple_tipos_violation(["Emitidas", "Recibidas"])
        mock_warn.assert_called_once()
        shown_text = mock_warn.call_args[0][2]
        self.assertIn("Emitidas", shown_text)
        self.assertIn("Recibidas", shown_text)

    def test_vault_sidebar_signal_is_connected_to_the_slot(self):
        with patch("cfdi_app.ui.main_window.QMessageBox.warning") as mock_warn:
            self.window.vault_sidebar.multiple_tipos_violation.emit(
                ["Emitidas", "Recibidas"])
        mock_warn.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
