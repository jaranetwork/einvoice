// Combined script for Sales Invoice - includes both custom buttons and E-Invoice Records tab

// Realtime listener for SIFEN status updates (funciona en cualquier página)
var _sifen_update_timeout = null;

function _apply_sifen_update(data) {
    if (!cur_frm || cur_frm.doc.name !== data.invoice_name) return;
    if (data.doctype && data.doctype !== "Sales Invoice") return;

    if (data.estado) cur_frm.set_value("custom_sifen_estado", data.estado);
    if (data.cdc) cur_frm.set_value("custom_sifen_cdc", data.cdc);
    if (data.correlativo) cur_frm.set_value("custom_sifen_correlativo", data.correlativo);
    if (data.factura_id) cur_frm.set_value("custom_sifen_factura_id", data.factura_id);
    if (data.proceso) cur_frm.set_value("custom_sifen_proceso", data.proceso);
    if (data.generated_date) cur_frm.set_value("custom_einvoice_generated_date", data.generated_date);
    update_einvoice_buttons(cur_frm);
}

frappe.realtime.on("sifen_status_update", function(data) {
    if (!["aceptado", "rechazado", "error"].includes((data.estado || "").toLowerCase())) {
        var _alertSig = "supdate_" + data.invoice_name + "|" + data.estado + "|" + data.proceso;
        if (!window.__sifen_alerts) window.__sifen_alerts = {};
        if (!window.__sifen_alerts[_alertSig]) {
            window.__sifen_alerts[_alertSig] = true;
            frappe.show_alert({
                message: __("E-Factura {0}: {1}", [data.invoice_name, data.estado]),
                indicator: "orange"
            });
        }
    }
    clearTimeout(_sifen_update_timeout);
    _sifen_update_timeout = setTimeout(function() {
        _apply_sifen_update(data);
    }, 300);
});

frappe.realtime.on("sifen_status_final", function(data) {
    var msg = data.proceso === "Completado"
        ? __("\u2705 E-Factura {0}: {1} | PDF Completado", [data.invoice_name, data.estado])
        : data.proceso === "No completado"
        ? __("\u26A0\uFE0F E-Factura {0}: {1} | PDF No completado", [data.invoice_name, data.estado])
        : __("\u2705 E-Factura {0}: {1}", [data.invoice_name, data.estado]);
    var indicator = data.proceso === "Completado" ? "green"
        : data.proceso === "No completado" ? "red"
        : (data.estado || "").toLowerCase() === "aceptado" ? "green" : "red";

    var _alertSig = "sfinal_" + data.invoice_name + "|" + data.estado + "|" + data.proceso;
    if (!window.__sifen_alerts) window.__sifen_alerts = {};
    if (!window.__sifen_alerts[_alertSig]) {
        window.__sifen_alerts[_alertSig] = true;
        frappe.show_alert({ message: msg, indicator: indicator });
    }

    clearTimeout(_sifen_update_timeout);
    _apply_sifen_update(data);
});

/**
 * Re-evaluates and refreshes E-Invoice custom buttons without full form reload.
 */
