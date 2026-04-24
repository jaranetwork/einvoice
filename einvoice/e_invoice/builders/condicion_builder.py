"""
Builds the CONDICION section of SIFEN payload.
Contains payment conditions, credit info, and delivery schedule.

SIFEN Payment Types (tipo):
1 = Efectivo
2 = Cheque (requires infoCheque)
3 = Tarjeta de crédito (requires infoTarjeta)
4 = Tarjeta de débito (requires infoTarjeta)
5 = Transferencia
6 = Giro
7 = Billetera electrónica
8 = Tarjeta empresarial
9 = Vale
10 = Retención
11 = Pago por anticipo
12 = Valor fiscal
13 = Valor comercial
14 = Compensación
15 = Permuta
16 = Pago bancario
17 = Pago Móvil
18 = Donación
19 = Promoción
20 = Consumo Interno
21 = Pago Electrónico
99 = Otro
"""

import frappe
from frappe.utils import flt


# Mapping from ERPNext Mode of Payment to SIFEN payment type
SIFEN_PAYMENT_TYPE_MAP = {
    "cash": 1,
    "efectivo": 1,
    "cheque": 2,
    "check": 2,
    "credit card": 3,
    "tarjeta de crédito": 3,
    "debit card": 4,
    "tarjeta de débito": 4,
    "transfer": 5,
    "transferencia": 5,
    "bank transfer": 5,
    "giro": 6,
    "billetera": 7,
    "billetera electrónica": 7,
    "wallet": 7,
    "tarjeta empresarial": 8,
    "corporate card": 8,
    "vale": 9,
    "retención": 10,
    "retencion": 10,
    "withholding": 10,
    "anticipo": 11,
    "advance": 11,
    "pago por anticipo": 11,
    "valor fiscal": 12,
    "valor comercial": 13,
    "compensación": 14,
    "compensacion": 14,
    "permuta": 15,
    "exchange": 15,
    "pago bancario": 16,
    "bank payment": 16,
    "pago móvil": 17,
    "pago movil": 17,
    "mobile payment": 17,
    "donación": 18,
    "donacion": 18,
    "donation": 18,
    "promoción": 19,
    "promocion": 19,
    "promotion": 19,
    "consumo interno": 20,
    "internal consumption": 20,
    "pago electrónico": 21,
    "pago electronico": 21,
    "electronic payment": 21,
}

# SIFEN card denominations (for infoTarjeta)
CARD_TYPE_MAP = {
    "visa": 1,
    "mastercard": 2,
    "master card": 2,
    "american express": 3,
    "amex": 3,
    "maestro": 4,
    "panal": 5,
    "cabal": 6,
}


def build_condicion_section(doc, moneda="PYG", condicion_tipo_cambio=1):
    """
    Build the 'condicion' section with payment conditions.

    Args:
        doc: Sales Invoice or Purchase Invoice document
        moneda: Currency code
        condicion_tipo_cambio: Exchange rate condition

    Returns:
        dict: Condicion section for SIFEN payload
    """
    # Get operation type (Contado vs Crédito)
    from ..utils.utils import get_condicion_operacion
    condicion_operacion = get_condicion_operacion(doc)

    # Build entregas (payment schedule)
    entregas = _build_entregas(doc, moneda)

    # Build condicion object
    condicion = {
        "tipo": condicion_operacion,
        "entregas": entregas
    }

    # Add credit info if credit operation
    if condicion_operacion == 2:
        credito_info = _build_credito_info(doc)
        if credito_info:
            condicion["credito"] = credito_info

    return condicion


