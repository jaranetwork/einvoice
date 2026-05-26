# Copyright (c) 2026, Ruben Jara and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime

def validate(doc, method=None):
    validate_customer_group_for_sifen(doc)

def validate_customer_group_for_sifen(doc):
    if doc.customer_group == "All Customer Groups":
        frappe.throw(_(
            "Debe seleccionar una Categoría de Cliente específica para SIFEN.<br><br>"
            "Opciones válidas:<br>"
            "1- Comercial (B2B)<br>"
            "2- Gubernamental (B2G)<br>"
            "3- Persona Física (B2C)<br>"
            "4- Sin fines de lucro (B2F)"
        ))

def before_insert(doc, method=None):
    """
    Generate SIFEN customer code automatically before inserting Customer.
    Format: CUST-YYYY-##### (e.g., CUST-2026-00001)
    """
    generate_sifen_customer_code(doc)

def generate_sifen_customer_code(doc):
    """
    Generate unique customer code for SIFEN.
    Format: CUST-.YYYY.-#####
    
    Args:
        doc: Customer document
    """
    # Only generate if not already set
    if doc.sifen_codigo_cliente:
        return
    
    # Get current year
    year = now_datetime().year
    
    # Get last customer code for this year
    last_customer = frappe.db.get_value(
        "Customer",
        {"sifen_codigo_cliente": ["like", f"CUST-{year}-%"]},
        "sifen_codigo_cliente",
        order_by="sifen_codigo_cliente desc"
    )
    
    if last_customer:
        # Extract last number and increment
        try:
            last_number = int(last_customer.split("-")[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    
    # Format new code: CUST-2026-00001
    doc.sifen_codigo_cliente = f"CUST-{year}-{new_number:05d}"


def update_existing_customers():
    """
    Update sifen_codigo_cliente for all existing customers that don't have it.
    Format: CUST-YYYY-#####
    
    Usage:
        bench --site [site-name] execute einvoice.e_invoice.doctype.customer.customer.update_existing_customers
    """
    print("\n" + "="*60)
    print("UPDATING EXISTING CUSTOMERS WITH SIFEN CODE")
    print("="*60 + "\n")
    
    # Get all customers without sifen_codigo_cliente
    customers = frappe.get_all(
        "Customer",
        filters={"sifen_codigo_cliente": ["in", ["", None]]},
        fields=["name", "customer_name", "creation"],
        order_by="creation asc"
    )
    
    if not customers:
        print("✅ All customers already have sifen_codigo_cliente")
        return
    
    print(f"Found {len(customers)} customers without sifen_codigo_cliente\n")
    
    # Group customers by year of creation
    customers_by_year = {}
    for customer in customers:
        year = customer.creation.year if customer.creation else now_datetime().year
        if year not in customers_by_year:
            customers_by_year[year] = []
        customers_by_year[year].append(customer)
    
    # Update each customer
    updated_count = 0
    error_count = 0
    
    for year, year_customers in sorted(customers_by_year.items()):
        print(f"\nProcessing year {year} ({len(year_customers)} customers)...")
        
        # Get the last used number for this year
        last_customer = frappe.db.get_value(
            "Customer",
            {"sifen_codigo_cliente": ["like", f"CUST-{year}-%"]},
            "sifen_codigo_cliente",
            order_by="sifen_codigo_cliente desc"
        )
        
        if last_customer:
            try:
                last_number = int(last_customer.split("-")[-1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1
        
        # Update each customer in this year
        for customer in year_customers:
            try:
                # Generate code
                new_code = f"CUST-{year}-{next_number:05d}"
                
                # Update customer
                frappe.db.set_value(
                    "Customer",
                    customer.name,
                    "sifen_codigo_cliente",
                    new_code,
                    update_modified=False
                )
                
                print(f"  ✓ {customer.name} → {new_code}")
                next_number += 1
                updated_count += 1
                
            except Exception as e:
                print(f"  ✗ {customer.name}: {str(e)[:50]}")
                error_count += 1
    
    # Commit changes
    frappe.db.commit()
    
    print("\n" + "="*60)
    print(f"UPDATE COMPLETE")
    print(f"  Updated: {updated_count} customers")
    print(f"  Errors: {error_count} customers")
    print("="*60 + "\n")
