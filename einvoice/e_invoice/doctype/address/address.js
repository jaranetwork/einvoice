// Client script for Address - SIFEN Paraguay
// Uses server-side search from address_validation.py

// Temporary storage for hierarchical selections
frappe.einvoice = frappe.einvoice || {};
frappe.einvoice.temp = {
    selectedDepartamento: null,
    selectedDistrito: null
};

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
        
        // Clear temporary selections when country changes (if not Paraguay)
        if (frm.doc.country !== 'Paraguay') {
            frappe.einvoice.temp.selectedDepartamento = null;
            frappe.einvoice.temp.selectedDistrito = null;
        }
    },

    state(frm) {
        // Clear departamento temp storage when field is cleared
        if (!frm.doc.state) {
            frappe.einvoice.temp.selectedDepartamento = null;
        }
        // Clear distrito selection when departamento changes
        frappe.einvoice.temp.selectedDistrito = null;
        frm.set_value('county', '');
        frm.set_value('city', '');
        frm.refresh_field('county');
        frm.refresh_field('city');
    },

    county(frm) {
        // Clear distrito temp storage when field is cleared
        if (!frm.doc.county) {
            frappe.einvoice.temp.selectedDistrito = null;
        }
        // Clear ciudad selection when distrito changes
        frm.set_value('city', '');
        frm.refresh_field('city');
    },

    btn_buscar_departamento(frm) {
        // Open search dialog for departamento
        open_departamento_dialog(frm);
    },

    btn_buscar_distrito(frm) {
        // Validate that departamento has been selected
        if (!frm.doc.state && !frappe.einvoice.temp.selectedDepartamento) {
            frappe.msgprint({
                title: 'Advertencia',
                message: 'Primero debe seleccionar un Departamento antes de buscar Distrito',
                indicator: 'orange'
            });
            return;
        }
        // Open search dialog for distrito
        open_distrito_dialog(frm);
    },

    btn_buscar_ciudad(frm) {
        // Validate that distrito has been selected
        if (!frm.doc.county && !frappe.einvoice.temp.selectedDistrito) {
            frappe.msgprint({
                title: 'Advertencia',
                message: 'Primero debe seleccionar un Distrito antes de buscar Ciudad',
                indicator: 'orange'
            });
            return;
        }
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
    
    open_search_dialog(frm, 'state', departamentos, 'Departamento', false, null, null, null, function(selected) {
        // Store selected departamento in temporary storage
        frappe.einvoice.temp.selectedDepartamento = selected;
        // Clear previous distrito selection since we're selecting a new departamento
        frappe.einvoice.temp.selectedDistrito = null;
    });
}

function open_distrito_dialog(frm) {
    /**
     * Open dialog to search distrito
     * Uses server-side search (300+ districts)
     * Filters by selected departamento
     */
    // Get selected departamento (check both form field and temp storage)
    var departamento = frm.doc.state || frappe.einvoice.temp.selectedDepartamento;
    
    if (!departamento) {
        frappe.msgprint({
            title: 'Advertencia',
            message: 'Por favor seleccione primero un Departamento',
            indicator: 'orange'
        });
        return;
    }
    
    // Extract departamento code (number before |)
    var depCode = departamento.split('|')[0];
    
    open_server_search_dialog(frm, 'county', 'distrito', 'Distrito', null, null, depCode);
}

function open_ciudad_dialog(frm) {
    /**
     * Open dialog to search ciudad
     * Uses server-side search (6000+ cities)
     * Filters by selected distrito
     */
    // Get selected distrito (check both form field and temp storage)
    var distrito = frm.doc.county || frappe.einvoice.temp.selectedDistrito;
    
    if (!distrito) {
        frappe.msgprint({
            title: 'Advertencia',
            message: 'Por favor seleccione primero un Distrito',
            indicator: 'orange'
        });
        return;
    }
    
    open_server_search_dialog(frm, 'city', 'ciudad', 'Ciudad', null, null, distrito);
}

function open_search_dialog(frm, fieldname, data_list, title, is_large, pre_filter, filter_field, parent_filter, on_select_callback) {
    /**
     * Open dialog with search field for small lists
     * Supports filtering and callbacks
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
            
            // Filter results by search term
            let filtered = data_list.filter(item => 
                item.toLowerCase().includes(search_term)
            );
            
            // Apply parent filter if provided
            if (parent_filter && data_list.length > 0) {
                // Filter items that match the parent (departamento code)
                filtered = filtered.filter(item => {
                    // Items are formatted as "code|NAME"
                    // For distritos: "code|CODE_DEPTO|NAME" (server will return this format)
                    return item.includes(parent_filter);
                });
            }
            
            if (filtered.length === 0) {
                frappe.msgprint('No se encontraron resultados para "' + search_term + '"');
                d.fields_dict.results.df.options = [''];
                d.fields_dict.results.refresh();
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
                
                // Execute callback if provided
                if (on_select_callback) {
                    on_select_callback(selected);
                }
                
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

function open_server_search_dialog(frm, fieldname, search_type, title, pre_filter, filter_field, parent_filter) {
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
            
            var method, args;
            
            if (search_type === 'distrito') {
                method = 'einvoice.e_invoice.utils.address_validation.search_sifen';
                args = {type: search_type, search_term: search_term};
                if (parent_filter) {
                    args.departamento_codigo = parent_filter;
                }
            } else if (search_type === 'ciudad') {
                method = 'einvoice.e_invoice.utils.address_validation.search_ciudad_por_distrito';
                args = {search_term: search_term};
                if (parent_filter) {
                    var distrito_parts = parent_filter.split('|');
                    if (distrito_parts.length >= 2) {
                        args.distrito_codigo = distrito_parts[0];
                    }
                }
            } else {
                method = 'einvoice.e_invoice.utils.address_validation.search_sifen';
                args = {type: search_type, search_term: search_term};
            }
            
            frappe.call({
                method: method,
                args: args,
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        const results = r.message.map(item => item.label); 
                        d.fields_dict.results.df.options = results;
                        d.fields_dict.results.refresh();
                        frappe.show_alert('Se encontraron ' + results.length + ' resultados. Seleccioná uno.');
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
                
                if (search_type === 'distrito') {
                    frappe.einvoice.temp.selectedDistrito = selected;
                }
                
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
