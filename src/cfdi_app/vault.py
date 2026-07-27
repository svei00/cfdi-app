# --- cfdi_app/vault.py ---
"""Capa de acceso a la boveda (COSTURA para F4/F5).

Hoy enumera CARPETAS en disco bajo la estructura humana
``BovedaCFDI/{RFC}/{Emitidas|Recibidas}/{YYYY}/{MM}`` (ver ROADMAP.md F3/D21).
La barra lateral (ui/vault_sidebar.py) NO conoce os.listdir ni SQLite: depende
solo de la interfaz `VaultSource`. Cuando llegue F4 (boveda SQLite, ROADMAP §14)
bastara con implementar otra `VaultSource` que lea la disponibilidad de
RFC/año/mes desde la DB; la capa de UI NO cambia (ROADMAP.md §11.2, D21).

REGLA DURA (prompt B3 / D21): una CARGA nunca mezcla dos RFCs NI dos
direcciones (Emitidas/Recibidas). La regla se hace cumplir AQUI, en el
modelo de datos (`build_load_folders` lanza `MultipleRfcError` /
`MultipleTiposError`), no solo en la UI. Comparar periodos (años/meses) del
MISMO RFC y la MISMA direccion si esta permitido.

D37 (B3-R2): `FolderVaultSource.rfcs()` filtra las carpetas de primer nivel
con un patron de RFC valido - las carpetas basura que a veces aparecen ahi
("Here", "Master", etc., residuos de otras herramientas o del propio SO)
dejan de mostrarse como si fueran RFCs.

D39 (B3-R2): la boveda se puede MUDAR de ubicacion completa (nunca por-RFC).
`validate_vault_move` valida el destino (clic directo del usuario);
`move_vault` hace el trabajo pesado y esta pensada para correr en un
QThread aparte (ver ui/vault_move_worker.py), igual que el pipeline de
procesamiento.
"""
import os
import re
import shutil

# Direcciones canonicas (mismo vocabulario que core.determine_file_naming_components).
TIPOS = ("Emitidas", "Recibidas")

# RFC de persona moral (3 letras) o fisica (4 letras) + 6 digitos de fecha +
# 3 caracteres de homoclave. Case-insensitive porque el sistema de archivos
# puede devolver la carpeta en cualquier capitalizacion.
RFC_PATTERN = re.compile(r"^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$", re.IGNORECASE)


def is_valid_rfc_folder(name):
    return bool(RFC_PATTERN.match(name))


class MultipleRfcError(Exception):
    """Se intento construir una carga que abarca mas de un RFC (prohibido)."""

    def __init__(self, rfcs):
        self.rfcs = list(rfcs)
        super().__init__(
            "Una carga no puede mezclar varios RFCs: " + ", ".join(self.rfcs))


class MultipleTiposError(Exception):
    """Se intento construir una carga que abarca mas de una direccion
    (Emitidas/Recibidas) - mismo nivel de gravedad que MultipleRfcError (D21:
    "NUNCA se mezclan RFCs ni direcciones"). Bug real 2026-07-25: el arbol NO
    limpiaba sus casillas tras un Cargar exitoso, asi que marcar "todo el
    año" en Emitidas, cargar, y luego marcar "todo el año" en Recibidas SIN
    reiniciar la app combinaba ambas direcciones en un solo lote - el
    resultado mezclado producia el nombre generico "MixedRFCs_Report" y
    requeria reiniciar la app para "limpiar" el estado. Esta excepcion cierra
    el hueco en el MODELO DE DATOS (no solo en la UI), igual que
    MultipleRfcError."""

    def __init__(self, tipos):
        self.tipos = list(tipos)
        super().__init__(
            "Una carga no puede mezclar Emitidas y Recibidas: " + ", ".join(self.tipos))


class VaultSource:
    """Interfaz de solo-lectura de la boveda.

    Un `Selection` es una tupla ``(rfc, tipo, year, month)`` donde los niveles
    inferiores pueden ser ``None`` para significar "todo":
        (rfc, tipo, year, month) -> ese mes
        (rfc, tipo, year, None)  -> todo el año
        (rfc, tipo, None, None)  -> toda la direccion (Emitidas/Recibidas)
    """

    def rfcs(self):
        raise NotImplementedError

    def tipos(self, rfc):
        raise NotImplementedError

    def years(self, rfc, tipo):
        raise NotImplementedError

    def months(self, rfc, tipo, year):
        raise NotImplementedError

    def folders_for(self, rfc, tipo, year=None, month=None):
        """Carpeta(s) en disco que cubren una `Selection`. Lista (puede ir vacia)."""
        raise NotImplementedError


