"""
Pruebas del widget de barra lateral de la boveda (cfdi_app.ui.vault_sidebar,
Task B3). Corren en modo offscreen (CI / entorno sin pantalla).

Aisla paths.BASE_APP_DIR a un temp dir para que set_last_rfc no toque el
settings.json real del usuario.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from cfdi_app import paths, settings, vault  # noqa: E402
from cfdi_app.ui.vault_sidebar import (  # noqa: E402
    BIMESTRES, SEMESTRES, TRIMESTRES, VaultSidebar,
)

_app = QApplication.instance() or QApplication([])


def _make_vault(root, tree):
    for rfc, tipos in tree.items():
        for tipo, years in tipos.items():
            for year, months in years.items():
                for month in months:
                    os.makedirs(os.path.join(root, rfc, tipo, year, month))


class _SidebarTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self._tmp.name, "BovedaCFDI")
        os.makedirs(self.root)
        # Aislar settings.json.
        self._orig = {
            "BASE_APP_DIR": paths.BASE_APP_DIR,
            "BOVEDA_XML_DIR": paths.BOVEDA_XML_DIR,
            "REPORTS_DIR": paths.REPORTS_DIR,
            "LOGS_DIR": paths.LOGS_DIR,
            "LAST_USED_DIR_FILE": paths.LAST_USED_DIR_FILE,
        }
        paths.BASE_APP_DIR = self._tmp.name
        paths.BOVEDA_XML_DIR = self.root
        paths.REPORTS_DIR = os.path.join(self._tmp.name, "Reports")
        paths.LOGS_DIR = os.path.join(self._tmp.name, "Logs")
        paths.LAST_USED_DIR_FILE = os.path.join(paths.REPORTS_DIR, "last.txt")

    def tearDown(self):
        for key, value in self._orig.items():
            setattr(paths, key, value)
        self._tmp.cleanup()

    def _sidebar(self):
        return VaultSidebar(vault.FolderVaultSource(self.root))

    def _year_item(self, sb, rfc_row=0, tipo_row=0, year_text="2025"):
        rfc_item = sb._model.item(rfc_row)
        tipo_item = rfc_item.child(tipo_row)
        for r in range(tipo_item.rowCount()):
            if tipo_item.child(r).text() == year_text:
                return tipo_item.child(r)
        return None


class TestPopulation(_SidebarTestCase):
    def test_empty_vault_hides_tree_shows_placeholder(self):
        sb = self._sidebar()
        # isHidden() refleja el estado explicito de ocultacion (isVisible() es
        # False en tests offscreen porque el top-level no esta .show()).
        self.assertTrue(sb._tree.isHidden())
        self.assertFalse(sb._empty_label.isHidden())
        self.assertEqual(sb._model.rowCount(), 0)

    def test_populates_all_rfcs(self):
        _make_vault(self.root, {
            "AAA010101AAA": {"Emitidas": {"2025": ["01", "02"]}},
            "BBB020202BBB": {"Recibidas": {"2024": ["12"]}},
        })
        sb = self._sidebar()
        rfcs = [sb._model.item(r).text() for r in range(sb._model.rowCount())]
        self.assertEqual(rfcs, ["AAA010101AAA", "BBB020202BBB"])


class TestCheckPropagation(_SidebarTestCase):
    def setUp(self):
        super().setUp()
        _make_vault(self.root, {"AAA010101AAA": {"Emitidas": {"2025": ["01", "02", "03"]}}})

    def test_checking_year_checks_all_months(self):
        sb = self._sidebar()
        year = self._year_item(sb)
        year.setCheckState(Qt.Checked)
        sels = sb.gather_selections()
        self.assertEqual(sorted(s[3] for s in sels), ["01", "02", "03"])

    def test_unchecking_one_month_makes_year_partial(self):
        sb = self._sidebar()
        year = self._year_item(sb)
        year.setCheckState(Qt.Checked)
        year.child(0).setCheckState(Qt.Unchecked)
        self.assertEqual(year.checkState(), Qt.PartiallyChecked)
        sels = sb.gather_selections()
        self.assertEqual(sorted(s[3] for s in sels), ["02", "03"])


class TestPresets(_SidebarTestCase):
    def setUp(self):
        super().setUp()
        _make_vault(self.root, {"AAA010101AAA": {"Emitidas": {"2025": [f"{m:02d}" for m in range(1, 13)]}}})

    def test_bimestre_checks_two_months(self):
        sb = self._sidebar()
        year = self._year_item(sb)
        sb._tree.setCurrentIndex(year.index())
        sb._apply_preset(BIMESTRES[3])  # meses 05, 06
        sels = sb.gather_selections()
        self.assertEqual(sorted(s[3] for s in sels), ["05", "06"])

    def test_trimestre_checks_three_months(self):
        sb = self._sidebar()
        year = self._year_item(sb)
        sb._tree.setCurrentIndex(year.index())
        sb._apply_preset(TRIMESTRES[1])  # 01, 02, 03
        self.assertEqual(sorted(s[3] for s in sb.gather_selections()), ["01", "02", "03"])

    def test_semestre_checks_six_months(self):
        sb = self._sidebar()
        year = self._year_item(sb)
        sb._tree.setCurrentIndex(year.index())
        sb._apply_preset(SEMESTRES[2])  # 07..12
        self.assertEqual(len(sb.gather_selections()), 6)

    def test_preset_without_year_selected_emits_status(self):
        sb = self._sidebar()
        sb._tree.clearSelection()
        messages = []
        sb.status_message.connect(messages.append)
        sb._apply_preset(BIMESTRES[1])
        self.assertTrue(messages)
        self.assertEqual(sb.gather_selections(), [])


class TestLoad(_SidebarTestCase):
    def setUp(self):
        super().setUp()
        _make_vault(self.root, {
            "AAA010101AAA": {"Emitidas": {"2025": ["01", "02"]}},
            "BBB020202BBB": {"Emitidas": {"2025": ["01"]}},
        })

    def test_load_emits_folders_and_persists_rfc(self):
        sb = self._sidebar()
        year = self._year_item(sb, rfc_row=0)
        year.setCheckState(Qt.Checked)
        captured = []
        sb.load_requested.connect(captured.append)
        sb.on_load_clicked()
        self.assertEqual(len(captured), 1)
        self.assertEqual(len(captured[0]), 2)  # dos meses
        self.assertEqual(settings.get_last_rfc(), "AAA010101AAA")

    def test_load_across_two_rfcs_does_not_emit(self):
        sb = self._sidebar()
        self._year_item(sb, rfc_row=0).child(0).setCheckState(Qt.Checked)
        # marcar tambien un mes del segundo RFC
        bbb = sb._model.item(1)
        bbb.child(0).child(0).child(0).setCheckState(Qt.Checked)
        captured = []
        violations = []
        sb.load_requested.connect(captured.append)
        sb.single_rfc_violation.connect(violations.append)
        sb.on_load_clicked()  # avisa (señal), NO emite carga
        self.assertEqual(captured, [])
        self.assertEqual(len(violations), 1)
        self.assertEqual(sorted(violations[0]), ["AAA010101AAA", "BBB020202BBB"])

    def test_load_without_selection_emits_status(self):
        sb = self._sidebar()
        messages = []
        sb.status_message.connect(messages.append)
        captured = []
        sb.load_requested.connect(captured.append)
        sb.on_load_clicked()
        self.assertTrue(messages)
        self.assertEqual(captured, [])

    def test_reopens_last_rfc(self):
        settings.set_last_rfc("BBB020202BBB")
        sb = self._sidebar()
        current = sb._tree.currentIndex()
        self.assertTrue(current.isValid())
        self.assertEqual(sb._model.itemFromIndex(current).text(), "BBB020202BBB")


if __name__ == "__main__":
    unittest.main(verbosity=2)
