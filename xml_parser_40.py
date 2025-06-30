# --- cfdi_processor/xml_parser_40.py ---
# This file contains the parsing logic specifically for CFDI 4.0 XML files.

import xml.etree.ElementTree as ET
import os
from datetime import datetime
# Corrected import: Changed from relative 'from .constants import' to direct 'from constants import'
from constants import (
    NAMESPACES_CFDI_40, TIPO_COMPROBANTE_MAP, FORMA_PAGO_MAP, METODO_PAGO_MAP,
    USO_CFDI_MAP, REGIMEN_FISCAL_RECEPTOR_MAP, INVOICE_COLUMN_ORDER,
    CFDI_COMMON_CHILD_ELEMENTS_TO_EXTRACT, NOMINA_FIELDS_TO_EXTRACT,
    FUEL_PROD_SERV_CODES, FUEL_UNITS, FUEL_KEYWORDS
)

# Define the full URI for the CFDI namespace for direct attribute access
CFDI_URI = NAMESPACES_CFDI_40['cfdi']
TFD_URI = NAMESPACES_CFDI_40['tfd']
IEDU_URI = NAMESPACES_CFDI_40['iedu']
IMPLOCAL_URI = NAMESPACES_CFDI_40['implocal']


def _initialize_cfdi_data(cfdi_version="4.0", cfdi_type_category="Invoice"):
    """
    Initializes a dictionary with all possible CFDI data fields based on INVOICE_COLUMN_ORDER.
    This ensures all columns are present even if not populated by the XML.
    """
    data = {}
    for field in INVOICE_COLUMN_ORDER:
        data[field] = None  # Initialize all fields to None

    # Set initial version and type based on input parameters
    data["Version"] = cfdi_version
    data["CFDI_Type"] = cfdi_type_category

    # Initialize specific numeric fields to 0.0 for aggregation
    data["SubTotal"] = "0.00"
    data["Descuento"] = "0.00"
    data["Total IEPS"] = "0.00"
    data["IVA 16%"] = "0.00"
    data["Retenido IVA"] = "0.00"
    data["Retenido ISR"] = "0.00"
    data["ISH"] = "0.00"
    data["Total"] = "0.00"
    data["Total Trasladados"] = "0.00"
    data["Total Retenidos"] = "0.00"
    data["Total LocalTrasladado"] = "0.00"
    data["Total LocalRetenido"] = "0.00"
    data["IEPS 3%"] = "0.00"
    data["IEPS 6%"] = "0.00"
    data["IEPS 7%"] = "0.00"
    data["IEPS 8%"] = "0.00"
    data["IEPS 9%"] = "0.00"
    data["IEPS 26.5%"] = "0.00"
    data["IEPS 30%"] = "0.00"
    data["IEPS 30.4%"] = "0.00"
    data["IEPS 53%"] = "0.00"
    data["IEPS 160%"] = "0.00"
    data["IVA 8%"] = "0.00"
    data["IVA Ret 6%"] = "0.00"
    # Used for internal calculation before setting 'Conceptos' field
    data["Conceptos_Importe_Sum"] = 0.0

    return data