class FolderVaultSource(VaultSource):
    """`VaultSource` respaldada por el sistema de archivos (pre-F4)."""

    def __init__(self, root):
        self.root = root

    # --- helpers -----------------------------------------------------------
    def _subdirs(self, path):
        try:
            entries = os.listdir(path)
        except OSError:
            return []
        return sorted(
            e for e in entries if os.path.isdir(os.path.join(path, e)))

    # --- interfaz ----------------------------------------------------------
    def rfcs(self):
        if not self.root or not os.path.isdir(self.root):
            return []
        return [r for r in self._subdirs(self.root) if is_valid_rfc_folder(r)]

    def tipos(self, rfc):
        present = self._subdirs(os.path.join(self.root, rfc))
        lower = {p.lower(): p for p in present}
        # Orden canonico Emitidas -> Recibidas; conservar cualquier otro al final
        # (nunca ocultar datos que existan en disco).
        canon = [lower[t.lower()] for t in TIPOS if t.lower() in lower]
        extra = [p for p in present if p.lower() not in (t.lower() for t in TIPOS)]
        return canon + extra

    def years(self, rfc, tipo):
        present = self._subdirs(os.path.join(self.root, rfc, tipo))
        return [y for y in present if len(y) == 4 and y.isdigit()]

    def months(self, rfc, tipo, year):
        present = self._subdirs(os.path.join(self.root, rfc, tipo, year))
        out = []
        for m in present:
            if m.isdigit() and 1 <= int(m) <= 12:
                out.append(m)
        return out

    def folders_for(self, rfc, tipo, year=None, month=None):
        base = os.path.join(self.root, rfc, tipo)
        if year is None:
            target = base
        elif month is None:
            target = os.path.join(base, year)
        else:
            target = os.path.join(base, year, month)
        return [target] if os.path.isdir(target) else []


def build_load_folders(source, selections):
    """Traduce las `Selection` marcadas a una lista de carpetas para el pipeline.

    - Hace cumplir la REGLA DURA de un solo RFC (lanza `MultipleRfcError`).
    - Hace cumplir la REGLA DURA de una sola direccion, Emitidas XOR
      Recibidas (lanza `MultipleTiposError`) - la otra mitad de D21, agregada
      2026-07-25 tras el bug real de mezcla entre direcciones.
    - Deduplica carpetas (dos selecciones pueden resolver a la misma ruta).

    El pipeline (`core.process_paths`) recorre cada carpeta con os.walk y
    deduplica ademas a nivel de ARCHIVO, asi que solapes año/mes son inofensivos.
    """
    selections = [s for s in selections if s and s[0]]
    rfcs = {s[0] for s in selections}
    if len(rfcs) > 1:
        raise MultipleRfcError(sorted(rfcs))

    # Selection = (rfc, tipo, year, month); tipo puede ser None ("toda la
    # boveda de este RFC" - hoy sin UI para marcarlo asi, pero la funcion lo
    # soporta). Solo se valida cuando HAY mas de un tipo EXPLICITO distinto;
    # ignorar aqui las tuplas sin tipo no relaja la regla, solo evita un
    # falso positivo en un caso que la UI actual no genera.
    tipos = {s[1] for s in selections if len(s) > 1 and s[1]}
    if len(tipos) > 1:
        raise MultipleTiposError(sorted(tipos))

    folders = []
    seen = set()
    for sel in selections:
        rfc = sel[0]
        tipo = sel[1] if len(sel) > 1 else None
        year = sel[2] if len(sel) > 2 else None
        month = sel[3] if len(sel) > 3 else None
        for folder in source.folders_for(rfc, tipo, year, month):
            key = os.path.normcase(os.path.abspath(folder))
            if key not in seen:
                seen.add(key)
                folders.append(folder)
    return folders


class VaultMoveError(Exception):
    """Destino invalido para mudar la boveda (D39). Mensaje ya listo para
    mostrar al usuario tal cual - nace de un clic directo, es un dialogo
    legitimo."""


