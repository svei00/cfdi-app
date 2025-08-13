# --- cfdi_processor/pagos_parser_20.py ---
# This file contains the parsing logic specifically for CFDI Pagos 2.0 complement.

import xml.etree.ElementTree as ET
import os
from datetime import datetime
from constants import (
    NAMESPACES_CFDI_40, FORMA_PAGO_MAP, TIPO_COMPROBANTE_MAP, USO_CFDI_MAP,
    REGIMEN_FISCAL_RECEPTOR_MAP, PAGOS_COLUMN_ORDER, PAGO_FIELDS_TO_EXTRACT,
    PAGO_DR_FIELDS_TO_EXTRACT, CFDI_COMMON_CHILD_ELEMENTS_TO_EXTRACT, PAGO_DR_TAX_FIELDS
)

# Define the full URIs for relevant namespaces for direct attribute access
CFDI_URI = NAMESPACES_CFDI_40['cfdi']
TFD_URI = NAMESPACES_CFDI_40['tfd']
PAGO20_URI = NAMESPACES_CFDI_40['pago20']


def _initialize_pagos_data_row():
    """
    Initializes a dictionary with all possible Pagos data fields based on PAGOS_COLUMN_ORDER.
    This ensures all columns are present even if not populated by the XML.
    """
    data = {}
    for field in PAGOS_COLUMN_ORDER:
        data[field] = None  # Initialize all fields to None

    # Initialize numeric fields to 0.0 for aggregation
    # These are specific to Pagos and DoctoRelacionado taxes
    for _, _, default_val, col_name in PAGO_FIELDS_TO_EXTRACT:
        if isinstance(default_val, str) and default_val.replace('.', '', 1).isdigit():
            data[col_name] = 0.0
    for _, _, default_val, col_name in PAGO_DR_FIELDS_TO_EXTRACT:
        if isinstance(default_val, str) and default_val.replace('.', '', 1).isdigit():
            data[col_name] = 0.0
    for col_name, (_, _, default_val) in PAGO_DR_TAX_FIELDS.items():
        if isinstance(default_val, str) and default_val.replace('.', '', 1).isdigit():
            data[col_name] = 0.0

    return data


