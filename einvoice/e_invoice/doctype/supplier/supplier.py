# Copyright (c) 2026, Ruben Jara and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime


def before_insert(doc, method=None):
    """
    Generate SIFEN supplier code automatically before inserting Supplier.
    Format: SUPP-YYYY-##### (e.g., SUPP-2026-00001)
    """
    generate_sifen_supplier_code(doc)


def generate_sifen_supplier_code(doc):
    """
    Generate unique supplier code for SIFEN.
    Format: SUPP-YYYY-#####

    Args:
        doc: Supplier document
    """
    # Only generate if not already set
    if doc.sifen_codigo_proveedor:
        return

    # Get current year
    year = now_datetime().year

    # Get last supplier code for this year
    last_supplier = frappe.db.get_value(
        "Supplier",
        {"sifen_codigo_proveedor": ["like", f"SUPP-{year}-%"]},
        "sifen_codigo_proveedor",
        order_by="sifen_codigo_proveedor desc"
    )

    if last_supplier:
        # Extract last number and increment
        try:
            last_number = int(last_supplier.split("-")[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1

    # Format new code: SUPP-2026-00001
    doc.sifen_codigo_proveedor = f"SUPP-{year}-{new_number:05d}"


def update_existing_suppliers():
    """
    Update sifen_codigo_proveedor for all existing suppliers that don't have it.
    Format: SUPP-YYYY-#####

    Usage:
        bench --site [site-name] execute einvoice.e_invoice.doctype.supplier.supplier.update_existing_suppliers
    """
    print("\n" + "="*60)
    print("UPDATING EXISTING SUPPLIERS WITH SIFEN CODE")
    print("="*60 + "\n")

    # Get all suppliers without sifen_codigo_proveedor
    suppliers = frappe.get_all(
        "Supplier",
        filters={"sifen_codigo_proveedor": ["in", ["", None]]},
        fields=["name", "supplier_name", "creation"],
        order_by="creation asc"
    )

    if not suppliers:
        print("✅ All suppliers already have sifen_codigo_proveedor")
        return

    print(f"Found {len(suppliers)} suppliers without sifen_codigo_proveedor\n")

    # Group suppliers by year of creation
    suppliers_by_year = {}
    for supplier in suppliers:
        year = supplier.creation.year if supplier.creation else now_datetime().year
        if year not in suppliers_by_year:
            suppliers_by_year[year] = []
        suppliers_by_year[year].append(supplier)

    # Update each supplier
    updated_count = 0
    error_count = 0

    for year, year_suppliers in sorted(suppliers_by_year.items()):
        print(f"\nProcessing year {year} ({len(year_suppliers)} suppliers)...")

        # Get the last used number for this year
        last_supplier = frappe.db.get_value(
            "Supplier",
            {"sifen_codigo_proveedor": ["like", f"SUPP-{year}-%"]},
            "sifen_codigo_proveedor",
            order_by="sifen_codigo_proveedor desc"
        )

        if last_supplier:
            try:
                last_number = int(last_supplier.split("-")[-1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1

        # Update each supplier in this year
        for supplier in year_suppliers:
            try:
                # Generate code
                new_code = f"SUPP-{year}-{next_number:05d}"

                # Update supplier
                frappe.db.set_value(
                    "Supplier",
                    supplier.name,
                    "sifen_codigo_proveedor",
                    new_code,
                    update_modified=False
                )

                print(f"  ✓ {supplier.name} → {new_code}")
                next_number += 1
                updated_count += 1

            except Exception as e:
                print(f"  ✗ {supplier.name}: {str(e)[:50]}")
                error_count += 1

    # Commit changes
    frappe.db.commit()

    print("\n" + "="*60)
    print(f"UPDATE COMPLETE")
    print(f"  Updated: {updated_count} suppliers")
    print(f"  Errors: {error_count} suppliers")
    print("="*60 + "\n")
