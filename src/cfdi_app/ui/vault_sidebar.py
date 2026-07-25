# --- cfdi_app/ui/vault_sidebar.py ---
"""Barra lateral de navegacion de la boveda (Task B3, fase F2.8; corregida en
B3-R2 tras la primera prueba real del dueno, D37/D38).

Reemplaza al selector de carpeta como flujo PRIMARIO (ROADMAP.md F3; el
"Abrir carpeta…" ad-hoc sobrevive como accion secundaria de menu, D11).

Arbol: RFC -> Emitidas/Recibidas -> Año -> Mes. D37 (B3-R2): divulgacion
progresiva - SOLO el nivel Mes tiene casilla; RFC/tipo/año son navegacion
pura (clic expande/colapsa). La cascada padre->hijos de la version anterior
se elimino por completo: marcar un año ya NO marca sus 12 meses de sorpresa.

"Cargar" reune lo marcado, hace cumplir la REGLA DURA de un solo RFC (en la
capa de datos, no solo aqui) y emite `load_requested(folders)` hacia el
pipeline existente (core.process_paths). Comparar periodos del MISMO RFC si
esta permitido; mezclar dos RFCs no (prompt B3 / D21).

Model/View a proposito (espiritu D13): QTreeView + QStandardItemModel. El
modelo se llena DESDE una `vault.VaultSource`; cuando llegue F4 (boveda
SQLite) se cambia la fuente, no este widget (ROADMAP.md §11.2). El filtro de
carpetas no-RFC vive en la capa de datos (vault.py), no aqui (D37).
"""
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QTreeView, QVBoxLayout, QWidget,
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
        self._preset_buttons = []  # [(QPushButton, [meses]), ...] - sync D38(b)

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

        # QStackedWidget en vez de un QLabel + QTreeView apilados a mano con
        # setVisible(): un widget oculto con stretch factor puede seguir
        # reservando espacio en el layout, dejando un hueco muerto entre el
        # texto y los presets (feedback real del dueño). El stack alterna
        # entre la pagina "vacia" (mensaje centrado) y el arbol, sin huecos.
        self._tree_stack = QStackedWidget()

        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch(1)
        self._empty_label = QLabel(
            "No hay RFCs en la bóveda todavía.\n"
            "Usa «Descargar del SAT…» (próximamente) o «Abrir XMLs sueltos…» "
            "(arriba a la derecha).")
        self._empty_label.setWordWrap(True)
        self._empty_label.setAlignment(Qt.AlignHCenter)
        self._empty_label.setStyleSheet("color: palette(placeholder-text);")
        empty_layout.addWidget(self._empty_label)
        empty_layout.addStretch(1)
        self._tree_stack.addWidget(empty_page)  # indice 0

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setUniformRowHeights(True)
        self._tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # D37: clic en un nodo de navegacion (RFC/tipo/año) expande/colapsa,
        # ademas de la flecha - el usuario no tiene que apuntarle al triangulo.
        self._tree.clicked.connect(self._on_tree_clicked)
        # D38(b): el estado visual de los presets depende del año seleccionado.
        self._tree.selectionModel().currentChanged.connect(
            lambda *_: self._sync_preset_buttons())
        self._tree_stack.addWidget(self._tree)  # indice 1

        layout.addWidget(self._tree_stack, stretch=1)

        layout.addWidget(self._build_presets_box())

        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("Cargar")
        self.load_btn.setToolTip("Procesar los periodos marcados del RFC activo")
        self.load_btn.setStyleSheet(
            "QPushButton { padding: 6px 12px; border-radius: 6px; "
            "background-color: palette(highlight); color: palette(highlighted-text); "
            "font-weight: 600; }"
            "QPushButton:disabled { background-color: palette(button); "
            "color: palette(mid); }")
        self.load_btn.clicked.connect(self.on_load_clicked)
        self.reload_btn = QPushButton("Recargar")
        self.reload_btn.setStyleSheet("QPushButton { padding: 6px 12px; border-radius: 6px; }")
        self.reload_btn.setToolTip("Volver a leer las carpetas de la bóveda")
        self.reload_btn.clicked.connect(self.reload)
        self.download_btn = QPushButton("Descargar…")
        self.download_btn.setStyleSheet("QPushButton { padding: 6px 12px; border-radius: 6px; }")
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

        full_btn = self._checkable_preset_button("Año completo", _MESES)
        grid.addWidget(full_btn, 2, 3, 1, 4)
        return box

    # D38(b): estado marcado notorio incluso en tema oscuro (palette(highlight)
    # sigue el tema activo, a diferencia de un color fijo).
    _PRESET_STYLESHEET = (
        "QPushButton:checked { background-color: palette(highlight); "
        "color: palette(highlighted-text); font-weight: bold; }"
    )

    def _checkable_preset_button(self, label, months):
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setStyleSheet(self._PRESET_STYLESHEET)
        btn.clicked.connect(lambda _=False, m=months: self._apply_preset(m))
        self._preset_buttons.append((btn, months))
        return btn

    def _preset_btn(self, label, months):
        btn = self._checkable_preset_button(label, months)
        btn.setMaximumWidth(36)
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
        self._tree_stack.setCurrentIndex(1 if has_rfcs else 0)

        # Reabrir en el ultimo RFC usado, si sigue existiendo.
        last = settings.get_last_rfc()
        if last and last in rfcs:
            self._expand_rfc(last)

        self._sync_preset_buttons()

    def _make_item(self, text, kind, ctx):
        item = QStandardItem(text)
        item.setEditable(False)
        if kind == "month":
            # D37: SOLO los meses tienen casilla - RFC/tipo/año son navegacion
            # pura, sin cascada.
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

    # --- Navegacion (D37: clic en RFC/tipo/año expande/colapsa) ------------
    def _on_tree_clicked(self, index):
        if not index.isValid():
            return
        item = self._model.itemFromIndex(index)
        if item is None or item.data(ROLE_KIND) == "month":
            return  # los meses no tienen hijos que expandir; solo su casilla
        self._tree.setExpanded(index, not self._tree.isExpanded(index))

    # --- Casillas de mes: sin cascada, solo sincroniza los presets ---------
    def _on_item_changed(self, item):
        if self._suppress_item_changed:
            return
        self._sync_preset_buttons()

    # --- Presets -------------------------------------------------------------
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

    def _months_of_year(self, year_item):
        """Items de mes (hijos directos) del item de año dado."""
        return [
            year_item.child(r) for r in range(year_item.rowCount())
            if year_item.child(r) is not None
        ]

    def _apply_preset(self, months):
        """D38(a): TOGGLE real. Si todos los meses disponibles del preset ya
        estan marcados, el clic los desmarca; si no, los marca."""
        year_item = self._current_year_item()
        if year_item is None:
            self.status_message.emit(
                "Selecciona primero un año en el árbol para aplicar el atajo.")
            self._sync_preset_buttons()
            return

        wanted = set(months)
        self._tree.expand(year_item.index())
        available = [m for m in self._months_of_year(year_item) if m.text() in wanted]
        if not available:
            self.status_message.emit(
                "Ese periodo no tiene meses disponibles en el año seleccionado.")
            self._sync_preset_buttons()
            return

        all_checked = all(m.checkState() == Qt.Checked for m in available)
        new_state = Qt.Unchecked if all_checked else Qt.Checked
        self._suppress_item_changed = True
        try:
            for m in available:
                m.setCheckState(new_state)
        finally:
            self._suppress_item_changed = False
        self._sync_preset_buttons()

    def _sync_preset_buttons(self):
        """D38(b): el boton de cada preset se marca solo si TODOS los meses
        disponibles de ese preset (en el año seleccionado) estan marcados."""
        year_item = self._current_year_item()
        existing = set()
        checked = set()
        if year_item is not None:
            for month_item in self._months_of_year(year_item):
                existing.add(month_item.text())
                if month_item.checkState() == Qt.Checked:
                    checked.add(month_item.text())
        for btn, months in self._preset_buttons:
            available = set(months) & existing
            btn.setChecked(bool(available) and available <= checked)

    # --- Atajos de periodo expuestos para QShortcut (D38(c)) ---------------
    def trigger_bimestre(self, i):
        self._apply_preset(BIMESTRES[i])

    def trigger_trimestre(self, i):
        self._apply_preset(TRIMESTRES[i])

    def trigger_semestre(self, i):
        self._apply_preset(SEMESTRES[i])

    def trigger_full_year(self):
        self._apply_preset(_MESES)

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