def _build_entregas(doc, moneda):
    """
    Build entregas array from payment schedule and linked Payment Entries.
    Maps ERPNext payment modes to SIFEN payment types.

    Priority:
    0. is_paid (for Purchase Invoice - immediate payment)
    1. POS payments table (for POS invoices)
    2. Advances (linked Payment Entries)
    3. Payment Schedule (for credit invoices)
    """
    # Get exchange rate from Currency Exchange
    cambio_valor = 0
    if moneda != "PYG":
        cambio_valor = frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": moneda, "to_currency": "PYG"},
            "exchange_rate"
        )
        if not cambio_valor and hasattr(doc, 'conversion_rate') and doc.conversion_rate:
            cambio_valor = doc.conversion_rate

    entregas = []

    # 0. Check is_paid (Purchase Invoice - already paid)
    if hasattr(doc, 'is_paid') and doc.is_paid:
        payment_mode = getattr(doc, 'mode_of_payment', None)
        paid_amount = getattr(doc, 'paid_amount', None) or getattr(doc, 'grand_total', 0)
        sifen_tipo = _get_sifen_payment_type(payment_mode)

        entrega = {
            "tipo": sifen_tipo,
            "monto": str(abs(float(paid_amount))),
            "moneda": moneda,
            "cambio": cambio_valor if moneda != "PYG" else 0
        }

        # Add additional info for specific payment types
        if sifen_tipo in [3, 4]:  # Tarjeta de crédito/débito
            card_info = _get_card_info(payment_mode)
            if card_info:
                entrega["infoTarjeta"] = card_info

        if sifen_tipo == 2:  # Cheque
            cheque_info = _get_cheque_info(payment_mode)
            if cheque_info:
                entrega["infoCheque"] = cheque_info

        entregas.append(entrega)
        return entregas

    # 1. Check payments table FIRST (for POS invoices)
    if hasattr(doc, 'payments') and doc.payments:
        for payment in doc.payments:
            if payment.amount and payment.amount > 0:
                payment_mode = payment.mode_of_payment
                sifen_tipo = _get_sifen_payment_type(payment_mode)

                entrega = {
                    "tipo": sifen_tipo,
                    "monto": str(abs(float(payment.amount))),
                    "moneda": moneda,
                    "cambio": cambio_valor if moneda != "PYG" else 0
                }

                # Add additional info for specific payment types
                if sifen_tipo in [3, 4]:  # Tarjeta de crédito/débito
                    card_info = _get_card_info(payment_mode)
                    if card_info:
                        entrega["infoTarjeta"] = card_info

                if sifen_tipo == 2:  # Cheque
                    cheque_info = _get_cheque_info(payment_mode)
                    if cheque_info:
                        entrega["infoCheque"] = cheque_info

                entregas.append(entrega)

    # 2. Check if invoice has advances (already paid)
    if hasattr(doc, 'advances') and doc.advances:
        for advance in doc.advances:
            if advance.allocated_amount and advance.allocated_amount > 0:
                # Get mode of payment from linked Payment Entry
                payment_mode = _get_payment_mode_from_pe(advance.reference_name)
                sifen_tipo = _get_sifen_payment_type(payment_mode)

                entrega = {
                    "tipo": sifen_tipo,
                    "monto": str(abs(float(advance.allocated_amount))),
                    "moneda": moneda,
                    "cambio": cambio_valor if moneda != "PYG" else 0
                }
                entregas.append(entrega)

    # 3. Check payment schedule with payment terms (for credit invoices)
    if hasattr(doc, 'payment_schedule') and doc.payment_schedule:
        for term in doc.payment_schedule:
            if term.payment_amount and term.payment_amount > 0:
                # Skip if already added as advance
                if _is_advance_already_added(term, entregas):
                    continue

                # Get payment mode from linked Payment Entry or invoice
                payment_mode = _get_payment_mode_from_pe_for_term(doc, term)
                sifen_tipo = _get_sifen_payment_type(payment_mode)

                entrega = {
                    "tipo": sifen_tipo,
                    "monto": str(abs(float(term.payment_amount))),
                    "moneda": moneda,
                    "cambio": cambio_valor if moneda != "PYG" else 0
                }

                # Add additional info for specific payment types
                if sifen_tipo in [3, 4]:  # Tarjeta de crédito/débito
                    card_info = _get_card_info(payment_mode)
                    if card_info:
                        entrega["infoTarjeta"] = card_info

                if sifen_tipo == 2:  # Cheque
                    cheque_info = _get_cheque_info(payment_mode)
                    if cheque_info:
                        entrega["infoCheque"] = cheque_info

                entregas.append(entrega)

    return entregas


def _get_payment_mode_from_pe(reference_name):
    """
    Get mode of payment from linked Payment Entry.

    Args:
        reference_name: Payment Entry name or reference

    Returns:
        str: Mode of payment name
    """
    if not reference_name:
        return None

    try:
        # Try to get Payment Entry directly
        pe = frappe.get_doc("Payment Entry", reference_name)
        if pe and hasattr(pe, 'mode_of_payment'):
            return pe.mode_of_payment
    except Exception:
        pass

    return None


