"""
E-Invoice HTML Preview Generator.
Renders the SIFEN JSON payload as an HTML preview without sending to the API.
"""

import frappe
from frappe import _
from ..builders import prepare_invoice_data

# ============================================================================
# SIFEN CODE CONSTANTS (from xml-gen Constante.service.js)
# ============================================================================

TIPOS_DOCUMENTO = {
    1: "Factura Electrónica",
    2: "Factura Electrónica de Exportación",
    3: "Factura Electrónica por Importación",
    4: "Autofactura Electrónica",
    5: "Nota de Crédito Electrónica",
    6: "Nota de Débito Electrónica",
}

TIPOS_TRANSACCION = {
    1: "Venta de mercadería",
    2: "Prestación de servicios",
    3: "Mixto",
    4: "Venta de activo fijo",
    5: "Venta de divisas",
    6: "Compra de divisas",
    7: "Promoción o muestra",
    8: "Donación",
    9: "Anticipo",
    10: "Compra de productos",
    11: "Compra de servicios",
    12: "Venta de crédito fiscal",
}

TIPOS_IMPUESTO = {
    1: "IVA",
    2: "ISC",
    3: "Renta",
    4: "Ninguno",
    5: "IVA - Renta",
}

TIPOS_REGIMEN = {
    1: "Régimen de Turismo",
    2: "Importador",
    3: "Exportador",
    4: "Maquila",
    5: "Ley N° 60/90",
    6: "Régimen del Pequeño Productor",
    7: "Régimen del Mediano Productor",
    8: "Régimen Contable",
}

TIPOS_OPERACION = {
    1: "B2B (Business to Business) - Operación entre empresas",
    2: "B2C (Business to Consumer) - Venta directa al consumidor final",
    3: "B2G (Business to Government) - Venta al Estado paraguayo",
    4: "B2F (Business to Foreign) - Servicios prestados a empresas/personas del exterior",
}

CONDICION_OPERACION = {
    1: "Contado",
    2: "Crédito",
}

TIPOS_DOCUMENTO_IDENTIDAD = {
    1: "Cédula paraguaya",
    2: "Pasaporte",
    3: "Cédula extranjera",
    4: "Carnet de residencia",
    5: "Innominado",
    6: "Tarjeta Diplomática",
    9: "No especificado",
}

TIPOS_PAGO_ENTREGA = {
    1: "Efectivo",
    2: "Cheque",
    3: "Tarjeta de crédito",
    4: "Tarjeta de débito",
    5: "Anticipo",
    6: "Cabal",
}

CONDICION_TIPO_CAMBIO = {
    1: "Global",
    2: "Por ítem",
}

CONDICION_ANTICIPO = {
    1: "Global",
    2: "Por ítem",
}

TIPO_CONTRIBUYENTE = {
    1: "Persona Física",
    2: "Persona Jurídica",
}

AFECTACIONES_IVA = {
    1: "Gravado IVA",
    2: "Exonerado (Art.83- Ley 125/91)",
    3: "Exento",
    4: "Gravado parcial",
}

MOTIVOS_NC_ND = {
    1: "Anulación del documento",
    2: "Corrección de errores en el documento",
    3: "Transmisión parcial del documento",
    4: "Descuento global por operaciones",
    5: "Cesión de crédito fiscal",
    6: "Exoneración de impuesto",
    7: "Bonificación al comprador",
    8: "Otro",
}


def get_sifen_description(category, code):
    """Get human-readable description for a SIFEN code."""
    mapping = {
        "tipoDocumento": TIPOS_DOCUMENTO,
        "tipoTransaccion": TIPOS_TRANSACCION,
        "tipoImpuesto": TIPOS_IMPUESTO,
        "tipoRegimen": TIPOS_REGIMEN,
        "tipoOperacion": TIPOS_OPERACION,
        "condicionOperacion": CONDICION_OPERACION,
        "documentoTipo": TIPOS_DOCUMENTO_IDENTIDAD,
        "tipoPago": TIPOS_PAGO_ENTREGA,
        "condicionTipoCambio": CONDICION_TIPO_CAMBIO,
        "afectacionIva": AFECTACIONES_IVA,
        "motivo": MOTIVOS_NC_ND,
    }
    m = mapping.get(category, {})
    return m.get(code, f"Código {code}")


