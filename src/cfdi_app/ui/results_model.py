# --- cfdi_app/ui/results_model.py ---
# Modelo de tabla Qt para el visor de resultados (ROADMAP.md D13/Sec.11).
#
# REGLA DURA D13: QAbstractTableModel + QTableView. QTableWidget prohibido
# (metería los datos dentro del widget, en vez de en un modelo reutilizable
# que F4 pueda reemplazar por uno respaldado en SQLite sin tocar la vista).
import html

from PySide6.QtCore import QAbstractTableModel, Qt

# Task B1 (docs/design-f2.8...): tooltips en data(), no en la vista - el
# QSortFilterProxyModel reenvia roles automaticamente, asi que funciona con
# sort/filter activos sin cablear nada extra por columna.
_MAX_CONCEPTO_TOOLTIP_LINES = 30


def _escape_tooltip(text):
    # Envuelto en un tag real para que Qt::mightBeRichText lo detecte como
    # HTML y decodifique las entidades al mostrarlo - de lo contrario un
    # tooltip escapado pero NO reconocido como rich text mostraria
    # literalmente "&lt;" en vez de "<". Las descripciones de proveedores
    # traen "<", ">" y "&" con cierta frecuencia (medidas, referencias).
    return f"<span>{html.escape(str(text), quote=False)}</span>"


def _conceptos_tooltip(detalle):
    descripciones = [
        item.get("Descripcion", "") for item in detalle if item.get("Descripcion")
    ]
    if not descripciones:
        return None
    shown = descripciones[:_MAX_CONCEPTO_TOOLTIP_LINES]
    lines = [html.escape(d, quote=False) for d in shown]
    remaining = len(descripciones) - len(shown)
    if remaining > 0:
        lines.append(f"… y {remaining} más")
    return "<span>" + "<br>".join(lines) + "</span>"


class RecordTableModel(QAbstractTableModel):
    """Modelo generico: una lista de dicts + un orden de columnas explicito.

    Se usa igual para Invoices, Nomina y Pagos - cada pestaña del visor solo
    cambia que columnas pide mostrar (ver ui/results_view.py).
    """

    def __init__(self, records, columns, parent=None):
        super().__init__(parent)
        self._records = records
        self._columns = columns

    def rowCount(self, parent=None):
        return len(self._records)

    def columnCount(self, parent=None):
        return len(self._columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        record = self._records[index.row()]
        column = self._columns[index.column()]

        if role == Qt.DisplayRole:
            value = record.get(column)
            if value is None:
                return ""
            if isinstance(value, float):
                return f"{value:,.2f}"
            return str(value)

        if role == Qt.ToolTipRole:
            if column == "Conceptos" and record.get("ConceptosDetalle"):
                return _conceptos_tooltip(record["ConceptosDetalle"])
            value = record.get(column)
            if value is None or value == "":
                return None
            if isinstance(value, float):
                value = f"{value:,.2f}"
            return _escape_tooltip(value)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._columns[section]
        return str(section + 1)

    def record_at(self, row):
        return self._records[row]
