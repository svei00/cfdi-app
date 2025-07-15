# --- cfdi_processor/xml_parser_33.py ---
# This file contains the parsing logic specifically for CFDI 3.3 XML files.

import xml.etree.ElementTree as ET
import os
from datetime import datetime
from constants import (
    NAMESPACES_CFDI_33, TIPO_COMPROBANTE_MAP, FORMA_PAGO_MAP, METODO_PAGO_MAP,
    USO_CFDI_MAP, REGIMEN_FISCAL_RECEPTOR_MAP, INVOICE_COLUMN_ORDER,
    CFDI_COMMON_CHILD_ELEMENTS_TO_EXTRACT, NOMINA_FIELDS_TO_EXTRACT,
    FUEL_PROD_SERV_CODES, FUEL_UNITS, FUEL_KEYWORDS
)

# Define the full URI for the CFDI namespace for direct attribute access (for CFDI 3.3)
CFDI_URI_33 = NAMESPACES_CFDI_33['cfdi']
# TimbreFiscalDigital namespace is consistent
TFD_URI = NAMESPACES_CFDI_33['tfd']
IEDU_URI = NAMESPACES_CFDI_33['iedu']  # IEDU namespace is consistent
# ImpLocal namespace is consistent
IMPLOCAL_URI = NAMESPACES_CFDI_33['implocal']


def _initialize_cfdi_data(cfdi_version="3.3", cfdi_type_category="Invoice"):
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

    # Initialize specific numeric fields to 0.0 for aggregation (as actual floats)
    data["SubTotal"] = 0.0
    data["Descuento"] = 0.0
    data["Total IEPS"] = 0.0
    data["IVA 16%"] = 0.0
    data["Retenido IVA"] = 0.0
    data["Retenido ISR"] = 0.0
    data["ISH"] = 0.0
    data["Total"] = 0.0
    data["Total Trasladados"] = 0.0
    data["Total Retenidos"] = 0.0
    data["Total LocalTrasladado"] = 0.0
    data["Total LocalRetenido"] = 0.0
    data["IEPS 3%"] = 0.0
    data["IEPS 6%"] = 0.0
    data["IEPS 7%"] = 0.0
    data["IEPS 8%"] = 0.0
    data["IEPS 9%"] = 0.0
    data["IEPS 26.5%"] = 0.0
    data["IEPS 30%"] = 0.0
    data["IEPS 30.4%"] = 0.0
    data["IEPS 53%"] = 0.0
    data["IEPS 160%"] = 0.0
    data["IVA 8%"] = 0.0
    data["IVA Ret 6%"] = 0.0
    data["Conceptos_Importe_Sum"] = 0.0

    return data


