# --- cfdi_app/ui/results_view.py ---
# Widget del "Visor de resultados" (ROADMAP.md Sec.11 / D13 / D15).
#
# Autocontenido a proposito (ver Sec.5.3 del ROADMAP): no conoce MainWindow,
# solo recibe un core.ProcessResult via set_result(). Esto permite colgarlo
# despues de un shell/dashboard sin reescribirlo, y que F4 conecte un modelo
# respaldado en SQLite a la MISMA vista para el modo historial.
from collections import defaultdict
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMenu, QTableView, QTabWidget,
    QVBoxLayout, QWidget,
)

from cfdi_app.ui import filtering
from cfdi_app.ui.results_model import RecordTableModel
from cfdi_app.ui.results_proxy import RecordFilterProxyModel

# Paleta "Office/Excel Dark" (decision del dueno 2026-07-04, ver ROADMAP D16).
# Aplicada SOLO a este widget (la tabla del visor) - NO es un tema de la app
# completa. El resto de la ventana sigue el tema de Windows como antes; un
# sistema de tema claro/oscuro para TODA la app (con autodeteccion del SO)
# queda pendiente y registrado aparte (ver ROADMAP Sec.5.3/notas de tema).
_DARK_TABLE_STYLESHEET = """
QTableView {
    background-color: #201F1E;
    alternate-background-color: #292827;
    color: #E8E6E3;
    gridline-color: #484644;
    selection-background-color: #004E8C;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background-color: #323130;
    color: #FFFFFF;
    padding: 4px;
    border: 1px solid #484644;
}
QTabWidget::pane {
    border: 1px solid #484644;
}
QTabBar::tab {
    background: #2D2C2B;
    color: #E8E6E3;
    padding: 6px 14px;
}
QTabBar::tab:selected {
    background: #201F1E;
    color: #FFFFFF;
}
"""


@dataclass(frozen=True)
class TabConfig:
    key: str              # "invoice_data" / "nomina_data" / "pagos_data" en ProcessResult
    title: str
    display_columns: list
    text_fields: list
    amount_fields: dict    # alias en minusculas -> clave real, para "campo<numero"
    default_amount_field: str  # clave real usada cuando no se nombra campo
    total_columns: list    # claves reales a sumar en la fila de totales


INVOICE_TAB = TabConfig(
    key="invoice_data",
    title="Facturas",
    # Default ampliado 2026-07-04 (D18): de 12 a 23 columnas de las 62 del
    # Excel. Criterio: se incluye lo que importa para revision contable
    # (Tipo I/E, UsoCFDI, retenciones, forma/metodo de pago, tipo de cambio,
    # UUID Relacion para credito/sustitucion). Se dejan fuera a proposito:
    # residentes extranjeros (NumRegIdTrib/ResidenciaFiscal - caso raro),
    # IEDU (CURP/Nivel Educativo Dependiente - solo escuelas privadas),
    # tasas de IEPS individuales (3%/6%/7%/8%/9%/26.5%/30%/30.4%/53%/160% -
    # "Total IEPS" ya las resume), direcciones completas (ocupan mucho ancho),
    # y "Estado SAT"/"Verificado o Asoc." (siempre vacios hoy: la validacion
    # SAT es F7, aun no implementada - una columna siempre en blanco es ruido).
    # Todo esto sigue disponible en el Excel completo; el visor es un vistazo
    # rapido, no un reemplazo del Excel. Selector de columnas configurable
    # por el usuario: F3 (D18).
    display_columns=["Factura", "Tipo", "Fecha Emision", "RFC Emisor", "Nombre Emisor",
                     "RFC Receptor", "Nombre Receptor", "UsoCFDI", "LugarDeExpedicion",
                     "SubTotal", "Descuento", "IVA 16%", "Retenido IVA", "Retenido ISR",
                     "Total IEPS", "Total", "Moneda", "Tipo De Cambio", "FormaDePago",
                     "Metodo de Pago", "Conceptos", "UUID", "UUID Relacion"],
    # Ampliado 2026-07-05 (a peticion del dueno, sin necesidad de Fable/Opus -
    # ambos campos YA eran columnas visibles arriba, solo faltaba poder
    # buscarlos): UsoCFDI (p.ej. deducibilidad D10 colegiaturas) y Metodo de
    # Pago (PUE/PPD).
    text_fields=["RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
                "Factura", "UUID", "Conceptos", "UsoCFDI", "Metodo de Pago"],
    amount_fields={"total": "Total", "subtotal": "SubTotal", "descuento": "Descuento",
                  "iva": "IVA 16%"},
    default_amount_field="Total",
    total_columns=["SubTotal", "Descuento", "IVA 16%", "Retenido IVA", "Retenido ISR",
                  "Total IEPS", "Total"],
)

