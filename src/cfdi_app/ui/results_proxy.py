# --- cfdi_app/ui/results_proxy.py ---
# Puente delgado entre la caja de busqueda (Qt) y la logica pura de filtrado
# (cfdi_app.ui.filtering). Este proxy NO reimplementa comparaciones: solo le
# pregunta a matches_search() por cada fila.
from PySide6.QtCore import QSortFilterProxyModel

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
        self.invalidateRowsFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return True
        record = model.record_at(source_row)
        return matches_search(
            record, self._query, self._text_fields,
            self._amount_fields, self._default_amount_field)
