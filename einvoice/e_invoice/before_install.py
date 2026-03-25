import frappe
import os

def before_install():
    """
    Clean up old property setters before installing new ones.
    This prevents conflicts with old reqd=1 settings.
    """
    print("\n" + "="*60)
    print("CLEANING UP OLD PROPERTY SETTERS")
    print("="*60 + "\n")
    
    # Clean up county reqd property setter
    cleanup_property_setter("Address", "county", "reqd")
    
    # Clean up state reqd property setter  
    cleanup_property_setter("Address", "state", "reqd")
    
    # Clean up city reqd property setter
    cleanup_property_setter("Address", "city", "reqd")
    
    frappe.db.commit()
    print("\n✅ Cleanup complete!\n")


def cleanup_property_setter(doc_type, field_name, property):
    """
    Delete all property setters for a specific field/property combination.
    """
    existing = frappe.db.get_all("Property Setter", filters={
        "doc_type": doc_type,
        "field_name": field_name,
        "property": property
    }, pluck="name")
    
    if existing:
        for ps_name in existing:
            frappe.delete_doc("Property Setter", ps_name, force=True)
            print(f"  Deleted: {doc_type}-{field_name}-{property} ({ps_name})")
    else:
        print(f"  No existing: {doc_type}-{field_name}-{property}")


if __name__ == "__main__":
    before_install()
