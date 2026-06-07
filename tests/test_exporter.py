"""
Pruebas de excel_exporter (ROADMAP.md Sec.6.6 / 6.9 punto 3).

Antes de F2, export_to_excel atrapaba TODAS las excepciones internamente e
imprimia un mensaje, por lo que un archivo destino abierto en Excel
(PermissionError) resultaba en "exito" reportado por la capa superior. Ahora
la excepcion debe propagarse para que la UI/CLI la muestren correctamente.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cfdi_app.exporters import excel_exporter  # noqa: E402

SAMPLE_INVOICE = [{
    "CFDI_Type": "Invoice",
    "RFC Emisor": "XAXX010101000",
    "RFC Receptor": "XAXX010101000",
}]


class TestExporterPropagatesErrors(unittest.TestCase):
    def test_permission_error_propagates_not_swallowed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "salida.xlsx")
            with patch.object(excel_exporter.pd, "ExcelWriter",
                             side_effect=PermissionError("archivo en uso")):
                with self.assertRaises(PermissionError):
                    excel_exporter.export_to_excel(SAMPLE_INVOICE, [], [], output_path)

    def test_no_data_does_not_raise_and_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "vacio.xlsx")
            excel_exporter.export_to_excel([], [], [], output_path)
            self.assertFalse(os.path.exists(output_path))

    def test_real_export_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "real.xlsx")
            excel_exporter.export_to_excel(SAMPLE_INVOICE, [], [], output_path)
            self.assertTrue(os.path.exists(output_path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
