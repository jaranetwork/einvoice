// Client script for Address - SIFEN Paraguay
// Uses server-side search from address_validation.py

frappe.ui.form.on('Address', {
    refresh(frm) {
        // Show/hide search buttons based on country
        if (frm.doc.country) {
            toggle_search_buttons(frm, frm.doc.country);
        }
    },

    country(frm) {
        // Toggle search buttons when country changes
        toggle_search_buttons(frm, frm.doc.country);
    },

    btn_buscar_departamento(frm) {
        // Open search dialog for departamento
        open_departamento_dialog(frm);
    },

    btn_buscar_distrito(frm) {
        // Open search dialog for distrito
        open_distrito_dialog(frm);
    },

    btn_buscar_ciudad(frm) {
        // Open search dialog for ciudad
        open_ciudad_dialog(frm);
    }
});

function toggle_search_buttons(frm, country) {
    /**
     * Show search buttons only for Paraguay
     */
    const show_buttons = (country === 'Paraguay');
    frm.toggle_display('btn_buscar_departamento', show_buttons);
    frm.toggle_display('btn_buscar_distrito', show_buttons);
    frm.toggle_display('btn_buscar_ciudad', show_buttons);
}

function open_departamento_dialog(frm) {
    /**
     * Open dialog to search departamento
     * Uses hardcoded list (only 18 departments)
     */
    const departamentos = [
        '1|CAPITAL', '2|CONCEPCION', '3|SAN PEDRO', '4|CORDILLERA',
        '5|GUAIRA', '6|CAAGUAZU', '7|CAAZAPA', '8|ITAPUA',
        '9|MISIONES', '10|PARAGUARI', '11|ALTO PARANA', '12|CENTRAL',
        '13|NEEMBUCU', '14|AMAMBAY', '15|PTE. HAYES', '16|BOQUERON',
        '17|ALTO PARAGUAY', '18|CANINDEYU'
    ];
    
    open_search_dialog(frm, 'state', departamentos, 'Departamento', false);
}

function open_distrito_dialog(frm) {
    /**
     * Open dialog to search distrito
     * Uses server-side search (300+ districts)
     */
    open_server_search_dialog(frm, 'county', 'distrito', 'Distrito');
}

function open_ciudad_dialog(frm) {
    /**
     * Open dialog to search ciudad
     * Uses server-side search (6000+ cities)
     */
    open_server_search_dialog(frm, 'city', 'ciudad', 'Ciudad');
}

function open_search_dialog(frm, fieldname, data_list, title, is_large) {
    /**
     * Open dialog with search field for small lists
     */
    const d = new frappe.ui.Dialog({
        title: 'Buscar ' + title,
        fields: [
            {
                label: 'Buscar ' + title,
                fieldname: 'search',
                fieldtype: 'Data',
                description: 'Escribí para buscar ' + title.toLowerCase()
            },
            {
                label: 'Resultados',
                fieldname: 'results',
                fieldtype: 'Select',
                options: data_list.slice(0, 100),
                description: 'Seleccioná un resultado'
            }
        ],
        primary_action_label: 'Buscar',
        primary_action: function() {
            const values = d.get_values();
            const search_term = (values.search || '').toLowerCase();
            
            // Filter results
            const filtered = data_list.filter(item => 
                item.toLowerCase().includes(search_term)
            );
            
            if (filtered.length === 0) {
                frappe.msgprint('No se encontraron resultados para "' + search_term + '"');
                d.fields_dict.results.df.options = [''];
                d.fields_dict.results.refresh();
            } else if (filtered.length === 1) {
                frm.set_value(fieldname, filtered[0]);
                frm.refresh_field(fieldname);
                d.hide();
                frappe.show_alert({
                    message: title + ' seleccionado: ' + filtered[0],
                    indicator: 'green'
                });
            } else {
                d.fields_dict.results.df.options = filtered.slice(0, 100);
                d.fields_dict.results.refresh();
                frappe.show_alert('Se encontraron ' + filtered.length + ' resultados. Seleccioná uno.');
            }
        },
        secondary_action_label: 'Seleccionar',
        secondary_action: function() {
            const values = d.get_values();
            const selected = values.results;
            
            if (selected && selected !== '') {
                frm.set_value(fieldname, selected);
                frm.refresh_field(fieldname);
                d.hide();
                frappe.show_alert({
                    message: title + ' seleccionado: ' + selected,
                    indicator: 'green'
                });
            } else {
                frappe.msgprint('Por favor seleccioná un resultado de la lista');
            }
        }
    });
    
    d.show();
}

function open_server_search_dialog(frm, fieldname, search_type, title) {
    /**
     * Open dialog with server-side search for large lists
     */
    const d = new frappe.ui.Dialog({
        title: 'Buscar ' + title,
        fields: [
            {
                label: 'Buscar ' + title,
                fieldname: 'search',
                fieldtype: 'Data',
                description: 'Escribí al menos 3 caracteres para buscar ' + title.toLowerCase()
            },
            {
                label: 'Resultados',
                fieldname: 'results',
                fieldtype: 'Select',
                options: [''],
                description: 'Los resultados aparecerán después de buscar'
            }
        ],
        primary_action_label: 'Buscar',
        primary_action: function() {
            const values = d.get_values();
            const search_term = values.search || '';
            
            if (search_term.length < 3) {
                frappe.msgprint('Por favor escribí al menos 3 caracteres para buscar');
                return;
            }
            
            // Call server-side search
            frappe.call({
                method: 'einvoice.e_invoice.utils.address_validation.search_sifen',
                args: {
                    type: search_type,
                    search_term: search_term
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        const results = r.message.map(item => item.label);
                        
                        if (results.length === 1) {
                            frm.set_value(fieldname, results[0]);
                            frm.refresh_field(fieldname);
                            d.hide();
                            frappe.show_alert({
                                message: title + ' seleccionado: ' + results[0],
                                indicator: 'green'
                            });
                        } else {
                            d.fields_dict.results.df.options = results;
                            d.fields_dict.results.refresh();
                            frappe.show_alert('Se encontraron ' + results.length + ' resultados. Seleccioná uno.');
                        }
                    } else {
                        frappe.msgprint('No se encontraron resultados para "' + search_term + '"');
                        d.fields_dict.results.df.options = [''];
                        d.fields_dict.results.refresh();
                    }
                }
            });
        },
        secondary_action_label: 'Seleccionar',
        secondary_action: function() {
            const values = d.get_values();
            const selected = values.results;
            
            if (selected && selected !== '') {
                frm.set_value(fieldname, selected);
                frm.refresh_field(fieldname);
                d.hide();
                frappe.show_alert({
                    message: title + ' seleccionado: ' + selected,
                    indicator: 'green'
                });
            } else {
                frappe.msgprint('Por favor seleccioná un resultado de la lista');
            }
        }
    });
    
    d.show();
}
