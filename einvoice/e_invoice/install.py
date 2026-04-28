"""
Install script for E-Invoice module.
Creates custom fields and child table required for SIFEN integration.
"""
import frappe
import json
import os


def create_child_table_doctype():
    """Create the Child Table DocType for Actividades Economicas if it doesn't exist."""
    doctype_name = "E-Invoice Actividad Economica"

    if frappe.db.exists("DocType", doctype_name):
        print(f"Child Table {doctype_name} already exists")
        return

    try:
        # Load the JSON file
        json_path = os.path.join(
            os.path.dirname(__file__),
            "doctype",
            "e_invoice_actividad_economica",
            "e_invoice_actividad_economica.json"
        )

        with open(json_path, "r") as f:
            doctype_data = json.load(f)

        # Create the DocType
        doctype = frappe.get_doc(doctype_data)
        doctype.insert()
        frappe.db.commit()
        print(f"Created Child Table: {doctype_name}")
    except FileNotFoundError as e:
        print(f"Error: JSON file not found at {json_path}")
        print(f"Creating child table programmatically...")
        create_child_table_programmatically()
    except Exception as e:
        print(f"Error creating Child Table {doctype_name}: {str(e)}")


def create_child_table_programmatically():
    """Create child table programmatically if JSON file is missing."""
    from frappe.core.doctype.doctype.doctype import DocType
    
    doctype = frappe.new_doc("DocType")
    doctype.name = "E-Invoice Actividad Economica"
    doctype.module = "E-Invoice"
    doctype.istable = 1
    doctype.autoname = "hash"
    
    # Add fields
    doctype.append("fields", {
        "fieldname": "codigo_actividad",
        "fieldtype": "Data",
        "label": "Código de Actividad",
        "reqd": 1,
        "in_list_view": 1
    })
    
    doctype.append("fields", {
        "fieldname": "descripcion_actividad",
        "fieldtype": "Data",
        "label": "Descripción de Actividad",
        "reqd": 1,
        "in_list_view": 1
    })
    
    doctype.insert()
    frappe.db.commit()
    print("Created Child Table: E-Invoice Actividad Economica (programmatically)")


def get_custom_fields_from_json():
    """Load custom fields from JSON files in the custom folder."""
    custom_fields = []
    custom_folder = os.path.join(os.path.dirname(__file__), "custom")

    if not os.path.exists(custom_folder):
        return custom_fields

    # Process files in sorted order to ensure correct field creation sequence
    for filename in sorted(os.listdir(custom_folder)):
        if filename.endswith(".json"):
            filepath = os.path.join(custom_folder, filename)
            with open(filepath, "r") as f:
                data = json.load(f)
                if "custom_fields" in data:
                    custom_fields.extend(data["custom_fields"])

    return custom_fields


def create_custom_fields():
    """Create custom fields from JSON files."""
    custom_fields = get_custom_fields_from_json()

    if not custom_fields:
        print("No custom fields found to import")
        return

    created_count = 0
    skipped_count = 0
    error_count = 0

    # Fields to filter out during creation (system fields)
    system_fields = [
        "name", "creation", "modified", "modified_by", "owner", "idx",
        "docstatus", "_assign", "_comments", "_liked_by", "_user_tags",
        "is_system_generated", "is_virtual", "link_filters", "show_dashboard",
        "sort_options", "mandatory_depends_on", "read_only_depends_on",
        "print_width", "width", "hide_border", "hide_days", "hide_seconds",
        "allow_in_quick_entry", "ignore_xss_filter", "in_global_search",
        "in_list_view", "in_preview", "in_standard_filter", "print_hide_if_no_value",
        "doctype", "custom"  # These are redundant in custom field data
    ]

    for field_data in custom_fields:
        dt = field_data.get("dt")
        fieldname = field_data.get("fieldname")

        if not dt or not fieldname:
            print(f"Skipping invalid field data: {field_data}")
            continue

        # Check if field already exists
        existing_field = frappe.db.get_value(
            "Custom Field",
            {"dt": dt, "fieldname": fieldname}
        )

        if existing_field:
            print(f"Field {fieldname} already exists in {dt}")
            skipped_count += 1
            continue

        # Create the custom field
        try:
            # Remove system fields that shouldn't be passed during creation
            field_doc_data = {k: v for k, v in field_data.items()
                             if k not in system_fields}

            field_doc_data["doctype"] = "Custom Field"

            custom_field = frappe.get_doc(field_doc_data)
            custom_field.insert()
            print(f"Created custom field {fieldname} in {dt}")
            created_count += 1
        except Exception as e:
            print(f"Error creating field {fieldname} in {dt}: {str(e)}")
            error_count += 1

    frappe.db.commit()
    print(f"\nCustom Fields Summary:")
    print(f"  Created: {created_count}")
    print(f"  Skipped (already exist): {skipped_count}")
    print(f"  Errors: {error_count}")


