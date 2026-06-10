# --- cfdi_app/ui/results_model.py ---
# Modelo de tabla Qt para el visor de resultados (ROADMAP.md D13/Sec.11).
#
# REGLA DURA D13: QAbstractTableModel + QTableView. QTableWidget prohibido
# (metería los datos dentro del widget, en vez de en un modelo reutilizable
# que F4 pueda reemplazar por uno respaldado en SQLite sin tocar la vista).
from PySide6.QtCore import QAbstractTableModel, Qt


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
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        record = self._records[index.row()]
        value = record.get(self._columns[index.column()])
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:,.2f}"
        return str(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._columns[section]
        return str(section + 1)

    def record_at(self, row):
        return self._records[row]
