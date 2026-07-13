# --- cfdi_app/ui/vault_sidebar.py ---
"""Barra lateral de navegacion de la boveda (Task B3, fase F2.8).

Reemplaza al selector de carpeta como flujo PRIMARIO (ROADMAP.md F3; el
"Abrir carpeta…" ad-hoc sobrevive como accion secundaria de menu, D11).

Arbol:  RFC -> Emitidas/Recibidas -> Año -> Mes, cada nivel con casilla.
"Cargar" reune lo marcado, hace cumplir la REGLA DURA de un solo RFC (en la
capa de datos, no solo aqui) y emite `load_requested(folders)` hacia el
pipeline existente (core.process_paths). Comparar periodos del MISMO RFC si
esta permitido; mezclar dos RFCs no (prompt B3 / D21).

Model/View a proposito (espiritu D13): QTreeView + QStandardItemModel. El
modelo se llena DESDE una `vault.VaultSource`; cuando llegue F4 (boveda
SQLite) se cambia la fuente, no este widget (ROADMAP.md §11.2).
"""
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QTreeView, QVBoxLayout, QWidget,
)

from cfdi_app import settings, vault

logger = logging.getLogger(__name__)

# Roles de datos de cada item del arbol.
ROLE_KIND = Qt.UserRole          # "rfc" | "tipo" | "year" | "month"
ROLE_CTX = Qt.UserRole + 1       # tupla (rfc, tipo, year, month) con None hacia abajo

# Presets: mes(es) que marca cada boton. Meses como texto "MM" para casar con
# los nombres de carpeta que enumera FolderVaultSource.
_MESES = [f"{m:02d}" for m in range(1, 13)]
BIMESTRES = {i: _MESES[2 * (i - 1):2 * i] for i in range(1, 7)}          # 1..6
TRIMESTRES = {i: _MESES[3 * (i - 1):3 * i] for i in range(1, 5)}         # 1..4
SEMESTRES = {1: _MESES[:6], 2: _MESES[6:]}                               # 1..2


