# --- cfdi_app/settings.py ---
# Preferencias persistentes minimas de la app (ROADMAP.md D14 / F2.5).
#
# Hoy solo guarda "ultima carpeta de entrada de XMLs" y "ultima carpeta donde
# se guardo un Excel" - lo necesario para que el dialogo de "Guardar Excel..."
# recuerde donde guardaste la ultima vez, en vez de proponer siempre Reports.
# F3 extiende ESTE MISMO archivo (p. ej. el checkbox "usar siempre la misma
# ruta fija") en vez de crear un segundo mecanismo de configuracion.
#
# Migra una sola vez el last_used_directory.txt legado (de paths.py) hacia la
# clave "last_input_dir" de este settings.json. El .txt no se borra (no hace
# falta; queda como fosil inofensivo).
import json
import os

from cfdi_app import paths

SETTINGS_FILE_NAME = "settings.json"

_DEFAULTS = {
    "last_input_dir": "",
    "last_save_dir": "",
}


def _settings_path():
    return os.path.join(paths.BASE_APP_DIR, SETTINGS_FILE_NAME)


def _migrate_legacy_last_used_directory(data):
    if data.get("last_input_dir"):
        return data
    legacy_file = paths.LAST_USED_DIR_FILE
    if os.path.exists(legacy_file):
        try:
            with open(legacy_file, "r", encoding="utf-8") as f:
                legacy_dir = f.read().strip()
            if legacy_dir:
                data["last_input_dir"] = legacy_dir
        except OSError:
            pass
    return data


def load():
    """Devuelve el dict de preferencias, con defaults + migracion del legado."""
    paths.create_initial_directories()
    data = dict(_DEFAULTS)
    settings_path = _settings_path()
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except (OSError, ValueError):
            pass
    return _migrate_legacy_last_used_directory(data)


def save(data):
    paths.create_initial_directories()
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def get_last_input_dir():
    return load().get("last_input_dir", "")


def set_last_input_dir(directory):
    if not directory:
        return
    data = load()
    data["last_input_dir"] = directory
    save(data)


def get_last_save_dir():
    return load().get("last_save_dir", "")


def set_last_save_dir(directory):
    if not directory:
        return
    data = load()
    data["last_save_dir"] = directory
    save(data)