def _get_payment_mode_from_pe_for_term(sales_invoice, term):
    """
    Get mode of payment from Payment Entry linked to a payment term.

    Args:
        sales_invoice: Sales Invoice document
        term: Payment Schedule term

    Returns:
        str: Mode of payment name
    """
    # Try to find Payment Entry references for this invoice
    try:
        # Get Payment Entry References linked to this Sales Invoice
        pe_refs = frappe.get_all(
            "Payment Entry Reference",
            filters={
                "reference_doctype": "Sales Invoice",
                "reference_name": sales_invoice.name
            },
            fields=["parent", "allocated_amount"]
        )

        if pe_refs:
            # Get the Payment Entry and its mode of payment
            for pe_ref in pe_refs:
                pe = frappe.get_doc("Payment Entry", pe_ref.parent)
                if pe and hasattr(pe, 'mode_of_payment'):
                    return pe.mode_of_payment
    except Exception:
        pass

    # Fallback: Try to get from payment term itself
    if term and hasattr(term, 'payment_term') and term.payment_term:
        try:
            payment_term = frappe.get_doc("Payment Term", term.payment_term)
            if payment_term and hasattr(payment_term, 'mode_of_payment'):
                return payment_term.mode_of_payment
        except Exception:
            pass

    # Fallback: Try from invoice payments
    if hasattr(sales_invoice, 'payments') and sales_invoice.payments:
        for payment in sales_invoice.payments:
            if payment.amount and payment.amount > 0:
                return payment.mode_of_payment

    # Fallback: Try from invoice field
    if hasattr(sales_invoice, 'mode_of_payment') and sales_invoice.mode_of_payment:
        return sales_invoice.mode_of_payment

    return None


def _get_payment_mode(sales_invoice, term=None):
    """
    Get the mode of payment from invoice or payment term.
    Legacy function for backward compatibility.

    Priority:
    1. From Payment Entry linked to invoice
    2. From payment term (if linked to Payment Entry)
    3. From invoice payments table
    4. From invoice mode_of_payment field
    5. Default based on invoice type
    """
    # First try to get from Payment Entry
    if hasattr(sales_invoice, 'name'):
        payment_mode = _get_payment_mode_from_pe_for_term(sales_invoice, term)
        if payment_mode:
            return payment_mode

    # Try to get from payment term
    if term and hasattr(term, 'payment_term') and term.payment_term:
        try:
            payment_term = frappe.get_doc("Payment Term", term.payment_term)
            if payment_term.mode_of_payment:
                return payment_term.mode_of_payment
        except Exception:
            pass

    # Try to get from invoice payments
    if hasattr(sales_invoice, 'payments') and sales_invoice.payments:
        for payment in sales_invoice.payments:
            if payment.amount and payment.amount > 0:
                return payment.mode_of_payment

    # Try to get from invoice field
    if hasattr(sales_invoice, 'mode_of_payment') and sales_invoice.mode_of_payment:
        return sales_invoice.mode_of_payment

    # Default based on invoice type
    if hasattr(sales_invoice, 'is_pos') and sales_invoice.is_pos:
        return "Cash"  # POS invoices default to cash

    return None


def _get_sifen_payment_type(payment_mode):
    """
    Map ERPNext Mode of Payment to SIFEN payment type.

    Args:
        payment_mode: Mode of Payment name from ERPNext

    Returns:
        int: SIFEN payment type code (1-99)
    """
    if not payment_mode:
        return 1  # Default to Efectivo

    mode_lower = payment_mode.lower().strip()

    # Direct lookup in mapping
    if mode_lower in SIFEN_PAYMENT_TYPE_MAP:
        return SIFEN_PAYMENT_TYPE_MAP[mode_lower]

    # Partial match
    for key, value in SIFEN_PAYMENT_TYPE_MAP.items():
        if key in mode_lower or mode_lower in key:
            return value

    # Check custom field if exists
    try:
        mode_doc = frappe.get_doc("Mode of Payment", payment_mode)
        if hasattr(mode_doc, 'sifen_tipo_pago') and mode_doc.sifen_tipo_pago:
            return int(mode_doc.sifen_tipo_pago)
    except Exception:
        pass

    # Default to Efectivo
    return 1