def _extract_tax_details(root, data, namespaces):
    """
    Extracts and aggregates various tax details (IVA, IEPS, Retenidos, Local Taxes) from XML.
    Correctly extracts TotalImpuestosTrasladados and TotalImpuestosRetenidos
    from the global cfdi:Impuestos element's attributes.
    """
    # --- Extract TotalImpuestosTrasladados and TotalImpuestosRetenidos from global cfdi:Impuestos attributes ---
    global_impuestos_element = root.find("./cfdi:Impuestos", namespaces)

    if global_impuestos_element is not None:
        # Directly get the attributes from the global cfdi:Impuestos element
        total_trasladados_str = global_impuestos_element.get(
            "TotalImpuestosTrasladados", "0.00").strip()
        total_retenidos_str = global_impuestos_element.get(
            "TotalImpuestosRetenidos", "0.00").strip()

        try:
            data["Total Trasladados"] = f"{float(total_trasladados_str):.2f}"
        except (ValueError, TypeError):
            data["Total Trasladados"] = "0.00"

        try:
            data["Total Retenidos"] = f"{float(total_retenidos_str):.2f}"
        except (ValueError, TypeError):
            data["Total Retenidos"] = "0.00"
    else:
        # If no global cfdi:Impuestos element, these totals are zero
        data["Total Trasladados"] = "0.00"
        data["Total Retenidos"] = "0.00"

    # --- Process Specific Traslados (IVA, IEPS) from Conceptos ONLY ---
    # This section sums up the individual tax amounts per concept.
    for concepto_traslado in root.findall(".//cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado", namespaces):
        impuesto_code = concepto_traslado.get("Impuesto", "").strip()
        tipo_factor = concepto_traslado.get("TipoFactor", "").strip()
        tasa_ocuota = concepto_traslado.get("TasaOCuota", "").strip()
        importe_str = concepto_traslado.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.00

        if impuesto_code == "002" and tipo_factor == "Tasa":  # IVA
            if tasa_ocuota == "0.160000":
                data["IVA 16%"] = f"{float(data.get('IVA 16%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.080000":
                data["IVA 8%"] = f"{float(data.get('IVA 8%', '0.00')) + importe:.2f}"
        elif impuesto_code == "003" and tipo_factor == "Tasa":  # IEPS
            # Total IEPS will be the sum of all IEPS rates
            data["Total IEPS"] = f"{float(data.get('Total IEPS', '0.00')) + importe:.2f}"
            if tasa_ocuota == "0.030000":
                data["IEPS 3%"] = f"{float(data.get('IEPS 3%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.060000":
                data["IEPS 6%"] = f"{float(data.get('IEPS 6%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.070000":
                data["IEPS 7%"] = f"{float(data.get('IEPS 7%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.080000":
                data["IEPS 8%"] = f"{float(data.get('IEPS 8%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.090000":
                data["IEPS 9%"] = f"{float(data.get('IEPS 9%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.265000":
                data["IEPS 26.5%"] = f"{float(data.get('IEPS 26.5%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.300000":
                data["IEPS 30%"] = f"{float(data.get('IEPS 30%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.304000":  # Specific IEPS rate
                data["IEPS 30.4%"] = f"{float(data.get('IEPS 30.4%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.530000":
                data["IEPS 53%"] = f"{float(data.get('IEPS 53%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "1.600000":
                data["IEPS 160%"] = f"{float(data.get('IEPS 160%', '0.00')) + importe:.2f}"

    # --- Process Specific Retenciones (ISR, IVA) from Conceptos ONLY ---
    for concepto_retencion in root.findall(".//cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Retenciones/cfdi:Retencion", namespaces):
        impuesto_code = concepto_retencion.get("Impuesto", "").strip()
        importe_str = concepto_retencion.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.00

        if impuesto_code == "001":  # ISR
            data["Retenido ISR"] = f"{float(data.get('Retenido ISR', '0.00')) + importe:.2f}"
        elif impuesto_code == "002":  # IVA
            data["Retenido IVA"] = f"{float(data.get('Retenido IVA', '0.00')) + importe:.2f}"
            tasa_ocuota_ret = concepto_retencion.get("TasaOCuota", "").strip()
            if tasa_ocuota_ret == "0.060000":  # Specific IVA Retenido rate
                data["IVA Ret 6%"] = f"{float(data.get('IVA Ret 6%', '0.00')) + importe:.2f}"

    # --- Process Local Taxes (ISH, Total LocalTrasladado, Total LocalRetenido) ---
    total_local_trasladado_sum = 0.0
    for traslado_local in root.findall(".//implocal:ImpuestosLocales/implocal:TrasladosLocales", namespaces):
        imp_loc_trasladado = traslado_local.get("ImpLocTrasladado", "").strip()
        importe_str = traslado_local.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.00

        if imp_loc_trasladado == "ISH":
            data["ISH"] = f"{float(data.get('ISH', '0.00')) + importe:.2f}"
        total_local_trasladado_sum += importe

    data["Total LocalTrasladado"] = f"{total_local_trasladado_sum:.2f}"

    total_local_retenido_sum = 0.0
    for retencion_local in root.findall(".//implocal:ImpuestosLocales/implocal:RetencionesLocales", namespaces):
        importe_str = retencion_local.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.00

        total_local_retenido_sum += importe
    data["Total LocalRetenido"] = f"{total_local_retenido_sum:.2f}"


