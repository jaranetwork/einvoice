"""
Script para crear/actualizar el workspace E-Invoice en la base de datos.
Ejecutar desde: bench --site <sitio-actual> console
"""
import frappe

def create_einvoice_workspace():
    """Crear o actualizar el workspace E-Invoice"""
    
    # Verificar si ya existe
    existing = frappe.db.exists("Workspace", "E-Invoice")
    
    if existing:
        print("Eliminando workspace existente...")
        frappe.delete_doc("Workspace", "E-Invoice", force=True)
    
    # Crear nuevo workspace
    workspace = frappe.new_doc("Workspace")
    workspace.label = "E-Invoice"
    workspace.title = "E-Invoice"
    workspace.module = "E-Invoice"
    workspace.public = 1
    workspace.is_hidden = 0
    workspace.icon = "file"
    workspace.sequence_id = 25.0
    workspace.parent_page = ""
    
    # Agregar shortcut
    workspace.append("shortcuts", {
        "label": "E-Invoice Settings",
        "link_to": "E-Invoice Setting",
        "type": "DocType",
        "color": "Blue"
    })
    
    # Agregar links
    workspace.append("links", {
        "label": "E-Invoice Settings",
        "link_to": "E-Invoice Setting",
        "link_type": "DocType",
        "type": "Link",
        "onboard": 1
    })
    
    # Contenido para EditorJS
    workspace.content = '[{"id":"Fq7G8Kx9mZ","type":"header","data":{"text":"<span class=\\"h4\\">E-Invoice Configuration</span>","col":12}},{"id":"Np2L5Rw3vT","type":"shortcut","data":{"shortcut_name":"E-Invoice Settings","col":4}}]'
    
    workspace.insert()
    frappe.db.commit()
    
    print(f"Workspace 'E-Invoice' creado exitosamente!")
    print(f"Nombre: {workspace.name}")
    print(f"Label: {workspace.label}")
    print(f"Public: {workspace.public}")
    print(f"Module: {workspace.module}")
    
    return workspace

if __name__ == "__main__":
    create_einvoice_workspace()
