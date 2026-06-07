# --- cfdi_app/ui/state.py ---
# Maquina de estados de la GUI (ver ROADMAP.md Sec.6.2), separada de Qt a
# proposito: es logica pura (enum + funcion), sin importar PySide6, para que
# las transiciones se puedan probar con pruebas unitarias normales sin
# necesitar una QApplication real.
#
# Correccion de fondo del Bug 1 ("GUI congelada"): el estado de los widgets se
# calcula SIEMPRE a partir de esta tabla. Ningun slot conectado a senales del
# hilo/worker debe abrir dialogos modales - solo puede llamar a
# widget_states_for() y aplicar el resultado.
from dataclasses import dataclass
from enum import Enum, auto


class AppState(Enum):
    IDLE = auto()          # sin carpeta seleccionada
    READY = auto()         # carpeta valida seleccionada, listo para procesar
    PROCESSING = auto()    # worker corriendo en su hilo
    DONE = auto()          # proceso termino con datos; se puede guardar Excel
    ERROR = auto()         # proceso termino sin datos o con excepcion


@dataclass(frozen=True)
class WidgetStates:
    select_enabled: bool
    process_enabled: bool
    save_enabled: bool
    progress_active: bool
    progress_format: str  # texto a mostrar en la barra de progreso (fuera de PROCESSING)


def widget_states_for(state: AppState, has_folder: bool) -> WidgetStates:
    """Calcula que widgets deben estar habilitados para un estado dado.

    Tabla exacta de ROADMAP.md Sec.6.2:

        Estado      | Seleccionar | Procesar | Guardar Excel | Progreso
        IDLE        | si          | no       | no            | vacia
        READY       | si          | si       | no            | vacia
        PROCESSING  | no          | no       | no            | activa
        DONE        | si          | si       | si            | "Completado"
        ERROR       | si          | si       | no            | "Error"

    `has_folder` adicionalmente exige una carpeta valida para habilitar
    "Procesar" (en IDLE nunca hay carpeta, pero por claridad se aplica en
    todos los estados).
    """
    if state == AppState.IDLE:
        return WidgetStates(True, False, False, False, "")
    if state == AppState.READY:
        return WidgetStates(True, has_folder, False, False, "")
    if state == AppState.PROCESSING:
        return WidgetStates(False, False, False, True, "")
    if state == AppState.DONE:
        return WidgetStates(True, has_folder, True, False, "Completado")
    if state == AppState.ERROR:
        return WidgetStates(True, has_folder, False, False, "Error")
    raise ValueError(f"Estado desconocido: {state!r}")