def create_property_setters():
    """Create property setters from JSON files to hide/modify standard fields."""
    property_setters = []
    custom_folder = os.path.join(os.path.dirname(__file__), "custom")

    if not os.path.exists(custom_folder):
        return

    for filename in os.listdir(custom_folder):
        if filename.endswith(".json"):
            filepath = os.path.join(custom_folder, filename)
            with open(filepath, "r") as f:
                data = json.load(f)
                if "property_setters" in data:
                    property_setters.extend(data["property_setters"])

    if not property_setters:
        print("No property setters found to import")
        return

    created_count = 0
    skipped_count = 0
    error_count = 0

    for ps_data in property_setters:
        doc_type = ps_data.get("doc_type")
        # Use field_name (with underscore) as defined in JSON
        field_name = ps_data.get("field_name") or ps_data.get("fieldname")
        property = ps_data.get("property")

        if not doc_type or not field_name or not property:
            continue

        # Check if property setter already exists
        try:
            existing_ps = frappe.db.get_value(
                "Property Setter",
                {"doc_type": doc_type, "field_name": field_name, "property": property}
            )
        except Exception:
            existing_ps = None

        if existing_ps:
            # Update existing property setter if value is different
            try:
                ps_doc = frappe.get_doc("Property Setter", existing_ps)
                if ps_doc.value != ps_data.get("value"):
                    ps_doc.value = ps_data.get("value")
                    ps_doc.save()
                    print(f"Updated Property Setter for {field_name}.{property} in {doc_type}")
                    created_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"Error updating Property Setter: {str(e)}")
                error_count += 1
            continue

        # Create new property setter - filter out invalid fields
        try:
            ps_doc_data = {k: v for k, v in ps_data.items()
                          if k not in ["name", "creation", "modified", "modified_by", "owner",
                                      "idx", "docstatus", "_assign", "_comments", "_liked_by", "_user_tags",
                                      "property_type"]  # property_type is not a valid field
                          }
            ps_doc_data["doctype"] = "Property Setter"

            ps_doc = frappe.get_doc(ps_doc_data)
            ps_doc.insert()
            print(f"Created Property Setter for {field_name}.{property} in {doc_type}")
            created_count += 1
        except Exception as e:
            print(f"Error creating Property Setter: {str(e)}")
            error_count += 1

    frappe.db.commit()
    print(f"\nProperty Setters Summary:")
    print(f"  Created/Updated: {created_count}")
    print(f"  Skipped (no changes): {skipped_count}")
    print(f"  Errors: {error_count}")


def create_workspace():
    """Create E-Invoice workspace for sidebar menu as child of Accounting."""
    workspace_name = "E-Invoice"

    # Check if workspace already exists
    if frappe.db.exists("Workspace", workspace_name):
        print(f"Deleting existing Workspace {workspace_name}...")
        frappe.delete_doc("Workspace", workspace_name, force=True)

    try:
        # Create new workspace
        workspace = frappe.new_doc("Workspace")
        workspace.label = workspace_name
        workspace.title = workspace_name
        workspace.module = "E-Invoice"
        workspace.public = 1
        workspace.is_hidden = 0
        workspace.icon = "file"
        workspace.sequence_id = 25.0
        workspace.parent_page = "Accounting"  # Make it a child of Accounting

        # Add shortcut
        workspace.append("shortcuts", {
            "label": "E-Invoice Settings",
            "link_to": "E-Invoice Setting",
            "type": "DocType",
            "color": "Blue"
        })

        # Add links
        workspace.append("links", {
            "label": "E-Invoice Settings",
            "link_to": "E-Invoice Setting",
            "link_type": "DocType",
            "type": "Link",
            "onboard": 1
        })

        # Content for EditorJS
        workspace.content = '[{"id":"Fq7G8Kx9mZ","type":"header","data":{"text":"<span class=\\"h4\\">E-Invoice Configuration</span>","col":12}},{"id":"Np2L5Rw3vT","type":"shortcut","data":{"shortcut_name":"E-Invoice Settings","col":4}}]'

        workspace.insert()
        frappe.db.commit()
        print(f"Created Workspace: {workspace_name} (child of Accounting)")
    except Exception as e:
        print(f"Error creating Workspace {workspace_name}: {str(e)}")