def _extract_tax_details(root, data, namespaces):
    """
    Extracts and aggregates various tax details (IVA, IEPS, Retenidos, Local Taxes) from XML.
    This function is designed to be compatible with both CFDI 3.3 and 4.0 tax structures.
    """
    # --- Extract TotalImpuestosTrasladados and TotalImpuestosRetenidos from global cfdi:Impuestos attributes ---
    global_impuestos_element = root.find("./cfdi:Impuestos", namespaces)

    if global_impuestos_element is not None:
        total_trasladados_str = global_impuestos_element.get(
            "TotalImpuestosTrasladados", "0.00").strip()
        total_retenidos_str = global_impuestos_element.get(
            "TotalImpuestosRetenidos", "0.00").strip()

        try:
            data["Total Trasladados"] = float(total_trasladados_str)
        except (ValueError, TypeError):
            data["Total Trasladados"] = 0.0

        try:
            data["Total Retenidos"] = float(total_retenidos_str)
        except (ValueError, TypeError):
            data["Total Retenidos"] = 0.0
    else:
        data["Total Trasladados"] = 0.0
        data["Total Retenidos"] = 0.0

    # --- Process Specific Traslados (IVA, IEPS) from Conceptos ONLY ---
    for concepto_traslado in root.findall(".//cfdi:Concepto/cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado", namespaces):
        impuesto_code = concepto_traslado.get("Impuesto", "").strip()
        tipo_factor = concepto_traslado.get("TipoFactor", "").strip()
        tasa_ocuota = concepto_traslado.get("TasaOCuota", "").strip()
        importe_str = concepto_traslado.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.0

        if impuesto_code == "002" and tipo_factor == "Tasa":  # IVA
            if tasa_ocuota == "0.160000":
                data["IVA 16%"] += importe
            elif tasa_ocuota == "0.080000":
                data["IVA 8%"] += importe
        elif impuesto_code == "003" and tipo_factor == "Tasa":  # IEPS
            data["Total IEPS"] += importe
            if tasa_ocuota == "0.030000":
                data["IEPS 3%"] += importe
            elif tasa_ocuota == "0.060000":
                data["IEPS 6%"] += importe
            elif tasa_ocuota == "0.070000":
                data["IEPS 7%"] += importe
            elif tasa_ocuota == "0.080000":
                data["IEPS 8%"] += importe
            elif tasa_ocuota == "0.090000":
                data["IEPS 9%"] += importe
            elif tasa_ocuota == "0.265000":
                data["IEPS 26.5%"] += importe
            elif tasa_ocuota == "0.300000":
                data["IEPS 30%"] += importe
            elif tasa_ocuota == "0.304000":  # Specific IEPS rate
                data["IEPS 30.4%"] += importe
            elif tasa_ocuota == "0.530000":
                data["IEPS 53%"] += importe
            elif tasa_ocuota == "1.600000":
                data["IEPS 160%"] += importe

    # --- Process Specific Retenciones (ISR, IVA) from Conceptos ONLY ---
    for concepto_retencion in root.findall(".//cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Retenciones/cfdi:Retencion", namespaces):
        impuesto_code = concepto_retencion.get("Impuesto", "").strip()
        importe_str = concepto_retencion.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.0

        if impuesto_code == "001":  # ISR
            data["Retenido ISR"] += importe
        elif impuesto_code == "002":  # IVA
            data["Retenido IVA"] += importe
            tasa_ocuota_ret = concepto_retencion.get("TasaOCuota", "").strip()
            if tasa_ocuota_ret == "0.060000":  # Specific IVA Retenido rate
                data["IVA Ret 6%"] += importe

    # --- Process Local Taxes (ISH, Total LocalTrasladado, Total LocalRetenido) ---
    total_local_trasladado_sum = 0.0
    for traslado_local in root.findall(".//implocal:ImpuestosLocales/implocal:TrasladosLocales", namespaces):
        imp_loc_trasladado = traslado_local.get("ImpLocTrasladado", "").strip()
        importe_str = traslado_local.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.0

        if imp_loc_trasladado == "ISH":
            data["ISH"] += importe
        total_local_trasladado_sum += importe

    data["Total LocalTrasladado"] = total_local_trasladado_sum

    total_local_retenido_sum = 0.0
    for retencion_local in root.findall(".//implocal:ImpuestosLocales/implocal:RetencionesLocales", namespaces):
        importe_str = retencion_local.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.0

        total_local_retenido_sum += importe
    data["Total LocalRetenido"] = total_local_retenido_sum


def _extract_iedu_data(root, data, namespaces):
    """
    Extracts Specific Data from IEDU Complement.
    This function expects the root of the XML (cfdi:Comprobante) and navigates from there.
    """
    iedu_complement = root.find(
        ".//cfdi:Concepto/cfdi:ComplementoConcepto/iedu:instEducativas", namespaces)
    if iedu_complement is not None:
        data["CURP Dependiente"] = iedu_complement.get("CURP", "").strip()
        data["Nivel Educativo"] = iedu_complement.get(
            "nivelEducativo", "").strip()
        data["Nombre Dependiente"] = iedu_complement.get(
            "nombreAlumno", "").strip()


