# --- cfdi_app/paths.py ---
# Dueno UNICO de las rutas de datos de la aplicacion (ver ROADMAP.md Sec.6.4).
# Ningun otro modulo debe construir estas rutas por su cuenta.
#
# Decision D4: el directorio de datos vive en Documents\CFDI-Processor\, NO en
# una ruta relativa al repo. El nombre "AdminXML" (heredado sin querer del
# nombre de la app competidora MiAdminXML) queda retirado.
import os

APP_FOLDER_NAME = "CFDI-Processor"

# Carpeta de recursos visuales (banner de la caratula, D36). Vive junto al
# paquete para que quede incluida al empaquetar la app.
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# GUID de Windows para la carpeta "Documentos" (FOLDERID_Documents), fijo por
# la API de Windows - no cambia entre versiones.
_FOLDERID_DOCUMENTS = (0xFDD39AD0, 0x238F, 0x46AF,
                        (0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))


def _documents_dir_from_windows_api():
    """Pide a Windows la carpeta 'Documentos' REAL vía SHGetKnownFolderPath.

    Por que no basta expanduser("~")/Documents: en Windows esa carpeta se
    puede REDIRIGIR a otro disco o a una carpeta sincronizada (OneDrive, por
    ejemplo) - es una funcion normal del sistema operativo, no un caso raro.
    expanduser ciego ignora esa redireccion y apunta a una ruta que puede ni
    siquiera existir. SHGetKnownFolderPath es la API que SI la respeta.
    Devuelve None si algo falla (no-Windows, API no disponible, etc.) para
    que el llamador use el fallback.
    """
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        data1, data2, data3, data4 = _FOLDERID_DOCUMENTS
        folder_id = GUID(data1, data2, data3, (ctypes.c_ubyte * 8)(*data4))

        path_ptr = ctypes.c_wchar_p()
        result = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id), 0, 0, ctypes.byref(path_ptr))
        if result != 0 or not path_ptr.value:
            return None
        path = path_ptr.value
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)
        return path
    except Exception:
        return None


def _documents_dir():
    """Carpeta 'Documentos' del usuario actual, respetando redirecciones."""
    documents = _documents_dir_from_windows_api()
    if documents and os.path.isdir(documents):
        return documents
    home = os.path.expanduser("~")
    fallback = os.path.join(home, "Documents")
    return fallback if os.path.isdir(fallback) else home


BASE_APP_DIR = os.path.join(_documents_dir(), APP_FOLDER_NAME)
BOVEDA_XML_DIR = os.path.join(BASE_APP_DIR, "BovedaCFDI")
REPORTS_DIR = os.path.join(BASE_APP_DIR, "Reports")
LOGS_DIR = os.path.join(BASE_APP_DIR, "Logs")
LAST_USED_DIR_FILE = os.path.join(REPORTS_DIR, "last_used_directory.txt")


def create_initial_directories():
    """Crea los directorios base de la aplicacion si no existen."""
    os.makedirs(BASE_APP_DIR, exist_ok=True)
    os.makedirs(BOVEDA_XML_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def read_last_used_directory():
    """Devuelve el ultimo directorio usado (si sigue siendo valido) o ''."""
    if os.path.exists(LAST_USED_DIR_FILE):
        try:
            with open(LAST_USED_DIR_FILE, "r") as f:
                last_dir = f.read().strip()
            if os.path.isdir(last_dir):
                return last_dir
        except OSError:
            pass
    return ""


def save_last_used_directory(directory):
    """Guarda el directorio seleccionado para recordarlo en la proxima sesion."""
    if not directory:
        return
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(LAST_USED_DIR_FILE, "w") as f:
            f.write(directory)
    except OSError:
        pass