def _extract_pagos_tax_details_dr(docto_relacionado_node, data, namespaces):
    """
    Extracts and aggregates tax details (TrasladosDR, RetencionesDR) from a DoctoRelacionado node.
    """
    # Initialize all tax fields for this DR to 0.0 before summing
    for col_name in PAGO_DR_TAX_FIELDS.keys():
        data[col_name] = 0.0

    # Process TrasladosDR
    for traslado_dr in docto_relacionado_node.findall("./pago20:ImpuestosDR/pago20:TrasladosDR/pago20:TrasladoDR", namespaces):
        impuesto_code = traslado_dr.get("ImpuestoDR", "").strip()
        tipo_factor = traslado_dr.get("TipoFactorDR", "").strip()
        tasa_ocuota = traslado_dr.get("TasaOCuotaDR", "").strip()
        base_str = traslado_dr.get("BaseDR", "0.00").strip()
        importe_str = traslado_dr.get("ImporteDR", "0.00").strip()

        try:
            base_val = float(base_str)
        except (ValueError, TypeError):
            base_val = 0.0
        try:
            importe_val = float(importe_str)
        except (ValueError, TypeError):
            importe_val = 0.0

        if impuesto_code == "002":  # IVA
            if tipo_factor == "Tasa":
                if tasa_ocuota == "0.160000":
                    data["IVA 16 Base"] += base_val
                    data["IVA 16 Importe"] += importe_val
                elif tasa_ocuota == "0.080000":
                    data["IVA 8 Base"] += base_val
                    data["IVA 8 Importe"] += importe_val
                elif tasa_ocuota == "0.000000":  # IVA 0%
                    data["IVA Cero Base"] += base_val
                    data["IVA Cero"] += importe_val
            elif tipo_factor == "Exento":
                data["IVA Excento Base"] += base_val
                data["IVA Excento"] += importe_val
        elif impuesto_code == "003":  # IEPS
            if tipo_factor == "Tasa":
                if tasa_ocuota == "0.030000":
                    data["IEPS 3 Base"] += base_val
                    data["IEPS 3 Importe"] += importe_val
                elif tasa_ocuota == "0.060000":
                    data["IEPS 6 Base"] += base_val
                    data["IEPS 6 Importe"] += importe_val
                elif tasa_ocuota == "0.070000":
                    data["IEPS 7 Base"] += base_val
                    data["IEPS 7 Importe"] += importe_val
                elif tasa_ocuota == "0.080000":
                    data["IEPS 8 Base"] += base_val
                    data["IEPS 8 Importe"] += importe_val
                elif tasa_ocuota == "0.090000":
                    data["IEPS 9 Base"] += base_val
                    data["IEPS 9 Importe"] += importe_val
                elif tasa_ocuota == "0.265000":
                    data["IEPS 26.5 Base"] += base_val
                    data["IEPS 26.5 Importe"] += importe_val
                elif tasa_ocuota == "0.300000":
                    data["IEPS 30 Base"] += base_val
                    data["IEPS 30 Importe"] += importe_val
                elif tasa_ocuota == "0.304000":
                    data["IEPS 30.4 Base"] += base_val
                    data["IEPS 30.4 Importe"] += importe_val
                elif tasa_ocuota == "0.530000":
                    data["IEPS 53 Base"] += base_val
                    data["IEPS 53 Importe"] += importe_val
                elif tasa_ocuota == "1.600000":
                    data["IEPS 160 Base"] += base_val
                    data["IEPS 160 Importe"] += importe_val
                # Add other IEPS rates as needed based on PAGO_DR_TAX_FIELDS
            elif tipo_factor == "Exento":
                data["IEPS Cero Base"] += base_val
                data["IEPS Cero"] += importe_val

    # Process RetencionesDR
    for retencion_dr in docto_relacionado_node.findall("./pago20:ImpuestosDR/pago20:RetencionesDR/pago20:RetencionDR", namespaces):
        impuesto_code = retencion_dr.get("ImpuestoDR", "").strip()
        tasa_ocuota = retencion_dr.get("TasaOCuotaDR", "").strip()
        base_str = retencion_dr.get("BaseDR", "0.00").strip()
        importe_str = retencion_dr.get("ImporteDR", "0.00").strip()

        try:
            base_val = float(base_str)
        except (ValueError, TypeError):
            base_val = 0.0
        try:
            importe_val = float(importe_str)
        except (ValueError, TypeError):
            importe_val = 0.0

        if impuesto_code == "001":  # ISR
            if tasa_ocuota == "0.012500":
                data["Ret ISR 1.25 Base"] += base_val
                data["Ret ISR 1.25 Importe"] += importe_val
            elif tasa_ocuota == "0.100000":
                data["Ret ISR 10 Base"] += base_val
                data["Ret ISR 10 Importe"] += importe_val
        elif impuesto_code == "002":  # IVA
            if tasa_ocuota == "0.040000":
                data["Ret IVA 4 Base"] += base_val
                data["Ret IVA 4 Importe"] += importe_val
            elif tasa_ocuota == "0.106667":
                data["Ret IVA 10.667 Base"] += base_val
                data["Ret IVA 10.667 Importe"] += importe_val
            elif tasa_ocuota == "0.020000":
                data["Ret IVA 2 Base"] += base_val
                data["Ret IVA 2 Importe"] += importe_val
            elif tasa_ocuota == "0.053333":
                data["Ret IVA 5.33 Base"] += base_val
                data["Ret IVA 5.33 Importe"] += importe_val
            elif tasa_ocuota == "0.080000":
                data["Ret IVA 8 Base"] += base_val
                data["Ret IVA 8 Importe"] += importe_val
            elif tasa_ocuota == "0.060000":
                data["Ret IVA 6 Base"] += base_val
                data["Ret IVA 6 Importe"] += importe_val
            elif tasa_ocuota == "0.160000":
                data["Ret IVA 16 Base"] += base_val
                data["Ret IVA 16 Importe"] += importe_val


