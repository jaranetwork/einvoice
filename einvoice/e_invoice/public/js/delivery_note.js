// Delivery Note E-Invoice functionality (autofactura)

function _apply_einvoice_data(data) {
    if (data.estado) cur_frm.set_value("custom_sifen_estado", data.estado);
    if (data.cdc) cur_frm.set_value("custom_sifen_cdc", data.cdc);
    if (data.correlativo) cur_frm.set_value("custom_sifen_correlativo", data.correlativo);
    if (data.factura_id) cur_frm.set_value("custom_sifen_factura_id", data.factura_id);
    if (data.generated_date) cur_frm.set_value("custom_einvoice_generated_date", data.generated_date);
    update_einvoice_buttons(cur_frm);
}

frappe.realtime.on("sifen_status_update", function(data) {
    frappe.show_alert({
        message: __("E-Factura {0}: {1}", [data.invoice_name, data.estado]),
        indicator: data.estado === "Aceptado" ? "green" : "orange"
    });
    if (cur_frm && cur_frm.doc.name === data.invoice_name && data.doctype === "Delivery Note") {
        _apply_einvoice_data(data);
    }
});

frappe.realtime.on("sifen_status_final", function(data) {
    frappe.show_alert({
        message: __("✅ E-Factura {0}: {1}", [data.invoice_name, data.estado]),
        indicator: data.estado === "Aceptado" ? "green" : "red"
    });
    if (cur_frm && cur_frm.doc.name === data.invoice_name && data.doctype === "Delivery Note") {
        _apply_einvoice_data(data);
    }
});

function update_einvoice_buttons(frm) {
    if (frm.doc.__islocal) return;

    frm.clear_custom_buttons();
    frm.page.clear_inner_toolbar();

    var show_actions = frm.doc.custom_sifen_factura_id ? true : false;

    if (!show_actions) {
        frm.add_custom_button(__('Generate E-Invoice'), function() {
            frappe.call({
                method: 'einvoice.e_invoice.doc_events.delivery_note.trigger_einvoice_generation',
                args: { invoice_name: frm.doc.name },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        update_einvoice_buttons(frm);
                        frappe.show_alert({ message: __('E-Invoice generated successfully'), indicator: 'green' });
                    }
                }
            });
        }, __('E-Invoice'));
    }

    if (show_actions) {
        frm.add_custom_button(__('🔄 Refresh Status'), function() {
            frappe.call({
                method: 'einvoice.e_invoice.doc_events.delivery_note.force_refresh_einvoice_status',
                args: { invoice_name: frm.doc.name },
                callback: function(r) { if (r.message) update_einvoice_buttons(frm); }
            });
        }, __('E-Invoice'));
    }

    if (show_actions && frappe.user.has_role('Administrator')) {
        frm.add_custom_button(__('⚠️ Regenerate and Send'), function() {
            frappe.confirm(__('This will extract all data again from the invoice fields and resend to SIFEN API.<br/><br/>Are you sure you want to continue?'), function() {
                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.delivery_note.generate_einvoice_manually_button',
                    args: { invoice_name: frm.doc.name, regenerate: true },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            update_einvoice_buttons(frm);
                        }
                    }
                });
            });
        }, __('E-Invoice'));
    }

    frm.add_custom_button(__('👁️ HTML Preview'), function() {
        frappe.call({
            method: 'einvoice.e_invoice.doc_events.delivery_note.get_einvoice_preview_html',
            args: { invoice_name: frm.doc.name },
            callback: function(r) {
                if (r.message) {
                    let dialog = new frappe.ui.Dialog({
                        title: __('SIFEN Preview'),
                        size: 'extra-large',
                        fields: [{ fieldname: 'preview_html', fieldtype: 'HTML' }]
                    });
                    dialog.fields_dict.preview_html.$wrapper.html(r.message);
                    dialog.show();
                }
            }
        });
    }, __('E-Invoice'));

    // Download/Print buttons only when factura_id exists
    if (show_actions) {
        frm.add_custom_button(__('📄 Download XML'), function() {
            download_einvoice_file(frm, 'xml');
        }, __('E-Invoice'));

        frm.add_custom_button(__('📄 Download KUDE'), function() {
            download_einvoice_file(frm, 'kude');
        }, __('E-Invoice'));

        frm.add_custom_button(__('🖨️ Print KUDE'), function() {
            print_kude_direct(frm);
        }, __('E-Invoice'));
    }
}

function print_kude_direct(frm) {
    if (!frm.doc.custom_sifen_factura_id) return;

    frappe.call({
        method: 'einvoice.e_invoice.utils.api_client.download_sifen_file',
        args: {
            factura_id: frm.doc.custom_sifen_factura_id,
            file_type: 'kude',
            invoice_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                var byteCharacters = atob(r.message.file_content);
                var byteNumbers = new Array(byteCharacters.length);
                for (var i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                var byteArray = new Uint8Array(byteNumbers);
                var blob = new Blob([byteArray], { type: 'application/pdf' });
                var url = URL.createObjectURL(blob);

                var iframe = document.createElement('iframe');
                iframe.style.display = 'none';
                iframe.src = url;
                document.body.appendChild(iframe);

                iframe.onload = function() {
                    setTimeout(function() {
                        try { iframe.contentWindow.print(); } catch(e) { console.error(e); }
                    }, 500);
                };

                setTimeout(function() {
                    document.body.removeChild(iframe);
                    URL.revokeObjectURL(url);
                }, 30000);
            }
        }
    });
}

frappe.ui.form.on('Delivery Note', {
    refresh(frm) {
        update_einvoice_buttons(frm);
    }
});

function download_einvoice_file(frm, type) {
    if (!frm.doc.custom_sifen_factura_id) {
        frappe.msgprint(__('Factura ID no encontrado. Por favor, genere el E-Invoice primero.'));
        return;
    }

    const factura_id = frm.doc.custom_sifen_factura_id;
    const invoice_name = frm.doc.name;

    frappe.show_alert({
        message: __('Downloading {0}...', [type.toUpperCase()]),
        indicator: 'blue'
    });

    frappe.call({
        method: 'einvoice.e_invoice.utils.api_client.download_sifen_file',
        args: {
            factura_id: factura_id,
            file_type: type,
            invoice_name: invoice_name
        },
        callback: function(r) {
            if (r.message) {
                const byteCharacters = atob(r.message.file_content);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: r.message.content_type });

                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = r.message.filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);

                frappe.show_alert({
                    message: __('{0} downloaded successfully', [type.toUpperCase()]),
                    indicator: 'green'
                });
            }
        },
        error: function(err) {
            frappe.show_alert({
                message: __('Error downloading {0}: {1}', [type.toUpperCase(), err.message]),
                indicator: 'red'
            });
        }
    });
}