def after_install():
    """Run after module installation."""
    print("\n" + "=" * 60)
    print("Installing E-Invoice module...")
    print("=" * 60)

    create_child_table_doctype()
    create_custom_fields()
    create_property_setters()
    create_workspace()
    create_unique_index_on_numero_control()

    # Create SIFEN IVA type field in Item Tax Template Detail (for item-level ivaTipo 1-4)
    create_sifen_tax_type_field_in_item_tax_template()

    # Reorder address fields: Country below Address Line 2, State below Country
    reorder_address_fields()

    print("\n" + "=" * 60)
    print("E-Invoice module installed successfully!")
    print("=" * 60)

    # Clear cache to reflect new fields
    frappe.clear_cache()
    print("Cache cleared successfully!")
    print("\nPlease refresh your browser to see the new fields.")


def create_unique_index_on_numero_control():
    """Create unique index on custom_numero_control + company for fast lookup."""
    print("\nCreating unique index on custom_numero_control + company...")

    # Create index for Sales Invoice
    try:
        existing_indexes = frappe.db.sql("""
            SHOW INDEX FROM `tabSales Invoice`
            WHERE Key_name = 'idx_company_numero_control'
        """, as_dict=True)

        if existing_indexes:
            print("Index idx_company_numero_control already exists in Sales Invoice")
        else:
            old_indexes = frappe.db.sql("""
                SHOW INDEX FROM `tabSales Invoice`
                WHERE Key_name = 'idx_custom_numero_control'
            """, as_dict=True)

            if old_indexes:
                frappe.db.sql("""
                    ALTER TABLE `tabSales Invoice`
                    DROP INDEX `idx_custom_numero_control`
                """)
                print("Dropped old index: idx_custom_numero_control")

            frappe.db.sql("""
                ALTER TABLE `tabSales Invoice`
                ADD UNIQUE INDEX `idx_company_numero_control` (`company`, `custom_numero_control`)
            """)
            frappe.db.commit()
            print("Created unique index: idx_company_numero_control in Sales Invoice")
    except Exception as e:
        print(f"Note (Sales Invoice): {e}")

    # Create index for Purchase Invoice
    try:
        existing_indexes = frappe.db.sql("""
            SHOW INDEX FROM `tabPurchase Invoice`
            WHERE Key_name = 'idx_company_numero_control'
        """, as_dict=True)

        if existing_indexes:
            print("Index idx_company_numero_control already exists in Purchase Invoice")
        else:
            frappe.db.sql("""
                ALTER TABLE `tabPurchase Invoice`
                ADD UNIQUE INDEX `idx_company_numero_control` (`company`, `custom_numero_control`)
            """)
            frappe.db.commit()
            print("Created unique index: idx_company_numero_control in Purchase Invoice")
    except Exception as e:
        print(f"Note (Purchase Invoice): {e}")


def create_sifen_tax_type_field_in_item_tax_template():
    """Create SIFEN IVA type field in Item Tax Template Detail table (child table)."""
    print("\nCreating SIFEN IVA type field in Item Tax Template Detail...")

    try:
        # Check if field already exists
        existing = frappe.db.exists("Custom Field", {
            "fieldname": "sifen_tipo_iva",
            "dt": "Item Tax Template Detail"
        })

        if existing:
            print("Field 'sifen_tipo_iva' already exists in Item Tax Template Detail")
            # Reload to ensure column exists in database
            frappe.reload_doc("accounts", "doctype", "item_tax_template_detail")
            print("✓ Reloaded Item Tax Template Detail schema")
            return

        # Create custom field in child table
        field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Item Tax Template Detail",
            "fieldname": "sifen_tipo_iva",
            "fieldtype": "Select",
            "label": "IVA tipo SIFEN (Afectación)",
            "insert_after": "tax_rate",
            "module": "E-Invoice",
            "options": "1|Gravado IVA\n2|Exonerado (Art.83- Ley 125/91)\n3|Exento\n4|Gravado parcial",
            "default": "1|Gravado IVA",
            "print_hide": 0,
            "report_hide": 0,
            "description": "Afectación al IVA del producto según SIFEN D013 (codigosAfectaciones): 1=Gravado, 2=Exonerado, 3=Exento, 4=Parcial"
        })

        field.insert()
        frappe.db.commit()

        # IMPORTANT: Reload doc to create column in database
        frappe.reload_doc("accounts", "doctype", "item_tax_template_detail")

        print("✓ Created field 'sifen_tipo_iva' in Item Tax Template Detail")

    except Exception as e:
        print(f"✗ Error creating SIFEN IVA type field in Item Tax Template Detail: {e}")
        import traceback
        traceback.print_exc()