NOMINA_TAB = TabConfig(
    key="nomina_data",
    title="Nómina",
    # Default ampliado 2026-07-04 (D18): agrega periodo de pago, identificadores
    # de empleado (CURP/NSS) y desglose de percepciones - lo que un contador
    # revisa primero en una nomina. IEDU (Nivel Educativo) queda fuera.
    display_columns=["Factura", "Tipo Nomina", "Fecha Inicial Pago", "Fecha Final Pago",
                     "RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
                     "CURP", "NSS", "SubTotal", "Total Sueldos", "Total Otros Pagos",
                     "Total Deducciones", "Total", "Periodicidad Pago",
                     "Registro Patronal", "Conceptos", "UUID"],
    text_fields=["RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
                "Factura", "UUID", "Conceptos"],
    amount_fields={"total": "Total", "subtotal": "SubTotal",
                  "deducciones": "Total Deducciones"},
    default_amount_field="Total",
    total_columns=["SubTotal", "Total Sueldos", "Total Otros Pagos",
                  "Total Deducciones", "Total"],
)

PAGOS_TAB = TabConfig(
    key="pagos_data",
    title="Pagos",
    # Default ampliado 2026-07-04 (D18): agrega a que factura aplica el pago
    # (Serie/Folio Relacionado - clave para conciliar), avance de parcialidad
    # y referencia bancaria. Se dejan fuera los ~90 campos de desglose de
    # impuestos por tasa especifica (IEPS/IVA/retenciones por porcentaje) -
    # rara vez se usan varios a la vez y estan completos en el Excel.
    display_columns=["Serie CFDI", "Folio CFDI", "RFC Emisor CFDI", "Nombre Emisor CFDI",
                     "RFC Receptor CFDI", "Nombre Receptor CFDI", "FechaPago",
                     "FormaDePagoP", "MontoTotalPagos", "Serie Relacionada",
                     "Folio Relacionado", "NumParcialidad", "ImpSaldoAnt", "ImpPagado",
                     "ImpSaldoInsoluto", "NumOperacion", "UUID CFDI"],
    text_fields=["RFC Emisor CFDI", "Nombre Emisor CFDI", "RFC Receptor CFDI",
                "Nombre Receptor CFDI", "Serie CFDI", "Folio CFDI", "UUID CFDI"],
    amount_fields={"total": "MontoTotalPagos", "monto": "Monto Pago"},
    default_amount_field="MontoTotalPagos",
    total_columns=["MontoTotalPagos", "ImpPagado"],
)

ALL_TABS = [INVOICE_TAB, NOMINA_TAB, PAGOS_TAB]