def _extract_iedu_data(root, data, namespaces):
    """
    Extracts Specific Data from IEDU Complement.
    This function expects the root of the XML (cfdi:Comprobante) and navigates from there.
    """
    # Corrected XPath to find iedu:instEducativas nested under cfdi:Concepto/cfdi:ComplementoConcepto
    iedu_complement = root.find(
        ".//cfdi:Concepto/cfdi:ComplementoConcepto/iedu:instEducativas", namespaces)
    if iedu_complement is not None:
        data["CURP Dependiente"] = iedu_complement.get("CURP", "").strip()
        data["Nivel Educativo"] = iedu_complement.get(
            "nivelEducativo", "").strip()
        data["Nombre Dependiente"] = iedu_complement.get(
            "nombreAlumno", "").strip()


def parse_cfdi_40_invoice(xml_file_path):
    """
    Parses a single CFDI 4.0 XML invoice file, extracts specified fields (data),
    and determines its type (Invoice or Nomina).

    Args:
        xml_file_path (str): Path to the XML file to be parsed.

    Returns:
        dict: A dictionary containing the extracted data from the XML file.
              Including a "CFDI_Type" key indicating whether it's an "Invoice" or "Nomina".
        None: If the XML file is not valid or does not match expected structure.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Determine if it's a Nomina or Invoice based on TipoDeComprobante and Nomina complement presence
        tipo_de_comprobante = root.get('TipoDeComprobante')
        cfdi_type_category = "Invoice"  # Default category

        if tipo_de_comprobante == 'N' and root.find('cfdi:Complemento/nomina12:Nomina', NAMESPACES_CFDI_40) is not None:
            cfdi_type_category = "Nomina"
        # For "I" (Ingreso) it's a standard Invoice. Other types are generally treated similarly for now.
        elif tipo_de_comprobante in ['I', 'E', 'T', 'P', 'D']:
            if tipo_de_comprobante == 'I':
                cfdi_type_category = "Invoice"
            else:
                # Broadly categorize other comprobante types as Invoice
                cfdi_type_category = "Invoice"

        data = _initialize_cfdi_data(
            cfdi_version="4.0", cfdi_type_category=cfdi_type_category)

        # --- Explicitly Extract Root-Level CFDI Comprobante Attributes ---
        data["Serie"] = root.get("Serie", '').strip()
        data["Folio"] = root.get("Folio", '').strip()
        data["Fecha Emision"] = root.get("Fecha", "").strip()
        data["Sello"] = root.get("Sello", "").strip()
        data["NoCertificado"] = root.get("NoCertificado", "").strip()
        data["Certificado"] = root.get("Certificado", "").strip()

        subtotal_str = root.get("SubTotal", "0.00").strip()
        data["SubTotal"] = f"{float(subtotal_str):.2f}" if subtotal_str else "0.00"

        descuento_str = root.get("Descuento", "0.00").strip()
        data["Descuento"] = f"{float(descuento_str):.2f}" if descuento_str else "0.00"

        total_str = root.get("Total", "0.00").strip()
        data["Total"] = f"{float(total_str):.2f}" if total_str else "0.00"

        data["Moneda"] = root.get("Moneda", "").strip()
        data["Tipo De Cambio"] = root.get("TipoCambio", "1.0").strip()

        forma_pago_code = root.get("FormaPago", "").strip()
        data["FormaDePago"] = f"{forma_pago_code} - {FORMA_PAGO_MAP.get(forma_pago_code, 'Desconocido')}" if forma_pago_code else None

        metodo_pago_code = root.get("MetodoPago", "").strip()
        data["Metodo de Pago"] = f"{metodo_pago_code} - {METODO_PAGO_MAP.get(metodo_pago_code, 'Desconocido')}" if metodo_pago_code else None

        data["Tipo"] = TIPO_COMPROBANTE_MAP.get(
            tipo_de_comprobante, "Desconocido")
        data["LugarDeExpedicion"] = root.get("LugarExpedicion", "").strip()
        data["Condicion de Pago"] = root.get("CondicionesDePago", "").strip()
        data["NumCtaPago"] = root.get("NumCtaPago", "").strip()
        data["Exportacion"] = root.get(
            "Exportacion", "").strip()  # CFDI 4.0 specific

        # --- Extract Common CFDI Child Elements ---
        for xpath, attr_name, default_val, col_name in CFDI_COMMON_CHILD_ELEMENTS_TO_EXTRACT:
            element = root.find(xpath, NAMESPACES_CFDI_40)
            if element is not None:
                value = element.get(attr_name, default_val).strip() if attr_name else \
                    element.text.strip() if element.text is not None else default_val
            else:
                value = default_val
            data[col_name] = value

        # --- UsoCFDI mapping (from Receptor) ---
        receptor_node = root.find("cfdi:Receptor", NAMESPACES_CFDI_40)
        if receptor_node is not None:
            uso_cfdi_code = receptor_node.get("UsoCFDI", "").strip()
            data["UsoCFDI"] = f"{uso_cfdi_code} - {USO_CFDI_MAP.get(uso_cfdi_code, 'Desconocido')}" if uso_cfdi_code else None
            # CFDI 4.0 specific Receptor attributes
            data["DomicilioFiscalReceptor"] = receptor_node.get(
                'DomicilioFiscalReceptor', '').strip()
            regimen_receptor_code = receptor_node.get(
                'RegimenFiscalReceptor', '').strip()
            data["RegimenFiscalReceptor"] = f"{regimen_receptor_code} - {REGIMEN_FISCAL_RECEPTOR_MAP.get(regimen_receptor_code, 'Desconocido')}" if regimen_receptor_code else None
        else:
            data["UsoCFDI"] = None
            data["DomicilioFiscalReceptor"] = None
            data["RegimenFiscalReceptor"] = None

        # --- Extract Timbre Fiscal Digital Attributes ---
        timbre_fiscal_digital = root.find(
            ".//tfd:TimbreFiscalDigital", NAMESPACES_CFDI_40)
        if timbre_fiscal_digital is not None:
            data["UUID"] = timbre_fiscal_digital.get("UUID", "").strip()
            data["Fecha Timbrado"] = timbre_fiscal_digital.get(
                "FechaTimbrado", "").strip()
            data["RfcProvCertif"] = timbre_fiscal_digital.get(
                "RfcProvCertif", "").strip()
            data["SelloSAT"] = timbre_fiscal_digital.get(
                "SelloSAT", "").strip()
            data["NoCertificadoSAT"] = timbre_fiscal_digital.get(
                "NoCertificadoSAT", "").strip()

        # Handle merged "Conceptos" from multiple Concepto nodes
        descriptions = []
        for concepto in root.findall(".//cfdi:Concepto", NAMESPACES_CFDI_40):
            description = concepto.get('Descripcion', '').strip()
            if description:
                descriptions.append(description)

            # Sum Importe from Conceptos for internal use (if needed for validation/cross-check)
            importe = concepto.get('Importe')
            if importe:
                try:
                    data["Conceptos_Importe_Sum"] += float(importe)
                except ValueError:
                    pass
        data['Conceptos'] = ' | '.join(descriptions) if descriptions else None

        # Extract and aggregate tax details (common function for 3.3/4.0 as tax structure is similar for common taxes)
        # Pass 4.0 namespaces
        _extract_tax_details(root, data, NAMESPACES_CFDI_40)

        # Nomina 1.2 complement specific parsing
        detected_complements = []
        nomina_complement = root.find(
            './/cfdi:Complemento/nomina12:Nomina', NAMESPACES_CFDI_40)
        if nomina_complement is not None:
            data['CFDI_Type'] = 'Nomina'
            detected_complements.append('NOMINA')
            for xpath, attr_name, default_val, col_name in NOMINA_FIELDS_TO_EXTRACT:
                element = root.find(xpath, NAMESPACES_CFDI_40)
                if element is not None:
                    value = element.get(attr_name, default_val).strip() if attr_name else \
                        element.text.strip() if element.text is not None else default_val
                else:
                    value = default_val
                data[col_name] = value

            # Calculate TotalGravado and TotalExcento from Percepciones
            total_gravado_percepciones = 0.0
            total_exento_percepciones = 0.0
            for percepcion in root.findall(".//nomina12:Percepcion", NAMESPACES_CFDI_40):
                importe_gravado_str = percepcion.get(
                    "ImporteGravado", "0.00").strip()
                importe_exento_str = percepcion.get(
                    "ImporteExento", "0.00").strip()

                try:
                    total_gravado_percepciones += float(importe_gravado_str)
                except (ValueError, TypeError):
                    pass
                try:
                    total_exento_percepciones += float(importe_exento_str)
                except (ValueError, TypeError):
                    pass
            data['TotalGravado'] = f"{total_gravado_percepciones:.2f}"
            data['TotalExcento'] = f"{total_exento_percepciones:.2f}"

            # Calculate TotalDeducciones and TotalOtrosPagos from their direct nodes if available
            total_otras_deducciones_node = nomina_complement.find(
                ".//nomina12:Deducciones", NAMESPACES_CFDI_40)
            if total_otras_deducciones_node is not None:
                total_otras_ded_str = total_otras_deducciones_node.get(
                    "TotalOtrasDeducciones", "0.00").strip()
                try:
                    data['TotalDeducciones'] = f"{float(total_otras_ded_str):.2f}"
                except (ValueError, TypeError):
                    data['TotalDeducciones'] = "0.00"

            total_otros_pagos_node = nomina_complement.find(
                ".//nomina12:OtrosPagos", NAMESPACES_CFDI_40)
            if total_otros_pagos_node is not None:
                # This attribute is directly on nomina12:Nomina
                total_otros_pag_str = nomina_complement.get(
                    "TotalOtrosPagos", "0.00").strip()
                try:
                    data['TotalOtrosPagos'] = f"{float(total_otros_pag_str):.2f}"
                except (ValueError, TypeError):
                    data['TotalOtrosPagos'] = "0.00"

        else:  # Default to Invoice if no Nomina complement is found
            data['CFDI_Type'] = 'Invoice'
            # Ensure Nomina specific fields are explicitly None for non-Nomina CFDI
            for _, _, _, col_name in NOMINA_FIELDS_TO_EXTRACT:
                data[col_name] = None
            data['TotalGravado'] = None
            data['TotalExcento'] = None
            data['TotalDeducciones'] = None
            data['TotalOtrosPagos'] = None

        # Detect IEDU complement
        iedu_complement = root.find(
            './/cfdi:Concepto/cfdi:ComplementoConcepto/iedu:instEducativas', NAMESPACES_CFDI_40)
        if iedu_complement is not None:
            detected_complements.append('IEDU')
            _extract_iedu_data(root, data, NAMESPACES_CFDI_40)

        # Detect IMPLOCAL complement
        if root.find('.//cfdi:Complemento/implocal:ImpuestosLocales', NAMESPACES_CFDI_40) is not None:
            detected_complements.append('IMPLOCAL')

        # Set the complement column
        data["Complemento"] = ", ".join(
            detected_complements) if detected_complements else None

        # "Archivo XML" (filename)
        data['Archivo XML'] = os.path.basename(xml_file_path)

        # --- Combustible Detection Logic ---
        combustible_detected = False
        for concepto in root.findall(".//cfdi:Concepto", NAMESPACES_CFDI_40):
            clave_prod_serv = concepto.get("ClaveProdServ", "").strip()
            unidad = concepto.get("ClaveUnidad", "").upper().strip()
            description = concepto.get("Descripcion", "").upper().strip()

            if clave_prod_serv in FUEL_PROD_SERV_CODES:
                combustible_detected = True
                break
            if unidad in FUEL_UNITS and any(keyword in description for keyword in FUEL_KEYWORDS):
                combustible_detected = True
                break
        data["Combustible"] = "Si   " if combustible_detected else "No"
        # --- End Combustible Detection Logic ---

        # Extract Serie and Folio to create the merged "Factura" field
        serie = root.get("Serie", '').strip()
        folio = root.get("Folio", '').strip()
        if serie and folio:
            data['Factura'] = f"{serie}-{folio}"
        elif folio:
            data['Factura'] = folio
        else:
            data['Factura'] = None

        # Placeholders for fields requiring external logic or not directly in the XML
        data["Verificado ó Asoc."] = ""
        data["Estado SAT"] = ""
        data["EstadoPago"] = ""
        data["FechaPago"] = ""

        # Emisor/Receptor Addresses/Location (Placeholders)
        data["Direccion Emisor"] = ""
        data["Localidad Emisor"] = ""
        data["Direccion Receptor"] = ""
        data["Localidad Receptor"] = ""

        # --- Format Dates for consistency with Excel Export ---
        if data["Fecha Emision"]:
            try:
                dt_obj = datetime.strptime(
                    data["Fecha Emision"], "%Y-%m-%dT%H:%M:%S")
                data["Fecha Emision"] = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                pass

        if data["Fecha Timbrado"]:
            try:
                dt_obj = datetime.strptime(
                    data["Fecha Timbrado"], "%Y-%m-%dT%H:%M:%S")
                data["Fecha Timbrado"] = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                pass

        return data

    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file_path}: {e}")
        return None
    except Exception as e:
        print(
            f"An unexpected error occurred while processing {xml_file_path}: {e}")
        return None
