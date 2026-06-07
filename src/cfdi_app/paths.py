# --- cfdi_app/paths.py ---
# Dueno UNICO de las rutas de datos de la aplicacion (ver ROADMAP.md Sec.6.4).
# Ningun otro modulo debe construir estas rutas por su cuenta.
#
# Decision D4: el directorio de datos vive en Documents\CFDI-Processor\, NO en
# una ruta relativa al repo. El nombre "AdminXML" (heredado sin querer del
# nombre de la app competidora MiAdminXML) queda retirado.
import os

APP_FOLDER_NAME = "CFDI-Processor"


def _documents_dir():
    """Carpeta 'Documentos' del usuario actual (Windows: %USERPROFILE%/Documents)."""
    home = os.path.expanduser("~")
    documents = os.path.join(home, "Documents")
    return documents if os.path.isdir(documents) else home


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