def reorder_address_fields():
    """Reorder address fields for Paraguay SIFEN compliance by updating DocField idx values."""
    import frappe

    # Define field order: fieldname -> idx (position)
    # Lower idx = higher position in the form
    field_order = [
        ("address_line1", 1),
        ("address_line2", 2),
        ("country", 3),
        ("state", 4),
        ("county", 5),
        ("city", 6),
    ]

    for fieldname, new_idx in field_order:
        # Update idx directly in DocField for standard fields
        frappe.db.set_value(
            "DocField",
            {"parent": "Address", "fieldname": fieldname},
            "idx",
            new_idx
        )
        print(f"Updated idx for {fieldname} -> {new_idx}")

    frappe.db.commit()
    frappe.clear_cache(doctype='Address')
    print("✓ Address field order updated successfully")


def before_uninstall():
    """Run before module uninstallation - clean up all custom fields and property setters."""
    print("\n" + "=" * 60)
    print("Uninstalling E-Invoice module...")
    print("=" * 60)

    # Get all custom fields for Company and Address related to SIFEN
    sifen_prefixes = [
        "sifen_", "codigo_establecimiento", "numero_timbrado",
        "fecha_timbrado", "tipo_contribuyente", "tipo_regimen",
        "actividades_economicas", "datos_sifen", "responsable_sifen",
        "sifen_responsable", "custom_einvoice", "custom_sifen",
        "codigo_punto_expedicion", "btn_buscar", "sifen_campos_obligatorios",
        "sifen_column", "sifen_denominacion", "custom_einvoice_section",
        "sifen_tipo_iva", "sifen_codigo_proveedor", "sifen_tipo_contribuyente",
        "sifen_tipo_transaccion", "sifen_tipo_transaccion_section",
        "es_factura_credito"
    ]

    for doctype in ["Company", "Address", "Sales Invoice", "Purchase Invoice", "Customer", "Supplier", "POS Profile", "Item Tax Template Detail"]:
        fields = frappe.get_all(
            "Custom Field",
            filters={"dt": doctype},
            fields=["name", "fieldname"]
        )

        for field in fields:
            fieldname = field["fieldname"]
            # Check if field is SIFEN-related
            if any(fieldname.startswith(prefix) or fieldname == prefix
                   for prefix in sifen_prefixes):
                try:
                    frappe.delete_doc("Custom Field", field["name"], force=True)
                    print(f"Deleted Custom Field: {field['name']} ({doctype})")
                except Exception as e:
                    print(f"Error deleting {field['name']}: {e}")

    # Delete all property setters for Company and Address
    for doctype in ["Company", "Address", "Sales Invoice", "Purchase Invoice", "Customer", "Supplier", "POS Profile"]:
        property_setters = frappe.get_all(
            "Property Setter",
            filters={"doc_type": doctype},
            fields=["name"]
        )

        for ps in property_setters:
            try:
                frappe.delete_doc("Property Setter", ps["name"], force=True)
                print(f"Deleted Property Setter: {ps['name']}")
            except Exception as e:
                print(f"Error deleting {ps['name']}: {e}")

    # Delete child table doctype
    if frappe.db.exists("DocType", "E-Invoice Actividad Economica"):
        frappe.delete_doc("DocType", "E-Invoice Actividad Economica", force=True)
        print("Deleted Child Table: E-Invoice Actividad Economica")

    # Delete workspace
    if frappe.db.exists("Workspace", "E-Invoice"):
        frappe.delete_doc("Workspace", "E-Invoice", force=True)
        print("Deleted Workspace: E-Invoice")

    # Drop unique index on custom_numero_control
    drop_unique_index_on_numero_control()

    frappe.db.commit()
    
    print("\n" + "=" * 60)
    print("E-Invoice module uninstalled successfully!")
    print("=" * 60)

    frappe.clear_cache()
    print("Cache cleared successfully!")


def drop_unique_index_on_numero_control():
    """Drop unique index on custom_numero_control + company during uninstall."""
    print("\nDropping unique index on custom_numero_control...")

    # Drop index from Sales Invoice
    try:
        frappe.db.sql("""
            ALTER TABLE `tabSales Invoice`
            DROP INDEX `idx_company_numero_control`
        """)
        frappe.db.commit()
        print("Dropped unique index: idx_company_numero_control in Sales Invoice")
    except Exception as e:
        print(f"Note (Sales Invoice): {e}")

    try:
        frappe.db.sql("""
            ALTER TABLE `tabSales Invoice`
            DROP INDEX `idx_custom_numero_control`
        """)
        frappe.db.commit()
        print("Dropped old index: idx_custom_numero_control in Sales Invoice (if existed)")
    except Exception as e:
        pass

    # Drop index from Purchase Invoice
    try:
        frappe.db.sql("""
            ALTER TABLE `tabPurchase Invoice`
            DROP INDEX `idx_company_numero_control`
        """)
        frappe.db.commit()
        print("Dropped unique index: idx_company_numero_control in Purchase Invoice")
    except Exception as e:
        print(f"Note (Purchase Invoice): {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        before_uninstall()
    else:
        after_install()