def validate_vault_move(current_root, dest_parent):
    """Valida un destino para mudar la boveda COMPLETA (D39). No mueve nada -
    solo valida y devuelve la ruta nueva resultante. Lanza `VaultMoveError`
    con un mensaje claro si el destino no sirve.
    """
    if not dest_parent or not os.path.isdir(dest_parent):
        raise VaultMoveError("La carpeta destino no existe.")

    current_root = os.path.abspath(current_root)
    dest_parent = os.path.abspath(dest_parent)

    try:
        common = os.path.commonpath([dest_parent, current_root])
    except ValueError:
        common = None  # discos distintos en Windows: no puede haber anidamiento
    if common == current_root:
        raise VaultMoveError(
            "La carpeta destino no puede estar dentro de la bóveda actual.")

    if not os.access(dest_parent, os.W_OK):
        raise VaultMoveError(
            "No hay permisos de escritura en la carpeta destino.")

    new_root = os.path.join(dest_parent, os.path.basename(current_root))
    if os.path.isdir(new_root) and os.listdir(new_root):
        raise VaultMoveError(
            f"El destino ya contiene una carpeta "
            f"'{os.path.basename(current_root)}' con archivos.")

    return new_root


def move_vault(current_root, dest_parent, on_progress=None, on_log=None):
    """Mueve la carpeta de boveda COMPLETA (current_root) dentro de
    dest_parent (D39, textual del dueno: "si movemos algo de ubicacion solo
    se mueve la boveda y TODO lo que tiene dentro" - jamas por-RFC).

    Se mueve subcarpeta de RFC por subcarpeta de RFC (en vez de un solo
    shutil.move del directorio raiz) para poder reportar progreso real por
    `on_progress`; tambien significa que si algo falla a medio camino, el
    log (via `on_log`, ya emitido ANTES de la falla) deja claro que se
    alcanzo a mover y que no - nada se borra del origen que no se haya
    movido con exito primero.

    Pensada para correr en un QThread (ver ui/vault_move_worker.py); no
    importa nada de Qt aqui, sigue el mismo patron que core.process_paths.
    Devuelve la ruta nueva de la boveda.
    """
    new_root = validate_vault_move(current_root, dest_parent)
    os.makedirs(new_root, exist_ok=True)

    entries = sorted(
        e for e in os.listdir(current_root)
        if os.path.isdir(os.path.join(current_root, e)))
    total = len(entries)

    for i, name in enumerate(entries, start=1):
        src = os.path.join(current_root, name)
        dst = os.path.join(new_root, name)
        shutil.move(src, dst)  # atomico si mismo disco; copia+borra si no
        if on_log:
            on_log(f"Movido: {name}")
        if on_progress:
            on_progress(i, total, name)

    try:
        if not os.listdir(current_root):
            os.rmdir(current_root)
    except OSError:
        pass  # la carpeta origen vacia es cosmetica; no vale la pena fallar por esto

    return new_root


def resolve_vault_candidate(path):
    """Adivina el nivel correcto de carpeta para "usar como boveda" (D41
    ampliado 2026-07-19: el dueño reporto no saber que nivel elegir en el
    dialogo). Se prueba, en orden:

    1. `path` YA tiene RFCs directamente adentro -> se usa tal cual.
    2. `path` contiene una subcarpeta "BovedaCFDI" (cualquier capitalizacion)
       con RFCs adentro -> se desciende ahi (el usuario eligio el PADRE,
       p. ej. "C:/AdminXML" en vez de "C:/AdminXML/BovedaCFDI").
    3. El NOMBRE de `path` hace match con un RFC valido y su carpeta PADRE
       tiene RFCs -> se sube al padre (el usuario eligio una carpeta de RFC
       por error, un nivel de mas adentro).

    Si nada aplica, devuelve `path` tal cual (sin RFCs encontrados - el
    llamador decide si avisar y dejar continuar de todos modos, p. ej. para
    apuntar a una carpeta vacia a proposito).

    Devuelve `(ruta_resuelta, se_ajusto: bool)`.
    """
    path = os.path.abspath(path)
    if FolderVaultSource(path).rfcs():
        return path, False

    try:
        entries = os.listdir(path) if os.path.isdir(path) else []
    except OSError:
        entries = []
    for entry in entries:
        if entry.lower() == "bovedacfdi":
            candidate = os.path.join(path, entry)
            if os.path.isdir(candidate) and FolderVaultSource(candidate).rfcs():
                return candidate, True

    parent = os.path.dirname(path)
    if parent and parent != path and is_valid_rfc_folder(os.path.basename(path)):
        if FolderVaultSource(parent).rfcs():
            return parent, True

    return path, False
