# --- cfdi_app/ui/desglose_lote_dialog.py ---
"""Visor del desglose del LOTE completo (F2.10, pedido del dueño 2026-10-28).

Una ventana con caja de busqueda y un arbol Proveedor (RFC) -> Factura ->
lineas, para ver QUE proveedor y QUE factura contiene cada concepto (ej.
escribir "tornillo" y ver en que RFC/factura aparece). Lo que se ve es lo que
"Exportar lo filtrado…" lleva al Excel.

Solo pinta: el filtro y la forma del arbol salen de reports/desglose_conceptos
(logica pura). No escribe archivos: al pedir exportar deja `wants_export` y
`visible_lines`/`query` y cierra; quien lo abrio (main_window) guarda.
Todo el texto va como texto plano (las descripciones del proveedor pueden
traer < > &).

Las lineas de cada factura se crean al EXPANDIRLA (un lote de miles de CFDI
no debe construir decenas de miles de items por cada tecla).
"""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QLabel, QLineEdit, QMenu,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from cfdi_app.reports import desglose_conceptos as dc

# Con mas resultados que esto no se expande todo de golpe (se avisa).
LIMITE_EXPANDIR_TODO = 1500
_NIVEL_PROVEEDOR, _NIVEL_FACTURA, _NIVEL_LINEA = 0, 1, 2
_RETRASO_FILTRO_MS = 250
_COLUMNAS_NUMERICAS = (3, 5, 6, 7)


class DesgloseLoteDialog(QDialog):
    # UUID del comprobante cuyo desglose individual se pidio (doble clic o
    # menu contextual sobre una factura o una linea).
    desglose_requested = Signal(str)

    def __init__(self, lineas, parent=None):
        super().__init__(parent)
        self._lineas = lineas
        self.visible_lines = lineas
        self.query = ""
        self.wants_export = False
        self._nodos = []  # nodo (dict del arbol) por indice guardado en el item

        self.setWindowTitle("Desglose del lote")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1250, 720)

        layout = QVBoxLayout(self)

        self.search_box = QLineEdit()
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setPlaceholderText(
            "Buscar por RFC, proveedor, factura, UUID, concepto, clave, "
            "tarjeta...   o montos:  total>=5000   iva<100   cantidad>10")
        self.search_box.textChanged.connect(lambda _t: self._timer.start())
        layout.addWidget(self.search_box)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_RETRASO_FILTRO_MS)
        self._timer.timeout.connect(self._aplicar_filtro)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(1 + len(dc.COLUMNAS_ARBOL))
        self.tree.setHeaderLabels(["Proveedor / Factura / Concepto"]
                                  + dc.COLUMNAS_ARBOL)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.setColumnWidth(0, 560)
        self.tree.itemExpanded.connect(self._on_expand)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu_contextual)
        layout.addWidget(self.tree, stretch=1)

        copiar = QShortcut(QKeySequence.StandardKey.Copy, self.tree)
        copiar.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copiar.activated.connect(self._copiar_seleccion)

        self.summary_label = QLabel()
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self.summary_label)

        self.hint_label = QLabel()
        self.hint_label.setTextFormat(Qt.PlainText)
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        botones = QDialogButtonBox()
        self.export_btn = botones.addButton(
            "Exportar lo filtrado…", QDialogButtonBox.ActionRole)
        self.export_btn.setToolTip(
            "Excel con lo que se ve ahora (sin la hoja Cuadre)")
        botones.addButton("Cerrar", QDialogButtonBox.RejectRole)
        self.export_btn.clicked.connect(self._on_export)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._aplicar_filtro()

    # --- filtro y poblado --------------------------------------------------
    def _aplicar_filtro(self):
        self.query = self.search_box.text().strip()
        self.visible_lines = dc.filtrar_lineas(self._lineas, self.query)
        self._poblar()

    def _poblar(self):
        self._timer.stop()
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        self._nodos = []
        nodos = dc.arbol(self.visible_lines)
        for nodo in nodos:
            item = self._crear_item(nodo, _NIVEL_PROVEEDOR)
            self.tree.addTopLevelItem(item)
            for hijo in nodo["hijos"]:
                self._agregar_hijo(item, hijo, _NIVEL_FACTURA)

        hint = ""
        if self.query and len(self.visible_lines) <= LIMITE_EXPANDIR_TODO:
            self.tree.expandAll()  # dispara el poblado de las lineas
        elif self.query:
            hint = (f"{len(self.visible_lines)} líneas coinciden: afina la "
                    "búsqueda para verlas todas expandidas, o expande a mano.")
        elif nodos:
            self.tree.expandToDepth(0)  # proveedores abiertos, facturas cerradas
        self.hint_label.setText(hint)
        self.summary_label.setText(
            dc.texto_resumen_lote(self.visible_lines, len(self._lineas)))
        self.export_btn.setEnabled(bool(self.visible_lines))
        self.tree.setUpdatesEnabled(True)

    def _crear_item(self, nodo, nivel):
        item = QTreeWidgetItem([nodo["texto"]] + nodo["cols"])
        for col in _COLUMNAS_NUMERICAS:
            item.setTextAlignment(col, Qt.AlignRight | Qt.AlignVCenter)
        if nivel != _NIVEL_LINEA:
            fuente = item.font(0)
            fuente.setBold(True)
            item.setFont(0, fuente)
        self._nodos.append(nodo)
        item.setData(0, Qt.UserRole, (len(self._nodos) - 1, nivel))
        item.setToolTip(0, nodo["texto"])
        return item

    def _agregar_hijo(self, padre, nodo, nivel):
        item = self._crear_item(nodo, nivel)
        padre.addChild(item)
        if nodo["hijos"]:
            # Marcador: las lineas reales se crean al expandir.
            marcador = QTreeWidgetItem(["…"])
            marcador.setData(0, Qt.UserRole, None)
            item.addChild(marcador)
        return item

    def _on_expand(self, item):
        datos = item.data(0, Qt.UserRole)
        if not datos or item.childCount() != 1:
            return
        if item.child(0).data(0, Qt.UserRole) is not None:
            return  # ya tiene lineas reales
        indice, nivel = datos
        if nivel != _NIVEL_FACTURA:
            return
        item.takeChild(0)
        for hijo in self._nodos[indice]["hijos"]:
            item.addChild(self._crear_item(hijo, _NIVEL_LINEA))

    # --- interaccion -------------------------------------------------------
    def _uuid_de(self, item):
        datos = item.data(0, Qt.UserRole) if item is not None else None
        return self._nodos[datos[0]]["uuid"] if datos else None

    def _on_double_click(self, item, _columna):
        uuid = self._uuid_de(item)
        if uuid:
            self.desglose_requested.emit(uuid)

    def _menu_contextual(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu(self.tree)
        uuid = self._uuid_de(item)
        if uuid:
            accion = menu.addAction("Ver desglose de este XML")
            accion.triggered.connect(
                lambda _c=False, u=uuid: self.desglose_requested.emit(u))
            menu.addSeparator()
        menu.addAction("Copiar").triggered.connect(self._copiar_seleccion)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _copiar_seleccion(self):
        filas = []
        for item in self.tree.selectedItems():
            filas.append("\t".join(
                item.text(c) for c in range(self.tree.columnCount())))
        if filas:
            QApplication.clipboard().setText("\n".join(filas))

    def _on_export(self):
        self.wants_export = True
        self.accept()