def _get_card_info(payment_mode):
    """
    Get card information for tarjeta de crédito/débito payments.

    Returns:
        dict: Card info with tipo, denominacion, etc.
    """
    if not payment_mode:
        return None

    mode_lower = payment_mode.lower()

    # Try to identify card type
    card_tipo = 99  # Otro
    card_denominacion = "Otro"

    for card_key, card_code in CARD_TYPE_MAP.items():
        if card_key in mode_lower:
            card_tipo = card_code
            card_denominacion = card_key.title()
            break

    # Try to get from Mode of Payment custom fields
    try:
        mode_doc = frappe.get_doc("Mode of Payment", payment_mode)
        if hasattr(mode_doc, 'sifen_tarjeta_tipo') and mode_doc.sifen_tarjeta_tipo:
            card_tipo = int(mode_doc.sifen_tarjeta_tipo)
        if hasattr(mode_doc, 'sifen_tarjeta_denominacion') and mode_doc.sifen_tarjeta_denominacion:
            card_denominacion = mode_doc.sifen_tarjeta_denominacion
        if hasattr(mode_doc, 'sifen_tarjeta_procesadora') and mode_doc.sifen_tarjeta_procesadora:
            return {
                "tipo": card_tipo,
                "tipoDescripcion": card_denominacion,
                "titular": getattr(mode_doc, 'sifen_tarjeta_titular', ''),
                "ruc": getattr(mode_doc, 'sifen_tarjeta_ruc', ''),
                "razonSocial": mode_doc.sifen_tarjeta_procesadora,
                "medioPago": getattr(mode_doc, 'sifen_medio_pago', 1),
                "codigoAutorizacion": getattr(mode_doc, 'sifen_codigo_autorizacion', '')
            }
    except Exception:
        pass

    # Return minimal card info
    return {
        "tipo": card_tipo,
        "tipoDescripcion": card_denominacion
    }


def _get_cheque_info(payment_mode):
    """
    Get cheque information for cheque payments.

    Returns:
        dict: Cheque info with numeroCheque, banco, etc.
    """
    if not payment_mode:
        return None

    # Try to get from Mode of Payment custom fields
    try:
        mode_doc = frappe.get_doc("Mode of Payment", payment_mode)
        if hasattr(mode_doc, 'sifen_cheque_banco') and mode_doc.sifen_cheque_banco:
            return {
                "numeroCheque": getattr(mode_doc, 'sifen_cheque_numero', ''),
                "banco": mode_doc.sifen_cheque_banco
            }
    except Exception:
        pass

    # Return empty cheque info (will be filled manually if needed)
    return {}


def _is_advance_already_added(term, entregas):
    """Check if advance was already added."""
    for entrega in entregas:
        if abs(float(entrega["monto"]) - float(term.payment_amount)) < 0.01:
            return True
    return False


def _build_credito_info(sales_invoice):
    """Build credit information from payment terms."""
    credito_info = {
        "tipo": 1,  # Default: Plazo
        "plazo": "",
    }

    # Try to get days from payment terms
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        total_days = 0
        for term in sales_invoice.payment_schedule:
            if hasattr(term, 'credit_days') and term.credit_days:
                total_days += int(term.credit_days)

        if total_days > 0:
            credito_info["plazo"] = f"{total_days} días"
            return credito_info

    # Try to get from payment terms template
    if hasattr(sales_invoice, 'payment_terms_template') and sales_invoice.payment_terms_template:
        try:
            template = frappe.get_doc("Payment Terms Template", sales_invoice.payment_terms_template)
            if template.terms:
                total_days = sum([int(term.credit_days or 0) for term in template.terms])
                if total_days > 0:
                    credito_info["plazo"] = f"{total_days} días"
                    return credito_info
        except Exception:
            pass

    # Fallback: calculate days from posting date to due date
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        for term in sales_invoice.payment_schedule:
            if term.due_date and term.payment_amount and term.payment_amount > 0:
                try:
                    from frappe.utils import date_diff
                    days = date_diff(term.due_date, sales_invoice.posting_date)
                    if days > 0:
                        credito_info["plazo"] = f"{days} días"
                        return credito_info
                except Exception:
                    pass

    return credito_info


def get_condicion_entregas(sales_invoice, moneda, condicion_tipo_cambio):
    """
    Legacy function for backward compatibility.
    Use build_condicion_section instead.
    """
    return _build_entregas(sales_invoice, moneda, condicion_tipo_cambio)
