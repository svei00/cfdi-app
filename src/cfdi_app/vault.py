# --- cfdi_app/vault.py ---
"""Capa de acceso a la boveda (COSTURA para F4/F5).

Hoy enumera CARPETAS en disco bajo la estructura humana
``BovedaCFDI/{RFC}/{Emitidas|Recibidas}/{YYYY}/{MM}`` (ver ROADMAP.md F3/D21).
La barra lateral (ui/vault_sidebar.py) NO conoce os.listdir ni SQLite: depende
solo de la interfaz `VaultSource`. Cuando llegue F4 (boveda SQLite, ROADMAP §14)
bastara con implementar otra `VaultSource` que lea la disponibilidad de
RFC/año/mes desde la DB; la capa de UI NO cambia (ROADMAP.md §11.2, D21).

REGLA DURA (prompt B3 / D21): una CARGA nunca mezcla dos RFCs. La regla se
hace cumplir AQUI, en el modelo de datos (`build_load_folders` lanza
`MultipleRfcError`), no solo en la UI. Comparar periodos (años/meses) del MISMO
RFC si esta permitido.
"""
import os

# Direcciones canonicas (mismo vocabulario que core.determine_file_naming_components).
TIPOS = ("Emitidas", "Recibidas")


class MultipleRfcError(Exception):
    """Se intento construir una carga que abarca mas de un RFC (prohibido)."""

    def __init__(self, rfcs):
        self.rfcs = list(rfcs)
        super().__init__(
            "Una carga no puede mezclar varios RFCs: " + ", ".join(self.rfcs))


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
        return self._subdirs(self.root)

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
    - Deduplica carpetas (dos selecciones pueden resolver a la misma ruta).

    El pipeline (`core.process_paths`) recorre cada carpeta con os.walk y
    deduplica ademas a nivel de ARCHIVO, asi que solapes año/mes son inofensivos.
    """
    selections = [s for s in selections if s and s[0]]
    rfcs = {s[0] for s in selections}
    if len(rfcs) > 1:
        raise MultipleRfcError(sorted(rfcs))

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
