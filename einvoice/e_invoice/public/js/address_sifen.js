/**
 * SIFEN Address - Usando campos estándar state, county y city
 */

frappe.ui.form.on('Address', {
    refresh: function(frm) {
        // No hacer nada, los botones están en el formulario
    },

    state: function(frm) {
        if (frm.doc.state) {
            frm.set_value('county', '');  // Distrito
            frm.set_value('city', '');    // Ciudad
        }
    },

    county: function(frm) {
        if (frm.doc.county) {
            frm.set_value('city', '');  // Limpiar ciudad si cambia distrito
        }
    },

    btn_buscar_distrito: function(frm) {
        buscar_distrito(frm);
    },

    btn_buscar_ciudad: function(frm) {
        buscar_ciudad(frm);
    }
});

function buscar_distrito(frm) {
    let departamento_codigo = null;
    if (frm.doc.state) {
        departamento_codigo = frm.doc.state.split('|')[0].trim();
    }

    let d = new frappe.ui.Dialog({
        title: 'Buscar Distrito',
        fields: [
            {
                fieldname: 'busqueda',
                fieldtype: 'Data',
                label: 'Buscar (código o nombre)',
                reqd: 1
            }
        ],
        primary_action_label: 'Buscar',
        primary_action: function(values) {
            frappe.call({
                method: 'einvoice.e_invoice.utils.address_validation.search_sifen',
                args: {
                    type: 'distrito',
                    search_term: values.busqueda,
                    departamento_codigo: departamento_codigo
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        mostrar_resultados(frm, 'distrito', r.message, d);
                    } else {
                        frappe.msgprint('No se encontraron resultados');
                    }
                }
            });
        }
    });
    d.show();
}

function buscar_ciudad(frm) {
    let distrito_codigo = null;
    if (frm.doc.county) {
        distrito_codigo = frm.doc.county.split('|')[0].trim();
    }

    let d = new frappe.ui.Dialog({
        title: 'Buscar Ciudad',
        fields: [
            {
                fieldname: 'busqueda',
                fieldtype: 'Data',
                label: 'Buscar (código o nombre)',
                reqd: 1
            }
        ],
        primary_action_label: 'Buscar',
        primary_action: function(values) {
            frappe.call({
                method: 'einvoice.e_invoice.utils.address_validation.search_ciudad_por_distrito',
                args: {
                    search_term: values.busqueda,
                    distrito_codigo: distrito_codigo
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        mostrar_resultados(frm, 'ciudad', r.message, d);
                    } else {
                        frappe.msgprint('No se encontraron resultados');
                    }
                }
            });
        }
    });
    d.show();
}

function mostrar_resultados(frm, tipo, resultados, dialog) {
    dialog.hide();

    let campos = [];
    resultados.forEach(function(item) {
        campos.push({
            fieldname: 'btn_' + item.value,
            fieldtype: 'Button',
            label: item.label,
            click: function() {
                let nombre = item.label.split('|')[1].trim();
                let codigo = item.value;
                let valor = codigo + '|' + nombre;
                
                if (tipo === 'distrito') {
                    frm.set_value('county', valor);
                    frm.refresh_field('county');
                } else {
                    frm.set_value('city', valor);
                    frm.refresh_field('city');
                }
                cur_dialog.hide();
            }
        });
    });

    let d = new frappe.ui.Dialog({
        title: 'Resultados (' + resultados.length + ')',
        fields: campos
    });
    d.show();
}
