#!/usr/bin/env python3
"""
Script to update sifen_codigo_cliente for existing customers.
Run this after installing the einvoice module.

Usage:
    bench --site [site-name] execute einvoice.e_invoice.doctype.customer.customer.update_existing_customers
"""

import frappe
from frappe.utils import now_datetime

def update_existing_customers():
    """
    Update sifen_codigo_cliente for all existing customers that don't have it.
    Format: CUST-YYYY-#####
    """
    print("\n" + "="*60)
    print("UPDATING EXISTING CUSTOMERS WITH SIFEN CODE")
    print("="*60 + "\n")
    
    # Get all customers without sifen_codigo_cliente
    customers = frappe.get_all(
        "Customer",
        filters={"sifen_codigo_cliente": ["in", ["", None]]},
        fields=["name", "customer_name"],
        order_by="creation asc"
    )
    
    if not customers:
        print("✅ All customers already have sifen_codigo_cliente")
        return
    
    print(f"Found {len(customers)} customers without sifen_codigo_cliente\n")
    
    # Group customers by year of creation
    customers_by_year = {}
    for customer in customers:
        year = customer.creation.year if hasattr(customer, 'creation') else now_datetime().year
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


if __name__ == "__main__":
    update_existing_customers()
