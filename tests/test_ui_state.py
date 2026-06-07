"""
Pruebas de la maquina de estados de la GUI (ROADMAP.md Sec.6.2 / 6.9 punto 6).

cfdi_app.ui.state es logica pura (enum + funcion), sin importar PySide6, asi
que estas pruebas corren sin necesitar una QApplication. Verifican la tabla
exacta de la correccion de fondo del Bug 1: "Guardar Excel..." SOLO se habilita
en DONE, y "Procesar"/"Seleccionar carpeta" quedan bloqueados mientras
PROCESSING (para que no se dispare un segundo hilo encima del primero).
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.ui.state import AppState, widget_states_for  # noqa: E402


class TestWidgetStatesForTable(unittest.TestCase):
    """Tabla exacta de ROADMAP.md Sec.6.2, con carpeta ya seleccionada."""

    def test_idle_only_allows_selecting_folder(self):
        ws = widget_states_for(AppState.IDLE, has_folder=False)
        self.assertTrue(ws.select_enabled)
        self.assertFalse(ws.process_enabled)
        self.assertFalse(ws.save_enabled)
        self.assertFalse(ws.progress_active)

    def test_ready_allows_select_and_process_but_not_save(self):
        ws = widget_states_for(AppState.READY, has_folder=True)
        self.assertTrue(ws.select_enabled)
        self.assertTrue(ws.process_enabled)
        self.assertFalse(ws.save_enabled)
        self.assertFalse(ws.progress_active)

    def test_processing_locks_everything(self):
        ws = widget_states_for(AppState.PROCESSING, has_folder=True)
        self.assertFalse(ws.select_enabled)
        self.assertFalse(ws.process_enabled)
        self.assertFalse(ws.save_enabled)
        self.assertTrue(ws.progress_active)

    def test_done_enables_save_and_shows_completed(self):
        ws = widget_states_for(AppState.DONE, has_folder=True)
        self.assertTrue(ws.select_enabled)
        self.assertTrue(ws.process_enabled)
        self.assertTrue(ws.save_enabled)
        self.assertEqual(ws.progress_format, "Completado")

    def test_error_disables_save_and_shows_error(self):
        ws = widget_states_for(AppState.ERROR, has_folder=True)
        self.assertTrue(ws.select_enabled)
        self.assertTrue(ws.process_enabled)
        self.assertFalse(ws.save_enabled)
        self.assertEqual(ws.progress_format, "Error")

    def test_process_requires_a_valid_folder_in_every_non_processing_state(self):
        for state in (AppState.READY, AppState.DONE, AppState.ERROR):
            with self.subTest(state=state):
                ws = widget_states_for(state, has_folder=False)
                self.assertFalse(ws.process_enabled)


if __name__ == "__main__":
    unittest.main(verbosity=2)