def parse_cfdi_pago_20(xml_file_path):
    """
    Parses a CFDI 4.0 XML file with a Pagos 2.0 complement.
    Extracts data for each DoctoRelacionado and returns a list of dictionaries,
    where each dictionary represents a row for the Pagos Excel sheet.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Ensure it's a CFDI 4.0 Pago comprobante
        if root.get('Version') != '4.0' or root.get('TipoDeComprobante') != 'P':
            print(
                f"Skipping {os.path.basename(xml_file_path)}: Not a CFDI 4.0 Pago document.")
            return []

        pagos_complement = root.find(".//pago20:Pagos", NAMESPACES_CFDI_40)
        if pagos_complement is None:
            print(
                f"Skipping {os.path.basename(xml_file_path)}: No Pagos 2.0 complement found.")
            return []

        all_pagos_data_rows = []

        # Extract common CFDI Comprobante and Timbre Fiscal Digital data
        base_cfdi_data = _initialize_pagos_data_row()
        # Internal type for main.py to categorize
        base_cfdi_data["CFDI_Type"] = "Pago"

        # Comprobante attributes
        base_cfdi_data["Version CFDI"] = root.get("Version", "").strip()
        base_cfdi_data["Serie CFDI"] = root.get("Serie", '').strip()
        base_cfdi_data["Folio CFDI"] = root.get("Folio", '').strip()
        base_cfdi_data["Fecha Emision"] = root.get("Fecha", "").strip()
        base_cfdi_data["TipoComprobante"] = TIPO_COMPROBANTE_MAP.get(
            root.get("TipoDeComprobante", ""), "Desconocido")
        base_cfdi_data["Lugar de Expedicion CFDI"] = root.get(
            "LugarExpedicion", "").strip()
        # Indicate presence of Pagos complement
        base_cfdi_data["Complementos Comprobante"] = "Pagos"
        base_cfdi_data["Archivo XML"] = os.path.basename(xml_file_path)

        # Emisor data
        emisor_node = root.find("cfdi:Emisor", NAMESPACES_CFDI_40)
        if emisor_node is not None:
            base_cfdi_data["RFC Emisor CFDI"] = emisor_node.get(
                "Rfc", "").strip()
            base_cfdi_data["Nombre Emisor CFDI"] = emisor_node.get(
                "Nombre", "").strip()
            regimen_emisor_code = emisor_node.get("RegimenFiscal", "").strip()
            base_cfdi_data[
                "Regimen Fiscal Emisor CFDI"] = f"{regimen_emisor_code} - {REGIMEN_FISCAL_RECEPTOR_MAP.get(regimen_emisor_code, 'Desconocido')}" if regimen_emisor_code else None

        # Receptor data
        receptor_node = root.find("cfdi:Receptor", NAMESPACES_CFDI_40)
        if receptor_node is not None:
            base_cfdi_data["RFC Receptor CFDI"] = receptor_node.get(
                "Rfc", "").strip()
            base_cfdi_data["Nombre Receptor CFDI"] = receptor_node.get(
                "Nombre", "").strip()
            uso_cfdi_code = receptor_node.get("UsoCFDI", "").strip()
            # This line already existed and correctly extracts the UsoCFDI
            base_cfdi_data["UsoCFDI CFDI"] = f"{uso_cfdi_code} - {USO_CFDI_MAP.get(uso_cfdi_code, 'Desconocido')}" if uso_cfdi_code else None
            base_cfdi_data["DomicilioFiscalReceptor CFDI"] = receptor_node.get(
                'DomicilioFiscalReceptor', '').strip()
            regimen_receptor_code = receptor_node.get(
                'RegimenFiscalReceptor', '').strip()
            base_cfdi_data[
                "Regimen Fiscal Receptor CFDI"] = f"{regimen_receptor_code} - {REGIMEN_FISCAL_RECEPTOR_MAP.get(regimen_receptor_code, 'Desconocido')}" if regimen_receptor_code else None
            base_cfdi_data["ResidenciaFiscal CFDI"] = receptor_node.get(
                "ResidenciaFiscal", "").strip()
            base_cfdi_data["NumRegIdTrib CFDI"] = receptor_node.get(
                "NumRegIdTrib", "").strip()

        # Timbre Fiscal Digital data
        timbre_fiscal_digital = root.find(
            ".//tfd:TimbreFiscalDigital", NAMESPACES_CFDI_40)
        if timbre_fiscal_digital is not None:
            base_cfdi_data["UUID CFDI"] = timbre_fiscal_digital.get(
                "UUID", "").strip()
            base_cfdi_data["Fecha Timbrado"] = timbre_fiscal_digital.get(
                "FechaTimbrado", "").strip()
            base_cfdi_data["No. Certificado SAT"] = timbre_fiscal_digital.get(
                "NoCertificadoSAT", "").strip()
            # No. Certificado Emisor is from Comprobante's NoCertificado
            base_cfdi_data["No. Certificado Emisor"] = root.get(
                "NoCertificado", "").strip()

        # Format Dates (Fecha Emision: DD/MM/YYYY, Fecha Timbrado: DD/MM/YYYY HH:MM:SS)
        if base_cfdi_data["Fecha Emision"]:
            try:
                dt_obj = datetime.strptime(
                    base_cfdi_data["Fecha Emision"], "%Y-%m-%dT%H:%M:%S")
                base_cfdi_data["Fecha Emision"] = dt_obj.strftime("%d/%m/%Y")
            except ValueError:
                pass
        if base_cfdi_data["Fecha Timbrado"]:
            try:
                dt_obj = datetime.strptime(
                    base_cfdi_data["Fecha Timbrado"], "%Y-%m-%dT%H:%M:%S")
                base_cfdi_data["Fecha Timbrado"] = dt_obj.strftime(
                    "%d/%m/%Y %H:%M:%S")
            except ValueError:
                pass

        # Extract Totales from pago20:Pagos
        totales_node = pagos_complement.find(
            "./pago20:Totales", NAMESPACES_CFDI_40)
        if totales_node is not None:
            for _, attr_name, default_val, col_name in PAGO_FIELDS_TO_EXTRACT:
                if col_name in PAGOS_COLUMN_ORDER and attr_name in totales_node.attrib:
                    value_str = totales_node.get(
                        attr_name, default_val).strip()
                    try:
                        base_cfdi_data[col_name] = float(value_str)
                    except (ValueError, TypeError):
                        # Ensure numeric default
                        base_cfdi_data[col_name] = 0.0

        # Iterate through each pago20:Pago element
        for pago_node in pagos_complement.findall("./pago20:Pago", NAMESPACES_CFDI_40):
            # Extract data from the current pago20:Pago element
            current_pago_data = {}
            for _, attr_name, default_val, col_name in PAGO_FIELDS_TO_EXTRACT:
                if col_name in PAGOS_COLUMN_ORDER and attr_name in pago_node.attrib:
                    value_str = pago_node.get(attr_name, default_val).strip()
                    if col_name == "FormaDePagoP":
                        current_pago_data[
                            col_name] = f"{value_str} - {FORMA_PAGO_MAP.get(value_str, 'Desconocido')}" if value_str else None
                    elif col_name == "FechaPago":
                        try:
                            dt_obj = datetime.strptime(
                                value_str, "%Y-%m-%dT%H:%M:%S")
                            current_pago_data[col_name] = dt_obj.strftime(
                                "%d/%m/%Y %H:%M:%S")
                        except ValueError:
                            # Keep original if parsing fails
                            current_pago_data[col_name] = value_str
                    # Check if it's a numeric field
                    elif isinstance(default_val, str) and default_val.replace('.', '', 1).isdigit():
                        try:
                            current_pago_data[col_name] = float(value_str)
                        except (ValueError, TypeError):
                            current_pago_data[col_name] = 0.0
                    else:
                        current_pago_data[col_name] = value_str
                else:
                    # Ensure all fields are initialized
                    current_pago_data[col_name] = None

            # Iterate through each pago20:DoctoRelacionado element within the current pago20:Pago
            for docto_relacionado_node in pago_node.findall("./pago20:DoctoRelacionado", NAMESPACES_CFDI_40):
                row_data = base_cfdi_data.copy()  # Start with base CFDI data

                # Add current pago20:Pago data
                for key, value in current_pago_data.items():
                    if key in PAGOS_COLUMN_ORDER:  # Only add if it's in the final column order
                        row_data[key] = value

                # Extract data from the current pago20:DoctoRelacionado element
                # --- MODIFICATION START ---
                # Add the MetodoDePagoDR field, which was not previously being extracted.
                row_data["MetodoDePagoDR"] = docto_relacionado_node.get(
                    "MetodoDePagoDR", "").strip()
                # --- MODIFICATION END ---
                for _, attr_name, default_val, col_name in PAGO_DR_FIELDS_TO_EXTRACT:
                    if col_name in PAGOS_COLUMN_ORDER and attr_name in docto_relacionado_node.attrib:
                        value_str = docto_relacionado_node.get(
                            attr_name, default_val).strip()
                        if isinstance(default_val, str) and default_val.replace('.', '', 1).isdigit():
                            try:
                                row_data[col_name] = float(value_str)
                            except (ValueError, TypeError):
                                row_data[col_name] = 0.0
                        else:
                            row_data[col_name] = value_str
                    else:
                        # Ensure all fields are initialized
                        row_data[col_name] = None

                # Extract and aggregate tax details for this DoctoRelacionado
                _extract_pagos_tax_details_dr(
                    docto_relacionado_node, row_data, NAMESPACES_CFDI_40)

                all_pagos_data_rows.append(row_data)

        if not all_pagos_data_rows:
            print(
                f"No DoctoRelacionado found in Pagos 2.0 complement for {os.path.basename(xml_file_path)}. Adding a placeholder row.")
            # If there's a Pagos complement but no DoctoRelacionado, add a row with just base CFDI data
            placeholder_data = base_cfdi_data.copy()
            # Ensure all Pagos-specific fields are None for this placeholder
            for _, _, _, col_name in PAGO_FIELDS_TO_EXTRACT:
                placeholder_data[col_name] = None
            for _, _, _, col_name in PAGO_DR_FIELDS_TO_EXTRACT:
                placeholder_data[col_name] = None
            for col_name in PAGO_DR_TAX_FIELDS.keys():
                placeholder_data[col_name] = None
            all_pagos_data_rows.append(placeholder_data)

        return all_pagos_data_rows

    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file_path}: {e}")
        return []
    except Exception as e:
        print(
            f"An unexpected error occurred while processing {xml_file_path}: {e}")
        return []