def get_invoice_preview_html(invoice_name):
    """
    Generate HTML preview for an invoice without sending to SIFEN.
    Builds JSON using prepare_invoice_data, then renders as HTML.
    """
    # Determine doc type
    doctype = "Sales Invoice"
    try:
        doc = frappe.get_doc("Sales Invoice", invoice_name)
    except Exception:
        try:
            doc = frappe.get_doc("Purchase Invoice", invoice_name)
            doctype = "Purchase Invoice"
        except Exception:
            frappe.throw(_("Invoice {0} not found").format(invoice_name))

    if doc.docstatus == 0:
        frappe.throw(_("Cannot preview a draft invoice. Please save and validate first."))

    # Generate JSON payload using existing builder
    invoice_data = prepare_invoice_data(doc)
    param = invoice_data.get("param", {})
    data = invoice_data.get("data", {})

    # Build HTML
    html = _build_html(param, data, doc, doctype)
    return html


def _build_html(param, data, doc, doctype):
    """Build complete HTML preview."""
    doc_type_label = _("Autofactura") if doctype == "Purchase Invoice" else _("Factura de Venta")

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 900px; margin: 20px auto; border: 1px solid #ccc; border-radius: 8px; overflow: hidden;">
        <!-- Header -->
        <div style="background: #1a73e8; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="margin: 0; font-size: 22px;">{doc_type_label} - Vista Previa SIFEN</h2>
                <p style="margin: 5px 0 0; opacity: 0.9;">{doc.name}</p>
            </div>
            <div style="text-align: right;">
                <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 4px; font-size: 12px;">
                    {_get_doc_desc(data.get('tipoDocumento'))}
                </span>
            </div>
        </div>

        <!-- Emisor y Receptor -->
        <div style="padding: 20px; background: #f8f9fa; border-bottom: 1px solid #e0e0e0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; vertical-align: top; width: 50%; border-right: 1px solid #ddd;">
                        <h3 style="margin: 0 0 12px; color: #1a73e8; font-size: 16px; border-bottom: 2px solid #1a73e8; padding-bottom: 6px;">
                            {_('Emisor')}
                        </h3>
                        <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                            {_build_param_rows(param)}
                        </table>
                    </td>
                    <td style="padding: 8px; vertical-align: top; width: 50%;">
                        <h3 style="margin: 0 0 12px; color: #1a73e8; font-size: 16px; border-bottom: 2px solid #1a73e8; padding-bottom: 6px;">
                            {_('Receptor')}
                        </h3>
                        <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                            {_build_cliente_rows(data.get('cliente', {}))}
                        </table>
                    </td>
                </tr>
            </table>
        </div>

        <!-- General Info -->
        <div style="padding: 20px; border-bottom: 1px solid #e0e0e0;">
            <h3 style="margin: 0 0 15px; color: #333; font-size: 16px;">{_('Información General')}</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr>
                    <td style="padding: 6px; width: 20%;"><strong>Establecimiento:</strong></td>
                    <td style="padding: 6px; width: 13%;">{data.get('establecimiento', '')}</td>
                    <td style="padding: 6px; width: 20%;"><strong>Punto:</strong></td>
                    <td style="padding: 6px; width: 13%;">{data.get('punto', '')}</td>
                    <td style="padding: 6px; width: 20%;"><strong>Número:</strong></td>
                    <td style="padding: 6px; width: 14%;">{data.get('numero', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 6px;"><strong>Fecha:</strong></td>
                    <td style="padding: 6px;">{data.get('fecha', '')}</td>
                    <td style="padding: 6px;"><strong>Tipo Emisión:</strong></td>
                    <td style="padding: 6px;">{'Contingencia' if data.get('tipoEmision') == 2 else 'Normal'}</td>
                    <td style="padding: 6px;"><strong>Nº Control:</strong></td>
                    <td style="padding: 6px;">{data.get('codigoSeguridadAleatorio', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 6px;"><strong>Tipo Documento:</strong></td>
                    <td style="padding: 6px;">{_get_doc_desc(data.get('tipoDocumento'))}</td>
                    <td style="padding: 6px;"><strong>Tipo Transacción:</strong></td>
                    <td style="padding: 6px;">{_get_transaccion_desc(data.get('tipoTransaccion'))}</td>
                    <td style="padding: 6px;"><strong>Tipo Impuesto:</strong></td>
                    <td style="padding: 6px;">{_get_impuesto_desc(data.get('tipoImpuesto'))}</td>
                </tr>
                <tr>
                    <td style="padding: 6px;"><strong>Moneda:</strong></td>
                    <td style="padding: 6px;">{data.get('moneda', 'PYG')}</td>
                    {_get_condicion_cambio_html(data.get('moneda'), data.get('condicionTipoCambio'))}
                </tr>
                {_get_descuento_global_html(data.get('descuentoGlobal'))}
                {_get_anticipo_row_html(data.get('anticipoGlobal'), data.get('condicionAnticipo'))}
                <tr>
                    <td style="padding: 6px;"><strong>Descripción:</strong></td>
                    <td colspan="3" style="padding: 6px;">{data.get('descripcion', '')}</td>
                    <td style="padding: 6px;"><strong>Total Pago:</strong></td>
                    <td style="padding: 6px; font-weight: bold; color: #1a73e8;">
                        {data.get('moneda', 'PYG')} {format(data.get('totalPago', 0), ',.0f')}
                    </td>
                </tr>
                {_row('Observación', data.get('observacion', '')) if data.get('observacion') else ''}
            </table>
        </div>

        <!-- Items -->
        <div style="padding: 20px; border-bottom: 1px solid #e0e0e0;">
            <h3 style="margin: 0 0 15px; color: #333; font-size: 16px;">{_('Detalle de Ítems')}</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background: #e8eef5;">
                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #1a73e8;">{_('Descripción')}</th>
                        <th style="padding: 8px; text-align: center; border-bottom: 2px solid #1a73e8;">{_('Cantidad')}</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 2px solid #1a73e8;">{_('Precio Unit.')}</th>
                        {_get_descuento_header_html(data.get('items', []))}
                        <th style="padding: 8px; text-align: right; border-bottom: 2px solid #1a73e8;">{_('Afect. IVA')}</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 2px solid #1a73e8;">{_('Total')}</th>
                    </tr>
                </thead>
                <tbody>
                    {_build_items_html(data.get('items', []))}
                </tbody>
            </table>
        </div>

        <!-- Payments -->
        {_build_payments_html(data.get('condicion', {}))}

        <!-- Footer -->
        <div style="padding: 15px 20px; background: #f8f9fa; text-align: center; color: #888; font-size: 12px; border-top: 1px solid #e0e0e0;">
            {_('Vista previa generada desde los datos de la factura - No es documento oficial')}<br/>
            {_('Para generar el documento oficial, envíe a SIFEN y descargue el KUDE')}
        </div>
    </div>
    """
    return html


def _build_items_html(items):
    """Build HTML for items table."""
    rows = []
    has_descuento = _has_item_descuento(items)

    for item in items:
        desc = item.get('descripcion', '')
        qty = item.get('cantidad', 0)
        price = item.get('precioUnitario', 0)
        afectacion = item.get('ivaTipo', '')
        afectacion_desc = _get_afectacion_iva_desc(afectacion)
        descuento = item.get('descuento', 0)

        # Calculate approximate total
        item_total = (qty or 0) * (price or 0) - (descuento or 0)

        descuento_cell = ''
        if has_descuento:
            if descuento and descuento > 0:
                descuento_cell = f'<td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; color: #c00;">{format(descuento, ",.0f")}</td>'
            else:
                descuento_cell = '<td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">—</td>'

        rows.append(f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{desc}</td>
            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #eee;">{qty}</td>
            <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">{format(price, ',.0f')}</td>
            {descuento_cell}
            <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">{afectacion_desc}</td>
            <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; font-weight: bold;">
                {format(item_total, ',.0f')}
            </td>
        </tr>
        """)

    colspan = 6 if has_descuento else 5
    return ''.join(rows) if rows else f'<tr><td colspan="{colspan}" style="padding: 15px; text-align: center; color: #999;">Sin ítems</td></tr>'


def _build_payments_html(condicion):
    """Build HTML for payments section."""
    entregas = condicion.get('entregas', [])
    if not entregas:
        return ""

    condicion_op = condicion.get('tipo', 1)

    html = f"""
    <div style="padding: 20px;">
        <h3 style="margin: 0 0 15px; color: #333; font-size: 16px;">
            {_('Forma de Pago')}: {_get_condicion_operacion_desc(condicion_op)}
        </h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background: #e8eef5;">
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #1a73e8;">{_('Tipo Pago')}</th>
                    <th style="padding: 8px; text-align: right; border-bottom: 2px solid #1a73e8;">{_('Monto')}</th>
                    <th style="padding: 8px; text-align: right; border-bottom: 2px solid #1a73e8;">{_('Moneda')}</th>
                    <th style="padding: 8px; text-align: right; border-bottom: 2px solid #1a73e8;">{_('Tipo Cambio')}</th>
                </tr>
            </thead>
            <tbody>
    """

    for entrega in entregas:
        tipo_pago = entrega.get('tipo', 1)
        monto = entrega.get('monto', 0)
        moneda = entrega.get('moneda', 'PYG')
        cambio = entrega.get('cambio', 0)

        html += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{_get_tipo_pago_desc(tipo_pago)}</td>
                    <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; font-weight: bold;">
                        {format(float(monto), ',.0f')}
                    </td>
                    <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">{moneda}</td>
                    <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">{cambio}</td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </div>
    """

    return html


# ============================================================================
# HELPER FUNCTIONS - Map codes to descriptions
# ============================================================================

def _build_param_rows(param):
    """Build HTML table rows for all param (emisor) fields."""
    establecimiento = param.get('establecimientos', [{}])[0] if param.get('establecimientos') else {}

    rows = [
        _row("RUC", param.get('ruc', '')),
        _row("Razón Social", param.get('razonSocial', '')),
        _row("Nombre Fantasía", param.get('nombreFantasia', '')),
        _row("Actividades Económicas", _format_actividades(param.get('actividadesEconomicas', []))),
        _row("Timbrado Nº", param.get('timbradoNumero', '')),
        _row("Timbrado Fecha", param.get('timbradoFecha', '')),
        _row("Tipo Contribuyente", _get_tipo_contribuyente_desc(param.get('tipoContribuyente'))),
        _row("Tipo Régimen", _get_regimen_desc(param.get('tipoRegimen'))),
        _row("Cód. Establecimiento", establecimiento.get('codigo', '')),
        _row("Denominación", establecimiento.get('denominacion', '')),
        _row("Dirección", establecimiento.get('direccion', '')),
        _row("Nº Casa", establecimiento.get('numeroCasa', '')),
        _row("Complemento 1", establecimiento.get('complementoDireccion1', '')),
        _row("Complemento 2", establecimiento.get('complementoDireccion2', '')),
        _row("Departamento", _format_location(establecimiento.get('departamento'), establecimiento.get('departamentoDescripcion'))),
        _row("Distrito", _format_location(establecimiento.get('distrito'), establecimiento.get('distritoDescripcion'))),
        _row("Ciudad", _format_location(establecimiento.get('ciudad'), establecimiento.get('ciudadDescripcion'))),
        _row("Teléfono", establecimiento.get('telefono', '')),
        _row("Email", establecimiento.get('email', '')),
    ]
    return '\n'.join(rows)


def _build_cliente_rows(cliente):
    """Build HTML table rows for all data.cliente (receptor) fields."""
    is_contribuyente = cliente.get('contribuyente', False)
    tipo_operacion = cliente.get('tipoOperacion', 0)
    show_documento = not is_contribuyente and tipo_operacion != 4

    rows = [
        _row("Contribuyente", "Sí" if cliente.get('contribuyente') else "No"),
        _row("RUC", cliente.get('ruc', '')),
        _row("Razón Social", cliente.get('razonSocial', '')),
        _row("Nombre Fantasía", cliente.get('nombreFantasia', '')),
        _row("Tipo Operación", _get_operacion_desc(cliente.get('tipoOperacion'))),
        _row("Dirección", cliente.get('direccion', '')),
        _row("Nº Casa", cliente.get('numeroCasa', '')),
        _row("Complemento 1", cliente.get('complementoDireccion1', '')),
        _row("Departamento", _format_location(cliente.get('departamento'), cliente.get('departamentoDescripcion'))),
        _row("Distrito", _format_location(cliente.get('distrito'), cliente.get('distritoDescripcion'))),
        _row("Ciudad", _format_location(cliente.get('ciudad'), cliente.get('ciudadDescripcion'))),
        _row("País", _format_location(cliente.get('pais'), cliente.get('paisDescripcion'))),
        _row("Tipo Contribuyente", _get_tipo_contribuyente_desc(cliente.get('tipoContribuyente'))),
    ]

    if show_documento:
        rows.append(_row("Tipo Documento", _get_documento_identidad_desc(cliente.get('documentoTipo'))))
        rows.append(_row("Nº Documento", cliente.get('documentoNumero', '')))

    rows.extend([
        _row("Teléfono", cliente.get('telefono', '')),
        _row("Celular", cliente.get('celular', '')),
        _row("Email", cliente.get('email', '')),
        _row("Código", cliente.get('codigo', '')),
    ])
    return '\n'.join(rows)


def _row(label, value):
    """Build a single table row with label and value."""
    display_value = value if value else '<span style="color: #ccc;">—</span>'
    return f'<tr><td style="padding: 3px 8px 3px 0; font-weight: bold; color: #555; width: 35%;">{label}:</td><td style="padding: 3px 0;">{display_value}</td></tr>'


def _format_location(code, description):
    """Format location code + description."""
    if code and description:
        return f"{code} - {description}"
    return str(description or code or '—')


def _format_actividades(actividades):
    """Format economic activities list."""
    if not actividades:
        return '—'
    return ', '.join([f"{a.get('codigo', '')}: {a.get('descripcion', '')}" for a in actividades])


def _get_doc_desc(code):
    return TIPOS_DOCUMENTO.get(int(code) if code else 0, str(code or ''))

def _get_transaccion_desc(code):
    return TIPOS_TRANSACCION.get(int(code) if code else 0, str(code or ''))

def _get_impuesto_desc(code):
    return TIPOS_IMPUESTO.get(int(code) if code else 0, str(code or ''))

def _get_regimen_desc(code):
    return TIPOS_REGIMEN.get(int(code) if code else 0, str(code or ''))

def _get_operacion_desc(code):
    return TIPOS_OPERACION.get(int(code) if code else 0, str(code or ''))

def _get_condicion_operacion_desc(code):
    return CONDICION_OPERACION.get(int(code) if code else 1, str(code or ''))

def _get_documento_identidad_desc(code):
    return TIPOS_DOCUMENTO_IDENTIDAD.get(int(code) if code else 0, str(code or ''))

def _get_tipo_pago_desc(code):
    return TIPOS_PAGO_ENTREGA.get(int(code) if code else 0, str(code or ''))

def _get_condicion_tipo_cambio_desc(code):
    return CONDICION_TIPO_CAMBIO.get(int(code) if code else 1, str(code or ''))

def _get_tipo_contribuyente_desc(code):
    return TIPO_CONTRIBUYENTE.get(int(code) if code else 0, str(code or ''))

def _get_condicion_cambio_html(moneda, condicion_tipo_cambio):
    """Get condicionTipoCambio HTML row. Only shown if currency is not PYG."""
    if moneda and moneda != 'PYG':
        return '<td style="padding: 6px;"><strong>Cond. Tipo Cambio:</strong></td><td style="padding: 6px;">{}</td>'.format(
            _get_condicion_tipo_cambio_desc(condicion_tipo_cambio)
        )
    return '<td style="padding: 6px;"></td><td style="padding: 6px;"></td>'

def _get_condicion_anticipo_desc(code):
    """Get anticipo condition description. Returns empty if None."""
    if not code:
        return '<span style="color: #ccc;">—</span>'
    return CONDICION_ANTICIPO.get(int(code), str(code))

def _get_descuento_global_html(descuento_global):
    """Return descuento global row. Empty string if 0 or None."""
    if descuento_global and float(descuento_global or 0) != 0:
        return '<tr><td style="padding: 6px;"><strong>Descuento Global:</strong></td><td colspan="5" style="padding: 6px;">{}</td></tr>'.format(
            format(float(descuento_global), ',.0f')
        )
    return ''

def _get_anticipo_row_html(anticipo_global, condicion_anticipo):
    """Return full anticipo row. Empty string if no anticipo."""
    if anticipo_global and float(anticipo_global or 0) != 0:
        return '<tr><td style="padding: 6px;"><strong>Cond. Anticipo:</strong></td><td style="padding: 6px;">{}</td><td style="padding: 6px;"><strong>Anticipo Global:</strong></td><td colspan="3" style="padding: 6px;">{}</td></tr>'.format(
            _get_condicion_anticipo_desc(condicion_anticipo),
            format(float(anticipo_global), ',.0f')
        )
    return ''

def _has_item_descuento(items):
    """Check if any item has discount."""
    for item in items:
        if item.get('descuento') and item.get('descuento') > 0:
            return True
    return False

def _get_descuento_header_html(items):
    """Return descuento header if any item has discount."""
    if _has_item_descuento(items):
        return '<th style="padding: 8px; text-align: right; border-bottom: 2px solid #1a73e8;">' + _('Descuento') + '</th>'
    return ''

def _get_afectacion_iva_desc(code):
    return AFECTACIONES_IVA.get(int(code) if code else 0, str(code or ''))

def _get_motivo_nc_nd_desc(code):
    return MOTIVOS_NC_ND.get(int(code) if code else 0, str(code or ''))