class _ResultsTabPanel(QWidget):
    """Una pestaña: caja de busqueda + tabla + fila de totales."""

    # F2.10 etapa 3: el usuario pidio el desglose de UN comprobante (clic
    # derecho en Facturas). Solo lleva el UUID; el panel no sabe de reportes.
    desglose_requested = Signal(str)

    def __init__(self, config: TabConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._records = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Buscar por RFC, nombre, folio, UUID, concepto, UsoCFDI, "
            "metodo de pago...  o  <2000 / total>=5000")
        self.search_box.textChanged.connect(self._on_query_changed)
        layout.addWidget(self.search_box)

        self.model = RecordTableModel([], config.display_columns)
        self.proxy = RecordFilterProxyModel(
            config.text_fields, config.amount_fields, config.default_amount_field)
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, stretch=1)

        # Task C (docs/design-f2.8...): copiar seleccion al portapapeles del
        # sistema. Ctrl+C estandar + menu contextual "Copiar", ambos
        # iniciados por el usuario (no choca con la regla anti-dialogos-
        # modales-automaticos).
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self.table)
        copy_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copy_shortcut.activated.connect(self._copy_selection)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.totals_label = QLabel()
        self.totals_label.setStyleSheet("font-weight: bold; padding: 4px;")
        # Sin word wrap, Qt calcula el ancho MINIMO de la ventana como el
        # ancho necesario para mostrar TODA la linea de totales sin cortar -
        # con muchas columnas de totales (Facturas: 7) eso bloqueaba encoger
        # la ventana por debajo de ~1900px. Con wrap, el texto se acomoda en
        # varias lineas cuando hace falta y la ventana vuelve a encoger libre.
        self.totals_label.setWordWrap(True)
        layout.addWidget(self.totals_label)

        self._update_totals_label()

    def set_records(self, records):
        self._records = records
        self.model = RecordTableModel(records, self.config.display_columns)
        self.proxy.setSourceModel(self.model)
        self._update_totals_label()

    def _record_at_pos(self, pos):
        """Registro de la fila bajo el cursor (no necesariamente la
        seleccionada), o None si el clic cayo fuera de las filas."""
        index = self.table.indexAt(pos)
        if not index.isValid():
            return None
        return self.model.record_at(self.proxy.mapToSource(index).row())

    def _show_context_menu(self, pos):
        menu = QMenu(self.table)
        if self.config.key == INVOICE_TAB.key:
            record = self._record_at_pos(pos)
            uuid = str((record or {}).get("UUID") or "").strip()
            if uuid:
                desglose_action = menu.addAction("Ver desglose de este XML")
                desglose_action.triggered.connect(
                    lambda _checked=False, u=uuid: self.desglose_requested.emit(u))
                menu.addSeparator()
        copy_action = menu.addAction("Copiar")
        copy_action.triggered.connect(self._copy_selection)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _copy_selection(self):
        selection_model = self.table.selectionModel()
        if selection_model is None:
            return
        indexes = selection_model.selectedIndexes()
        if not indexes:
            return

        # Valores mostrados (formateados), en orden visual (ya reflejan
        # sort/filter activos porque vienen del proxy via la vista).
        by_row = defaultdict(dict)
        for index in indexes:
            value = index.data(Qt.ItemDataRole.DisplayRole)
            by_row[index.row()][index.column()] = "" if value is None else str(value)

        lines = []
        for row in sorted(by_row):
            columns = by_row[row]
            lines.append("\t".join(columns[col] for col in sorted(columns)))

        QApplication.clipboard().setText("\n".join(lines))

    def _on_query_changed(self, text):
        self.proxy.set_query(text)
        self._update_totals_label()

    def _update_totals_label(self):
        query = self.search_box.text()
        visible = filtering.filter_records(
            self._records, query, self.config.text_fields,
            self.config.amount_fields, self.config.default_amount_field)
        totals = filtering.compute_totals(visible, {c: c for c in self.config.total_columns})
        parts = [f"{col}: ${totals[col]:,.2f}" for col in self.config.total_columns]
        count_part = f"{len(visible)} de {len(self._records)} registro(s)"
        self.totals_label.setText(f"{count_part}   —   " + "   ".join(parts))


