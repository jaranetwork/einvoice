// Purchase Invoice E-Invoice functionality (autofactura)
// Realtime listener for SIFEN status updates
frappe.realtime.on("sifen_status_update", function(data) {
    frappe.show_alert({
        message: __("E-Factura {0}: {1}", [data.invoice_name, data.estado]),
        indicator: data.estado === "Aceptado" ? "green" : "orange"
    });
    if (cur_frm && cur_frm.doc.name === data.invoice_name && data.doctype === "Purchase Invoice") {
        _apply_einvoice_data(cur_frm, data);
        update_einvoice_buttons(cur_frm);
    }
});

frappe.realtime.on("sifen_status_final", function(data) {
    frappe.show_alert({
        message: __("\u2705 E-Factura {0}: {1}", [data.invoice_name, data.estado]),
        indicator: data.estado === "Aceptado" ? "green" : "red"
    });
    if (cur_frm && cur_frm.doc.name === data.invoice_name && data.doctype === "Purchase Invoice") {
        _apply_einvoice_data(cur_frm, data);
        update_einvoice_buttons(cur_frm);
    }
});

function _apply_einvoice_data(frm, data) {
    if (data.estado) frm.set_value("custom_sifen_estado", data.estado);
    if (data.cdc) frm.set_value("custom_sifen_cdc", data.cdc);
    if (data.correlativo) frm.set_value("custom_sifen_correlativo", data.correlativo);
    if (data.factura_id) frm.set_value("custom_sifen_factura_id", data.factura_id);
    if (data.generated_date) frm.set_value("custom_einvoice_generated_date", data.generated_date);
}

function update_einvoice_buttons(frm) {
    if (!frm || frm.doc.__islocal) return;

    var einv_btn_group = frm.custom_buttons && frm.custom_buttons['E-Invoice'];
    if (einv_btn_group) {
        einv_btn_group.remove();
        delete frm.custom_buttons['E-Invoice'];
    }

    var estado = frm.doc.custom_sifen_estado || '';
    var is_final = ["Aceptado", "Rechazado", "Error"].includes(estado);
    var has_factura = !!frm.doc.custom_sifen_factura_id;

    if (frm.doc.docstatus === 1) {
        if (!has_factura || !is_final) {
            frm.add_custom_button(__('Generate E-Invoice'), function() {
                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.purchase_invoice.trigger_einvoice_generation',
                    args: { invoice_name: frm.doc.name },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frm.refresh();
                            frappe.show_alert({ message: __('✅ E-Invoice enviada. Verificando estado automáticamente...'), indicator: 'green' });
                        } else {
                            frappe.show_alert({ message: __('Error: ' + (r.message ? r.message.message : 'Unknown error')), indicator: 'red' });
                        }
                    }
                });
            }, __('E-Invoice'));
        }

        frm.add_custom_button(__('🔄 Refresh Status'), function() {
            frappe.call({
                method: 'einvoice.e_invoice.doc_events.purchase_invoice.force_refresh_einvoice_status',
                args: { invoice_name: frm.doc.name },
                callback: function(r) { if (r.message) update_einvoice_buttons(frm); }
            });
        }, __('E-Invoice'));

        if (frappe.user.has_role('Administrator')) {
            frm.add_custom_button(__('\u26a0\ufe0f Regenerate and Send'), function() {
                frappe.confirm(__('This will extract all data again from the invoice fields and resend to SIFEN API.<br/><br/>Are you sure you want to continue?'), function() {
                    frappe.call({
                        method: 'einvoice.e_invoice.doc_events.purchase_invoice.generate_einvoice_manually_button',
                        args: { invoice_name: frm.doc.name, regenerate: true },
                        callback: function(r) {
                            if (r.message) { frappe.show_alert({ message: __('✅ E-Invoice reenviada. Verificando estado automáticamente...'), indicator: 'green' }); }
                        }
                    });
                });
            }, __('E-Invoice'));
        }

        if (has_factura) {
            frm.add_custom_button(__('Download XML'), function() { download_einvoice_file(frm, 'xml'); }, __('E-Invoice'));
            frm.add_custom_button(__('Download KUDE'), function() { download_einvoice_file(frm, 'kude'); }, __('E-Invoice'));
            frm.add_custom_button(__('🖨️ Print KUDE'), function() { print_kude_direct(frm); }, __('E-Invoice'));
        }
    }

    frm.add_custom_button(__('👁️ HTML Preview'), function() {
        frappe.call({
            method: 'einvoice.e_invoice.doc_events.purchase_invoice.get_einvoice_preview_html',
            args: { invoice_name: frm.doc.name },
            callback: function(r) {
                if (r.message) {
                    var d = new frappe.ui.Dialog({ title: __('SIFEN Preview'), size: 'extra-large', fields: [{ fieldname: 'preview_html', fieldtype: 'HTML' }] });
                    d.fields_dict.preview_html.$wrapper.html(r.message);
                    d.show();
                }
            }
        });
    }, __('E-Invoice'));
}

frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        frm.toggle_display('sifen_motivo_nota_credito_debito',
            frm.doc.is_return || frm.doc.is_debit_note);

        frm.toggle_display('sifen_cdc_factura_original',
            frm.doc.is_return || frm.doc.is_debit_note);

        if (frm.doc.is_return || frm.doc.is_debit_note) {
            frm.set_df_property('sifen_motivo_nota_credito_debito', 'reqd', 1);
            frm.set_df_property('sifen_cdc_factura_original', 'reqd', 1);
        } else {
            frm.set_df_property('sifen_motivo_nota_credito_debito', 'reqd', 0);
            frm.set_df_property('sifen_cdc_factura_original', 'reqd', 0);
        }

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

function print_kude_direct(frm) {
    if (!frm.doc.custom_sifen_factura_id) {
        frappe.msgprint(__('Factura ID no encontrado. Por favor, genere el E-Invoice primero.'));
        return;
    }

    const factura_id = frm.doc.custom_sifen_factura_id;
    const invoice_name = frm.doc.name;

    frappe.show_alert({
        message: __('Obteniendo PDF para impresión...'),
        indicator: 'blue'
    });

    frappe.call({
        method: 'einvoice.e_invoice.utils.api_client.download_sifen_file',
        args: {
            factura_id: factura_id,
            file_type: 'kude',
            invoice_name: invoice_name
        },
        callback: function(r) {
            if (!r.message) return;

            const byteCharacters = atob(r.message.file_content);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'application/pdf' });
            const blobUrl = window.URL.createObjectURL(blob);

            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = blobUrl;
            document.body.appendChild(iframe);

            iframe.onload = function() {
                setTimeout(function() {
                    iframe.contentWindow.print();
                }, 500);
                setTimeout(function() {
                    document.body.removeChild(iframe);
                    window.URL.revokeObjectURL(blobUrl);
                }, 60000);
            };

            frappe.show_alert({
                message: __('✅ PDF listo. Abriendo diálogo de impresión...'),
                indicator: 'green'
            });
        },
        error: function(err) {
            frappe.show_alert({
                message: __('Error al obtener PDF: {0}', [err.message]),
                indicator: 'red'
            });
        }
    });
}