function update_einvoice_buttons(frm) {
    if (!frm || frm.doc.__islocal) return;

    // Remove only E-Invoice group buttons to re-add them
    var einv_btn_group = frm.custom_buttons && frm.custom_buttons['E-Invoice'];
    if (einv_btn_group) {
        einv_btn_group.remove();
        delete frm.custom_buttons['E-Invoice'];
    }

    var estado = frm.doc.custom_sifen_estado || '';
    var is_final = ["aceptado", "rechazado", "error"].includes(estado.toLowerCase());
    var has_factura = !!frm.doc.custom_sifen_factura_id;
    var pdf_listo = frm.doc.custom_sifen_proceso === "Completado";

    if (frm.doc.docstatus === 1) {
        // Generate (only if not generated or no estado final)
        if (!has_factura || !is_final) {
            frm.add_custom_button(__('Generate E-Invoice'), function() {
                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.sales_invoice.trigger_einvoice_generation',
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

        // Refresh Status (always visible for submitted invoices)
        frm.add_custom_button(__('🔄 Refresh Status'), function() {
            frappe.call({
                method: 'einvoice.e_invoice.doc_events.sales_invoice.force_refresh_einvoice_status',
                args: { invoice_name: frm.doc.name },
                callback: function(r) { if (r.message) update_einvoice_buttons(frm); }
            });
        }, __('E-Invoice'));

        // Regenerate and Send (Administrator only)
        if (frappe.user.has_role('Administrator')) {
            frm.add_custom_button(__('⚠️ Regenerate and Send'), function() {
                frappe.confirm(__('This will extract all data again from the invoice fields and resend to SIFEN API.<br/><br/>Are you sure you want to continue?'), function() {
                    frappe.call({
                        method: 'einvoice.e_invoice.doc_events.sales_invoice.generate_einvoice_manually_button',
                        args: { invoice_name: frm.doc.name, regenerate: true },
                        callback: function(r) {
                            if (r.message) {
                                frappe.show_alert({ message: __('✅ E-Invoice reenviada. Verificando estado automáticamente...'), indicator: 'green' });
                                update_einvoice_buttons(frm);
                            }
                        }
                    });
                });
            }, __('E-Invoice'));
        }

        // Download/Print buttons (only when factura_id exists and PDF is ready)
        if (has_factura && pdf_listo) {
            frm.add_custom_button(__('Download XML'), function() { download_einvoice_file(frm, 'xml'); }, __('E-Invoice'));
            frm.add_custom_button(__('Download KUDE'), function() { download_einvoice_file(frm, 'kude'); }, __('E-Invoice'));
            frm.add_custom_button(__('🖨️ Print KUDE'), function() { print_kude_direct(frm); }, __('E-Invoice'));
        }
    }

    // HTML Preview (any saved invoice)
    frm.add_custom_button(__('👁️ HTML Preview'), function() {
        frappe.call({
            method: 'einvoice.e_invoice.doc_events.sales_invoice.get_einvoice_preview_html',
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

frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        // Show/hide SIFEN motivo field based on is_return or is_debit_note
        frm.toggle_display('sifen_motivo_nota_credito_debito',
            frm.doc.is_return || frm.doc.is_debit_note);

        // Show/hide CDC field based on is_return or is_debit_note
        frm.toggle_display('sifen_cdc_factura_original',
            frm.doc.is_return || frm.doc.is_debit_note);

        // Make fields required if is_return or is_debit_note
        if (frm.doc.is_return || frm.doc.is_debit_note) {
            frm.set_df_property('sifen_motivo_nota_credito_debito', 'reqd', 1);
            frm.set_df_property('sifen_cdc_factura_original', 'reqd', 1);
        } else {
            frm.set_df_property('sifen_motivo_nota_credito_debito', 'reqd', 0);
            frm.set_df_property('sifen_cdc_factura_original', 'reqd', 0);
        }

        // Build E-Invoice buttons
        update_einvoice_buttons(frm);
    },

    is_pos(frm) {
        // When "Include Payment (POS)" is checked, uncheck "Es Factura Crédito"
        if (frm.doc.is_pos) {
            frm.set_value('es_factura_credito', 0);
        }
    },

    es_factura_credito(frm) {
        // When "Es Factura Crédito" is checked, uncheck "Include Payment (POS)"
        if (frm.doc.es_factura_credito) {
            frm.set_value('is_pos', 0);
        }
    }
});

/**
 * Download XML or KUDE file from SIFEN API
 * @param {Object} frm - Form object
 * @param {string} type - 'xml' or 'kude'
 */
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

    // Call server-side method to download file using factura_id directly
    frappe.call({
        method: 'einvoice.e_invoice.utils.api_client.download_sifen_file',
        args: {
            factura_id: factura_id,
            file_type: type,
            invoice_name: invoice_name
        },
        callback: function(r) {
            if (r.message) {
                // Create blob from base64 content
                const byteCharacters = atob(r.message.file_content);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: r.message.content_type });

                // Create download link
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

/**
 * Print KUDE PDF directly from SIFEN API without downloading
 * Uses hidden iframe + print() to open browser's print dialog
 * @param {Object} frm - Form object
 */
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
