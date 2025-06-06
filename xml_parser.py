# ----------XML Procesor----------
# source: http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd
import xml.etree.ElementTree as ET
import os

""""
Define the XML namespaces used in CFDI 4.0 for parsing.
This is crucial for correctly interpreting the XML structure
and finding the necessary elements.
"""
NAMESPACES = {
    'cfdi': 'http://www.sat.gob.mx/cfd/4',
    'nomina12': 'http://www.sat.gob.mx/nomina12',
    'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
    'iedu': 'http://www.sat.gob.mx/iedu',
    'implocal': 'http://www.sat.gob.mx/implocal',  # Local Taxex complement like ISH
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

# List of XML tags/attributes to extract for regula CFDI XML.
# Eaach item is a tuple: (XPath, atribute_name_if_any, default_value_if_not_found, output_column_name)
# For atributes, the XPath should point to the element containing the attribute and atribute_name_if_any should be the atribute name.
# For element text, atribute_name_if_any should be "".
# The output_column_name is how it will appear in the Excel file.
CFDI_FIELDS_TO_EXTRACT = [
    # CFDI 4.0 Invoice fields (Atriutes)
    # If something goes wrong take of .// from the beginning of the XPath
    (".//cfdi:Comprobante", "Version", "4.0", "Version"),
    (".//cfdi:Comprobante", "TipoDeComprobante", "", "Tipo"),
    (".//cfdi:Comprobante", "Fecha", "", "Fecha"),
    # "Factura" (Serie+Folio) will be handled as a derived field.
    (".//cfdi:Comprobante", "LugarExpedicion", "", "LugarExpedicion"),
    (".//cfdi:Comprobante", "SubTotal", "0.00", "SubTotal"),
    (".//cfdi:Comprobante", "Descuento", "0.00", "Descuento"),
    (".//cfdi:Comprobante", "Total", "0.00", "Total"),
    (".//cfdi:Comprobante", "Moneda", "", "Moneda"),
    (".//cfdi:Comprobante", "FormaPago", "", "FormaPago"),
    (".//cfdi:Comprobante", "MetodoPago", "", "MetodoPago"),
    (".//cfdi:Comprobante", "Exportacion", "", "Exportacion"),
    (".//cfdi:Comprobante", "CondicionesDePago", "", "Condiciones de Pago"),
    (".//cfdi:Comprobante", "TipoCambio", "1.0", "TipoCambio"),
    # CFDI 4.0 Relacionados
    (".//cfdi:CfdiRelacionados", "TipoRelacion", "", "TipoDeRelacion"),
    (".//cfdi:CfdiRelacionados", "UUID", "", "UUID_Relacionados"),
    # CFDI 4.0 Emisor
    # In the original XLS file I renamed RFC
    (".//cfdi:Emisor", "Rfc", "", "RFC Emisor"),
    (".//cfdi:Emisor", "Nombre", "", "Nombre Emisor"),
    (".//cfdi:Emisor", "RegimenFiscal", "", "Regimen FiscalEmisor"),
    # CFDI 4.0 Receptor
    (".//cfdi:Receptor", "Rfc", "", "RFC Receptor"),
    (".//cfdi:Receptor", "Nombre", "", "Nombre Receptor"),
    # (".//cfdi:Receptor", "ResidenciaFiscal", "", "Residencia Fiscal Receptor"),
    # (".//cfdi:Receptor", "NumRegIdTrib", "", "NumRegIdTrib Receptor"),
    (".//cfdi:Receptor", "UsoCFDI", "", "Uso CFDI Receptor"),
    # CFDI 4.0 Timbre Fiscal Digital
    (".//tfd:TimbreFiscalDigital", "UUID", "", "Folio Fiscal"),
    (".//tfd:TimbreFiscalDigital", "FechaTimbrado", "", "Fecha Timbrado"),
    # (".//tfd:TimbreFiscalDigital", "SelloCFD", "", "Sello CFD"),
    # (".//tfd:TimbreFiscalDigital", "NoCertificadoSAT", "", "No Certificado SAT"),
    # (".//tfd:TimbreFiscalDigital", "SelloSAT", "", "Sello SAT"),
    # CFDI 4.0 Impuestos Trasladados
    (".//cfdi:Impuestos", "TotalImpuestosTrasladados", "0.00", "IVA"),
    # CFDI 4.0 Impuestos Retenidos
    # (".//cfdi:Impuestos", "TotalImpuestosRetenidos", "0.00", "ISR Retenido"),
    # CFDI 4.0 Impuestos Locales
    (".//implocal:ImpuestosLocales", "TotaldeRetenciones",
     "0.00", "Total Retenciones Locales"),
    (".//implocal:ImpuestosLocales", "TotaldeTraslados",
     "0.00", "Total Traslados Locales"),
]

# List of XML tags/attributes to extract for Nomina complement 1.2 XML.
NOMINA_FIELDS_TO_EXTRACT = [
    (".//nomina12:Nomina", "Version", "", "Version Nomina"),
    (".//nomina12:Nomina", "TipoNomina", "", "Tipo Nomina"),
    (".//nomina12:Nomina", "FechaPago", "", "Fecha Pago"),
    (".//nomina12:Nomina", "FechaInicialPago", "", "Fecha Inicial Pago"),
    (".//nomina12:Nomina", "FechaFinalPago", "", "Fecha Final Pago"),
    # (".//nomina12:Nomina", "NumDiasPagados", "", "Num Dias Pagados"),
    (".//nomina12:Nomina", "TotalPercepciones", "0.00", "Total Sueldos"),
    (".//nomina12:Nomina", "TotalDeducciones", "0.00", "Total Deducciones"),
    (".//nomina12:Nomina", "TotalOtrosPagos", "0.00", "Total Otros Pagos"),
    # Nomina 1.2 Emisor
    (".//nomina12:Emisor", "RegistroPatronal", "", "Registro Patronal"),
    (".//nomina12:Emisor", "Curp", "", "CURP Patron"),
    (".//nomina12:Emisor", "RfcPatronOrigen", "", "RFC Patron"),
    # Nomina 1.2 Receptor
    (".//nomina12:Receptor", "Curp", "", "CURP"),
    (".//nomina12:Receptor", "NumSeguridadSocial", "", "NSS"),
    (".//nomina12:Receptor", "FechaInicioRelLaboral", "", "Inicio Relacion Laboral"),
    # (".//nomina12:Receptor", "Rfc", "", "RFC"),
    # (".//nomina12:Receptor", "TipoContrato", "", "Tipo Contrato"),
    (".//nomina12:Receptor", "Antigüedad", "", "Antiguedad"),
    (".//nomina12:Receptor", "PeriodicidadPago", "", "Periodicidad Pago"),
    # (".//nomina12:Receptor", "Banco", "", "Banco"),
    # (".//nomina12:Receptor", "CuentaBancaria", "", "Cuenta Bancaria"),
    (".//nomina12:Receptor", "SalarioBaseCotApor", "0.00", "SBC"),
    (".//nomina12:Receptor", "SalarioDiarioIntegrado", "0.00", "SDI"),
    (".//nomina12:Receptor", "ClaveEntFed", "", "Entidad"),
    # Nomina 1.2 Deducciones
    # (".//nomina12:Deducciones", "TotalOtrasDeducciones", "0.00", "Total Otras Deducciones"),
    (".//nomina12:Deducciones", "TotalImpuestosRetenidos",
     "0.00", "Total ISR Retenido"),
]


def parse_xml_invoice(xml_file_path):
    """
    Parses a single XML invoice file, extracts specified fields (data), and determines its type (Invoice or Nomina).
    Merges descriptions from multiple Concepto nodes.

    Args:
        xml_file_path (str): Path to the XML file to be parsed.

    Returns:
        dict: A dictionary containing the extracted data from the XML file.
        Including a "CDFI_Type" key indicating whether it's an "Invoice" or "Nomina".
        None: If the XML file is not valid or does not match expected structure.
    """

    data = {}  # Dictionary to hold the extracted data
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        """ 
        Initialize all possible fields to None to ensure consitency in DataFrame columns
        regardless of CFDI type.
        """
        all_possible_fields = [col_name for _, _,
                               _, col_name in CFDI_FIELDS_TO_EXTRACT]
        all_possible_fields.extend(
            [col_name for _, _, _, col_name in NOMINA_FIELDS_TO_EXTRACT])
        all_possible_fields.extend(['Descripcion, 'TotalGravado', 'TotalExento', 'Source.Name', 'CDFI_Type','Factura',  # For the merged Serie+Folio field
                                    'ImpLocal_TrasladadosLocales_Details  # For the concatenated implocal details
                                    ])
        # Using set to avoud duplicates
        for field in set(all_possible_fields):
            data[field] = None

    except "" as e:
        print()
        return None
    except Exception as e:
        print("")
        return None
    return