class ResultsView(QTabWidget):
    """Visor de resultados: una pestaña por tipo de documento (D13/D15)."""

    # F2.7 (D29/§16): cualquier caja de busqueda de cualquier pestaña cambio -
    # MainWindow lo usa para habilitar/deshabilitar "Guardar filtrado…" en
    # vivo, sin pasar por la maquina de estados AppState (que no sabe de
    # filtros de texto).
    filter_changed = Signal()

    # F2.10 etapa 3: reenvia el UUID elegido en el menu contextual de Facturas.
    desglose_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_DARK_TABLE_STYLESHEET)
        self._panels = {}
        for config in ALL_TABS:
            panel = _ResultsTabPanel(config)
            self._panels[config.key] = panel
            self.addTab(panel, config.title)
            # textChanged manda el texto nuevo (str); filter_changed no toma
            # argumentos - una lambda descarta el str en vez de reenviarlo.
            panel.search_box.textChanged.connect(lambda _text: self.filter_changed.emit())
            panel.desglose_requested.connect(self.desglose_requested)

    def set_result(self, result):
        """Puebla las 3 pestañas a partir de un core.ProcessResult (o None para vaciar)."""
        for config in ALL_TABS:
            records = getattr(result, config.key, []) if result is not None else []
            self._panels[config.key].set_records(records)

    def clear(self):
        self.set_result(None)

    # --- F2.7: exportacion filtrada "espejo del visor" (D29/§16) -------------
    def has_any_active_filter(self):
        """True si AL MENOS una pestaña tiene texto de busqueda activo."""
        return any(p.search_box.text().strip() for p in self._panels.values())

    def active_filter_info(self):
        """Lista de (config.key, query) SOLO para pestañas con filtro activo -
        usada para decidir el sufijo del nombre de archivo (§16.4: sufijo
        legible con UNA pestaña filtrada, generico con varias)."""
        return [
            (p.config.key, p.search_box.text().strip())
            for p in self._panels.values() if p.search_box.text().strip()
        ]

    def filtered_data(self):
        """dict {config.key: registros} - cada pestaña filtrada con SU PROPIO
        query via la MISMA filtering.filter_records() que usa el proxy de la
        tabla (results_proxy.py llama matches_search con los mismos
        parametros), garantizando que exportado == visible (§16.5). Una
        pestaña sin filtro activo devuelve su lista COMPLETA (filter_records
        con query vacio no descarta nada) - asi que llamar esto SIEMPRE,
        filtro activo o no, ya produce el "espejo" pedido en §16.2."""
        return {
            p.config.key: filtering.filter_records(
                p._records, p.search_box.text(), p.config.text_fields,
                p.config.amount_fields, p.config.default_amount_field)
            for p in self._panels.values()
        }

    # --- F2.9: exportacion CSV de la pestaña activa (D43/§18.6) -------------
    def active_tab_export_data(self, all_columns=False):
        """dict con lo necesario para exportar a CSV la pestaña que el
        usuario tiene ABIERTA ahora mismo (currentWidget()), respetando SU
        filtro - reusa la MISMA filtering.filter_records() que filtered_data()
        y el proxy de la tabla, asi que la fidelidad de §16.5 aplica igual:
        lo exportado ES lo que esa pestaña muestra en pantalla.

        `all_columns`: False (default) -> "columns" trae las columnas
        curadas del visor (TabConfig.display_columns, D18). True -> "columns"
        viene en None a proposito - esta capa de UI no conoce las listas
        COMPLETAS de columnas (viven en constants.py via core.py, D43); el
        llamador (main_window) las resuelve con core.full_columns_for_tab().

        Devuelve: {"title", "tab_key", "columns", "rows", "query"}.
        """
        panel = self.currentWidget()
        query = panel.search_box.text()
        rows = filtering.filter_records(
            panel._records, query, panel.config.text_fields,
            panel.config.amount_fields, panel.config.default_amount_field)
        return {
            "title": panel.config.title,
            "tab_key": panel.config.key,
            "columns": None if all_columns else panel.config.display_columns,
            "rows": rows,
            "query": query.strip(),
        }
