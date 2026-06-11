# --- cfdi_app/ui/results_proxy.py ---
# Puente delgado entre la caja de busqueda (Qt) y la logica pura de filtrado
# (cfdi_app.ui.filtering). Este proxy NO reimplementa comparaciones: solo le
# pregunta a matches_search() por cada fila.
from PySide6.QtCore import QSortFilterProxyModel, Qt

from cfdi_app.ui.filtering import matches_search


class RecordFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, text_fields, amount_fields, default_amount_field, parent=None):
        super().__init__(parent)
        self._query = ""
        self._text_fields = text_fields
        self._amount_fields = amount_fields
        self._default_amount_field = default_amount_field

    def set_query(self, query):
        self._query = query
        self.invalidate()  # invalidateFilter()/invalidateRowsFilter() estan deprecados en Qt 6.11

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return True
        record = model.record_at(source_row)
        return matches_search(
            record, self._query, self._text_fields,
            self._amount_fields, self._default_amount_field)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        # Comportamiento por defecto de QSortFilterProxyModel: el encabezado
        # vertical se resuelve vía mapToSource(), por lo que al ordenar o
        # filtrar el numero de fila mostrado queda "pegado" a la posicion
        # ORIGINAL (antes de ordenar) en vez de la posicion visual actual -
        # es el bug que reporto el dueno ("las veintenas junto con el 2...").
        # Se corrige devolviendo la posicion visual (1..N) directamente, sin
        # pasar por el modelo fuente, solo para el encabezado vertical.
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(section + 1)
        return super().headerData(section, orientation, role)