def parse_cfdi_33_invoice(xml_file_path):
    """
    Parses a single CFDI 3.3 XML invoice file, extracts specified fields (data),
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

        tipo_de_comprobante = root.get('TipoDeComprobante')
        cfdi_type_category = "Invoice"

        if tipo_de_comprobante == 'N' and root.find('cfdi:Complemento/nomina12:Nomina', NAMESPACES_CFDI_33) is not None:
            cfdi_type_category = "Nomina"
        elif tipo_de_comprobante in ['I', 'E', 'T', 'P', 'D']:
            if tipo_de_comprobante == 'I':
                cfdi_type_category = "Invoice"
            else:
                cfdi_type_category = "Invoice"

        data = _initialize_cfdi_data(
            cfdi_version="3.3", cfdi_type_category=cfdi_type_category)

        # --- Explicitly Extract Root-Level CFDI Comprobante Attributes ---
        data["Serie"] = root.get("Serie", '').strip()
        data["Folio"] = root.get("Folio", '').strip()
        data["Fecha Emision"] = root.get("Fecha", "").strip()
        data["Sello"] = root.get("Sello", "").strip()
        data["NoCertificado"] = root.get("NoCertificado", "").strip()
        data["Certificado"] = root.get("Certificado", "").strip()

        subtotal_str = root.get("SubTotal", "0.00").strip()
        try:
            data["SubTotal"] = float(subtotal_str)
        except (ValueError, TypeError):
            data["SubTotal"] = 0.0

        descuento_str = root.get("Descuento", "0.00").strip()
        try:
            data["Descuento"] = float(descuento_str)
        except (ValueError, TypeError):
            data["Descuento"] = 0.0

        total_str = root.get("Total", "0.00").strip()
        try:
            data["Total"] = float(total_str)
        except (ValueError, TypeError):
            data["Total"] = 0.0

        data["Moneda"] = root.get("Moneda", "").strip()

        tipo_cambio_str = root.get("TipoCambio", "1.0").strip()
        try:
            data["Tipo De Cambio"] = float(tipo_cambio_str)
        except (ValueError, TypeError):
            data["Tipo De Cambio"] = 1.0

        forma_pago_code = root.get("FormaPago", "").strip()
        data["FormaDePago"] = f"{forma_pago_code} - {FORMA_PAGO_MAP.get(forma_pago_code, 'Desconocido')}" if forma_pago_code else None

        metodo_pago_code = root.get("MetodoPago", "").strip()
        data["Metodo de Pago"] = f"{metodo_pago_code} - {METODO_PAGO_MAP.get(metodo_pago_code, 'Desconocido')}" if metodo_pago_code else None

        data["Tipo"] = TIPO_COMPROBANTE_MAP.get(
            tipo_de_comprobante, "Desconocido")
        data["LugarDeExpedicion"] = root.get("LugarExpedicion", "").strip()
        data["Condicion de Pago"] = root.get("CondicionesDePago", "").strip()
        data["NumCtaPago"] = root.get("NumCtaPago", "").strip()

        # --- Extract Common CFDI Child Elements (present in 3.3) ---
        for xpath, attr_name, default_val, col_name in CFDI_COMMON_CHILD_ELEMENTS_TO_EXTRACT:
            element = root.find(xpath, NAMESPACES_CFDI_33)
            if element is not None:
                value = element.get(attr_name, default_val).strip() if attr_name else \
                    element.text.strip() if element.text is not None else default_val
            else:
                value = default_val
            data[col_name] = value

        # --- UsoCFDI mapping (from Receptor) ---
        receptor_node = root.find("cfdi:Receptor", NAMESPACES_CFDI_33)
        if receptor_node is not None:
            uso_cfdi_code = receptor_node.get("UsoCFDI", "").strip()
            data["UsoCFDI"] = f"{uso_cfdi_code} - {USO_CFDI_MAP.get(uso_cfdi_code, 'Desconocido')}" if uso_cfdi_code else None
        else:
            data["UsoCFDI"] = None

        # --- Extract Timbre Fiscal Digital Attributes ---
        timbre_fiscal_digital = root.find(
            ".//tfd:TimbreFiscalDigital", NAMESPACES_CFDI_33)
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
        for concepto in root.findall(".//cfdi:Concepto", NAMESPACES_CFDI_33):
            description = concepto.get('Descripcion', '').strip()
            if description:
                descriptions.append(description)

            importe_str = concepto.get('Importe')
            if importe_str:
                try:
                    data["Conceptos_Importe_Sum"] += float(importe_str)
                except ValueError:
                    pass
        data['Conceptos'] = ' | '.join(descriptions) if descriptions else None

        # Extract and aggregate tax details
        _extract_tax_details(root, data, NAMESPACES_CFDI_33)

        # Nomina 1.2 complement specific parsing
        detected_complements = []
        nomina_complement = root.find(
            './/cfdi:Complemento/nomina12:Nomina', NAMESPACES_CFDI_33)
        if nomina_complement is not None:
            data['CFDI_Type'] = 'Nomina'
            detected_complements.append('NOMINA')
            for xpath, attr_name, default_val, col_name in NOMINA_FIELDS_TO_EXTRACT:
                element = root.find(xpath, NAMESPACES_CFDI_33)
                if element is not None:
                    value = element.get(attr_name, default_val).strip() if attr_name else \
                        element.text.strip() if element.text is not None else default_val
                else:
                    value = default_val

                # Convert specific Nomina numeric fields to float
                if col_name in ["Total Sueldos", "Total Deducciones", "Total Otros Pagos", "SBC", "SDI", "ImpuestosRetenidos"]:
                    try:
                        data[col_name] = float(value)
                    except (ValueError, TypeError):
                        data[col_name] = 0.0
                else:
                    data[col_name] = value

            # Calculate TotalGravado and TotalExcento from Percepciones
            total_gravado_percepciones = 0.0
            total_exento_percepciones = 0.0
            for percepcion in root.findall(".//nomina12:Percepcion", NAMESPACES_CFDI_33):
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
            data['TotalGravado'] = total_gravado_percepciones
            data['TotalExcento'] = total_exento_percepciones

            # Calculate TotalDeducciones and TotalOtrosPagos from their direct nodes if available
            total_otras_deducciones_node = nomina_complement.find(
                ".//nomina12:Deducciones", NAMESPACES_CFDI_33)
            if total_otras_deducciones_node is not None:
                total_otras_ded_str = total_otras_deducciones_node.get(
                    "TotalOtrasDeducciones", "0.00").strip()
                try:
                    data['TotalDeducciones'] = float(total_otras_ded_str)
                except (ValueError, TypeError):
                    data['TotalDeducciones'] = 0.0

            total_otros_pag_str = nomina_complement.get(
                "TotalOtrosPagos", "0.00").strip()
            try:
                data['TotalOtrosPagos'] = float(total_otros_pag_str)
            except (ValueError, TypeError):
                data['TotalOtrosPagos'] = 0.0

        else:
            data['CFDI_Type'] = 'Invoice'
            for _, _, _, col_name in NOMINA_FIELDS_TO_EXTRACT:
                data[col_name] = None
            data['TotalGravado'] = None
            data['TotalExcento'] = None
            data['TotalDeducciones'] = None
            data['TotalOtrosPagos'] = None

        # Detect IEDU complement
        iedu_complement = root.find(
            './/cfdi:Concepto/cfdi:ComplementoConcepto/iedu:instEducativas', NAMESPACES_CFDI_33)
        if iedu_complement is not None:
            detected_complements.append('IEDU')
            _extract_iedu_data(root, data, NAMESPACES_CFDI_33)

        # Detect IMPLOCAL complement
        if root.find('.//cfdi:Complemento/implocal:ImpuestosLocales', NAMESPACES_CFDI_33) is not None:
            detected_complements.append('IMPLOCAL')

        data["Complemento"] = ", ".join(
            detected_complements) if detected_complements else None
        data['Archivo XML'] = os.path.basename(xml_file_path)

        # --- Combustible Detection Logic ---
        combustible_detected = False
        for concepto in root.findall(".//cfdi:Concepto", NAMESPACES_CFDI_33):
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

        serie = root.get("Serie", '').strip()
        folio = root.get("Folio", '').strip()
        if serie and folio:
            data['Factura'] = f"{serie}-{folio}"
        elif folio:
            data['Factura'] = folio
        else:
            data['Factura'] = None

        data["Verificado ó Asoc."] = ""
        data["Estado SAT"] = ""
        data["EstadoPago"] = ""
        data["FechaPago"] = ""
        data["Direccion Emisor"] = ""
        data["Localidad Emisor"] = ""
        data["Direccion Receptor"] = ""
        data["Localidad Receptor"] = ""

        # --- Format Dates for consistency with Excel Export ---
        if data["Fecha Emision"]:
            try:
                dt_obj = datetime.strptime(
                    data["Fecha Emision"], "%Y-%m-%dT%H:%M:%S")
                data["Fecha Emision"] = dt_obj.strftime("%d/%m/%Y")
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