class VaultSidebar(QWidget):
    """Panel de navegacion de la boveda. Emite carpetas listas para el motor."""

    # Lista de carpetas (ya validada: un solo RFC) para core.process_paths.
    load_requested = Signal(list)
    # Mensaje breve para el log/estado de la ventana (sin dialogos automaticos).
    status_message = Signal(str)
    # Se marcaron varios RFCs: la ventana muestra el aviso (dialogo nacido del
    # clic directo en "Cargar", legitimo). Lleva la lista de RFCs en conflicto.
    single_rfc_violation = Signal(list)

    def __init__(self, source: vault.VaultSource, parent=None):
        super().__init__(parent)
        self._source = source
        self._suppress_item_changed = False

        self._model = QStandardItemModel(self)
        self._model.itemChanged.connect(self._on_item_changed)

        self._build_ui()
        self.reload()

    # --- Fuente de datos (costura F4) --------------------------------------
    def set_source(self, source: vault.VaultSource):
        """Cambia la fuente (p. ej. de carpetas a SQLite en F4) y recarga."""
        self._source = source
        self.reload()

    # --- Construccion de la UI ---------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel("Bóveda CFDI")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        self._empty_label = QLabel(
            "No hay RFCs en la bóveda todavía.\n"
            "Usa «Descargar del SAT…» (próximamente) o «Abrir carpeta…» "
            "para XMLs sueltos.")
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("color: gray;")
        layout.addWidget(self._empty_label)

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setUniformRowHeights(True)
        self._tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self._tree, stretch=1)

        layout.addWidget(self._build_presets_box())

        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("Cargar")
        self.load_btn.setToolTip("Procesar los periodos marcados del RFC activo")
        self.load_btn.clicked.connect(self.on_load_clicked)
        self.reload_btn = QPushButton("Recargar")
        self.reload_btn.setToolTip("Volver a leer las carpetas de la bóveda")
        self.reload_btn.clicked.connect(self.reload)
        self.download_btn = QPushButton("Descargar…")
        self.download_btn.setEnabled(False)  # F6: depende de CIEC/e.firma (no construido)
        self.download_btn.setToolTip(
            "Descarga del SAT (CIEC / e.firma) — disponible en una fase futura")
        btn_row.addWidget(self.load_btn, stretch=1)
        btn_row.addWidget(self.reload_btn)
        btn_row.addWidget(self.download_btn)
        layout.addLayout(btn_row)

    def _build_presets_box(self):
        box = QGroupBox("Atajos de periodo (año seleccionado)")
        grid = QGridLayout(box)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)

        grid.addWidget(QLabel("Bimestre:"), 0, 0)
        for i in range(1, 7):
            grid.addWidget(self._preset_btn(str(i), BIMESTRES[i]), 0, i)

        grid.addWidget(QLabel("Trimestre:"), 1, 0)
        for i in range(1, 5):
            grid.addWidget(self._preset_btn(str(i), TRIMESTRES[i]), 1, i)

        grid.addWidget(QLabel("Semestre:"), 2, 0)
        for i in range(1, 3):
            grid.addWidget(self._preset_btn(str(i), SEMESTRES[i]), 2, i)

        full_btn = QPushButton("Año completo")
        full_btn.clicked.connect(lambda: self._apply_preset(_MESES))
        grid.addWidget(full_btn, 2, 3, 1, 4)
        return box

    def _preset_btn(self, label, months):
        btn = QPushButton(label)
        btn.setMaximumWidth(36)
        btn.clicked.connect(lambda _=False, m=months: self._apply_preset(m))
        return btn

    # --- Poblado del arbol (desde la VaultSource) --------------------------
    def reload(self):
        """Reconstruye el arbol desde la fuente actual (lectura fresca)."""
        self._suppress_item_changed = True
        self._model.clear()
        root = self._model.invisibleRootItem()

        rfcs = self._source.rfcs()
        for rfc in rfcs:
            rfc_item = self._make_item(rfc, "rfc", (rfc, None, None, None))
            root.appendRow(rfc_item)
            for tipo in self._source.tipos(rfc):
                tipo_item = self._make_item(tipo, "tipo", (rfc, tipo, None, None))
                rfc_item.appendRow(tipo_item)
                for year in self._source.years(rfc, tipo):
                    year_item = self._make_item(
                        year, "year", (rfc, tipo, year, None))
                    tipo_item.appendRow(year_item)
                    for month in self._source.months(rfc, tipo, year):
                        month_item = self._make_item(
                            month, "month", (rfc, tipo, year, month))
                        year_item.appendRow(month_item)

        self._suppress_item_changed = False

        has_rfcs = bool(rfcs)
        self._empty_label.setVisible(not has_rfcs)
        self._tree.setVisible(has_rfcs)

        # Reabrir en el ultimo RFC usado, si sigue existiendo.
        last = settings.get_last_rfc()
        if last and last in rfcs:
            self._expand_rfc(last)

    def _make_item(self, text, kind, ctx):
        item = QStandardItem(text)
        item.setEditable(False)
        item.setCheckable(True)
        item.setCheckState(Qt.Unchecked)
        item.setData(kind, ROLE_KIND)
        item.setData(ctx, ROLE_CTX)
        return item

    def _expand_rfc(self, rfc):
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item and item.text() == rfc:
                self._tree.expand(item.index())
                self._tree.setCurrentIndex(item.index())
                break

    # --- Propagacion de casillas (padre <-> hijos) -------------------------
    def _on_item_changed(self, item):
        if self._suppress_item_changed:
            return
        self._suppress_item_changed = True
        try:
            state = item.checkState()
            if state != Qt.PartiallyChecked:
                self._set_children_state(item, state)
            self._refresh_ancestors(item)
        finally:
            self._suppress_item_changed = False

    def _set_children_state(self, item, state):
        for row in range(item.rowCount()):
            child = item.child(row)
            if child is None:
                continue
            child.setCheckState(state)
            self._set_children_state(child, state)

    def _refresh_ancestors(self, item):
        parent = item.parent()
        while parent is not None:
            states = {
                parent.child(r).checkState()
                for r in range(parent.rowCount())
                if parent.child(r) is not None
            }
            if states == {Qt.Checked}:
                parent.setCheckState(Qt.Checked)
            elif states == {Qt.Unchecked}:
                parent.setCheckState(Qt.Unchecked)
            else:
                parent.setCheckState(Qt.PartiallyChecked)
            parent = parent.parent()

    # --- Presets -----------------------------------------------------------
    def _current_year_item(self):
        """Item de tipo 'year' del nodo seleccionado (o su ancestro año)."""
        index = self._tree.currentIndex()
        if not index.isValid():
            return None
        item = self._model.itemFromIndex(index)
        while item is not None:
            if item.data(ROLE_KIND) == "year":
                return item
            item = item.parent()
        return None

    def _apply_preset(self, months):
        year_item = self._current_year_item()
        if year_item is None:
            self.status_message.emit(
                "Selecciona primero un año en el árbol para aplicar el atajo.")
            return
        wanted = set(months)
        matched = 0
        self._tree.expand(year_item.index())
        for row in range(year_item.rowCount()):
            month_item = year_item.child(row)
            if month_item is not None and month_item.text() in wanted:
                month_item.setCheckState(Qt.Checked)  # dispara _on_item_changed
                matched += 1
        if matched == 0:
            self.status_message.emit(
                "Ese periodo no tiene meses disponibles en el año seleccionado.")

    # --- Recoleccion de la seleccion ---------------------------------------
    def gather_selections(self):
        """Devuelve las `Selection` marcadas: hojas del arbol con casilla activa."""
        selections = []

        def walk(parent):
            for row in range(parent.rowCount()):
                item = parent.child(row)
                if item is None:
                    continue
                if item.rowCount() == 0:
                    if item.checkState() == Qt.Checked:
                        selections.append(item.data(ROLE_CTX))
                else:
                    walk(item)

        walk(self._model.invisibleRootItem())
        return selections

    # --- Cargar (clic directo del usuario) ---------------------------------
    def on_load_clicked(self):
        selections = self.gather_selections()
        if not selections:
            self.status_message.emit(
                "Marca al menos un periodo (RFC → Emitidas/Recibidas → año/mes).")
            return

        try:
            folders = vault.build_load_folders(self._source, selections)
        except vault.MultipleRfcError as exc:
            # La ventana muestra el aviso (dialogo nacido de este clic directo).
            self.single_rfc_violation.emit(exc.rfcs)
            return

        if not folders:
            self.status_message.emit(
                "Los periodos marcados no tienen carpetas en disco.")
            return

        rfc = selections[0][0]
        settings.set_last_rfc(rfc)
        self.load_requested.emit(folders)

    # --- Habilitacion durante el procesamiento -----------------------------
    def set_busy(self, busy):
        """Deshabilita la carga mientras el worker corre (evita cargas paralelas)."""
        self.load_btn.setEnabled(not busy)
        self.reload_btn.setEnabled(not busy)
