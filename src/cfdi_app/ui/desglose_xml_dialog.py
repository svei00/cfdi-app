# --- cfdi_app/ui/desglose_xml_dialog.py ---
"""Dialogo "Ver desglose de este XML" (F2.10 etapa 3, diseño §3.4).

Muestra las lineas de UN comprobante (conceptos del CFDI y, en estados de
cuenta de combustible, una linea por carga), sus totales con el IVA del CFDI y
el del complemento SEPARADOS (D54) y el semaforo de cuadre.

No escribe archivos ni conoce el motor: recibe lineas y fila de cuadre ya
calculadas por reports/desglose_conceptos.py. Si el usuario pulsa "Exportar
este XML…" cierra con accept() y deja `wants_export = True`; quien lo abrio
(main_window) decide donde guardar. Todo el texto va como texto plano (las
descripciones del proveedor pueden traer < > &).
"""
from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QHeaderView, QLabel,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from cfdi_app.reports import desglose_conceptos as dc

_ESTILO_OK = "color: #2E7D32; font-weight: bold;"
_ESTILO_MAL = "color: #C62828; font-weight: bold;"
_ESTILO_AVISO = "color: #B26A00; font-weight: bold;"


class DesgloseXmlDialog(QDialog):
    def __init__(self, lineas, fila_cuadre, parent=None):
        super().__init__(parent)
        self.wants_export = False
        primera = lineas[0]
        self.setWindowTitle(f"Desglose – {primera['factura'] or primera['uuid']}")
        self.resize(1100, 560)

        layout = QVBoxLayout(self)

        cabecera = QLabel(
            f"{primera['factura']}   |   {primera['nombre_emisor']} "
            f"({primera['rfc_emisor']})   |   {primera['fecha_cfdi']}\n"
            f"UUID: {primera['uuid']}")
        cabecera.setTextFormat(Qt.PlainText)
        cabecera.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(cabecera)

        encabezados, filas, numericas = dc.tabla_xml(lineas)
        self.table = QTableWidget(len(filas), len(encabezados))
        self.table.setHorizontalHeaderLabels(encabezados)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        for i, fila in enumerate(filas):
            for j, texto in enumerate(fila):
                item = QTableWidgetItem(texto)  # texto plano, sin rich text
                item.setToolTip(texto)
                if numericas[j]:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, j, item)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, stretch=1)

        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self.table)
        copy_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copy_shortcut.activated.connect(self._copy_selection)

        pie = QLabel("\n".join(dc.texto_pie_xml(dc.resumen_xml(lineas))))
        pie.setTextFormat(Qt.PlainText)
        pie.setStyleSheet("font-weight: bold; padding: 4px;")
        pie.setWordWrap(True)
        layout.addWidget(pie)

        self.cuadre_label = QLabel(self._texto_cuadre(fila_cuadre))
        self.cuadre_label.setTextFormat(Qt.PlainText)
        self.cuadre_label.setWordWrap(True)
        self.cuadre_label.setStyleSheet(self._estilo_cuadre(fila_cuadre))
        layout.addWidget(self.cuadre_label)

        botones = QDialogButtonBox()
        self.export_btn = botones.addButton(
            "Exportar este XML…", QDialogButtonBox.ActionRole)
        botones.addButton("Cerrar", QDialogButtonBox.RejectRole)
        self.export_btn.clicked.connect(self._on_export)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    @staticmethod
    def _texto_cuadre(fila):
        if fila["estatus"] == dc.ESTATUS_OK:
            return ("Cuadre: OK — la suma de las líneas coincide con el Total "
                    "del CFDI" + (" y con el complemento de combustible."
                                  if fila.get("ecc_total") is not None else "."))
        return f"Cuadre: {fila['estatus']} — {fila['detalle']}"

    @staticmethod
    def _estilo_cuadre(fila):
        if fila["estatus"] == dc.ESTATUS_OK:
            return _ESTILO_OK
        if fila["estatus"] == dc.ESTATUS_NO_CUADRA:
            return _ESTILO_MAL
        return _ESTILO_AVISO

    def _on_export(self):
        self.wants_export = True
        self.accept()

    def _copy_selection(self):
        indexes = self.table.selectedIndexes()
        if not indexes:
            return
        por_fila = defaultdict(dict)
        for index in indexes:
            por_fila[index.row()][index.column()] = index.data() or ""
        lineas = ["\t".join(cols[c] for c in sorted(cols))
                  for _, cols in sorted(por_fila.items())]
        QApplication.clipboard().setText("\n".join(lineas))
