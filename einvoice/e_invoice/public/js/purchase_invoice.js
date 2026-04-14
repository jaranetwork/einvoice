// Purchase Invoice E-Invoice functionality (autofactura)
frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        // Show/hide SIFEN motivo field based on is_return or is_debit_note
        if (frm.fields_dict.sifen_motivo_nota_credito_debito) {
            frm.toggle_display('sifen_motivo_nota_credito_debito',
                frm.doc.is_return || frm.doc.is_debit_note);
        }

        // Show/hide CDC field based on is_return or is_debit_note
        if (frm.fields_dict.sifen_cdc_factura_original) {
            frm.toggle_display('sifen_cdc_factura_original',
                frm.doc.is_return || frm.doc.is_debit_note);
        }

        // Make fields required if is_return or is_debit_note
        if (frm.doc.is_return || frm.doc.is_debit_note) {
            if (frm.fields_dict.sifen_motivo_nota_credito_debito) {
                frm.set_df_property('sifen_motivo_nota_credito_debito', 'reqd', 1);
            }
            if (frm.fields_dict.sifen_cdc_factura_original) {
                frm.set_df_property('sifen_cdc_factura_original', 'reqd', 1);
            }
        } else {
            if (frm.fields_dict.sifen_motivo_nota_credito_debito) {
                frm.set_df_property('sifen_motivo_nota_credito_debito', 'reqd', 0);
            }
            if (frm.fields_dict.sifen_cdc_factura_original) {
                frm.set_df_property('sifen_cdc_factura_original', 'reqd', 0);
            }
        }

        // Add a button to generate e-invoice manually
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Generate E-Invoice'), () => {
                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.purchase_invoice.trigger_einvoice_generation',
                    args: {
                        invoice_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frm.refresh();
                            frappe.show_alert({
                                message: __('E-Invoice generated successfully'),
                                indicator: 'green'
                            });
                        } else {
                            frappe.show_alert({
                                message: __('Error: ' + (r.message ? r.message.message : 'Unknown error')),
                                indicator: 'red'
                            });
                        }
                    }
                });
            }, __('E-Invoice'));
        }

        // Add a button to force refresh e-invoice status from SIFEN API
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('🔄 Refresh Status'), () => {
                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.purchase_invoice.force_refresh_einvoice_status',
                    args: {
                        invoice_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            frm.refresh();
                        }
                    }
                });
            }, __('E-Invoice'));
        }

        // Add a button to regenerate E-Invoice (extract fresh data and resend)
        // Only visible for Administrator role
        if (!frm.doc.__islocal && frappe.user.has_role('Administrator')) {
            frm.add_custom_button(__('⚠️ Regenerate and Send'), () => {
                frappe.confirm(
                    __('This will extract all data again from the invoice fields and resend to SIFEN API.<br/><br/>Are you sure you want to continue?'),
                    () => {
                        frappe.call({
                            method: 'einvoice.e_invoice.doc_events.purchase_invoice.generate_einvoice_manually_button',
                            args: {
                                invoice_name: frm.doc.name,
                                regenerate: true
                            },
                            callback: function(r) {
                                if (r.message) {
                                    frm.refresh();
                                    frappe.show_alert({
                                        message: __('E-Invoice regenerated successfully'),
                                        indicator: 'green'
                                    });
                                }
                            }
                        });
                    }
                );
            }, __('E-Invoice'));
        }

        // Add download buttons for XML and KUDE if factura_id exists
        if (frm.doc.custom_sifen_factura_id && !frm.doc.__islocal) {
            frm.add_custom_button(__('Download XML'), () => {
                download_einvoice_file(frm, 'xml');
            }, __('E-Invoice'));

            frm.add_custom_button(__('Download KUDE'), () => {
                download_einvoice_file(frm, 'kude');
            }, __('E-Invoice'));
        }

        // Add Vista Previa HTML button (works for any saved invoice)
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('👁️ Vista Previa HTML'), () => {
                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.purchase_invoice.get_einvoice_preview_html',
                    args: {
                        invoice_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            let dialog = new frappe.ui.Dialog({
                                title: __('Vista Previa SIFEN'),
                                size: 'extra-large',
                                fields: [{
                                    fieldname: 'preview_html',
                                    fieldtype: 'HTML'
                                }]
                            });
                            dialog.fields_dict.preview_html.$wrapper.html(r.message);
                            dialog.show();
                        }
                    }
                });
            }, __('E-Invoice'));
        }

        // Add a button to check e-invoice status (local data only)
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Check Local Status'), () => {
                // Pre-validation: Check if invoice is in draft
                if (frm.doc.docstatus === 0) {
                    frappe.msgprint({
                        title: __('Factura en Borrador'),
                        indicator: 'red',
                        message: __('La factura está en estado <b>Borrador</b>.<br><br>' +
                                   'Debe <b>Validar</b> la factura antes de verificar su estado en SIFEN.<br><br>' +
                                   '<strong>Acciones requeridas:</strong><br>' +
                                   '1. Guarde la factura<br>' +
                                   '2. Click en <b>Validar</b> (Submit)<br>' +
                                   '3. Luego use E-Invoice → Send to SIFEN<br>' +
                                   '4. Después puede usar Check Local Status')
                    });
                    return;
                }

                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.purchase_invoice.get_einvoice_status',
                    args: {
                        invoice_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            let msg = [];
                            msg.push(`Generated: ${r.message.generated ? 'Yes' : 'No'}`);
                            if (r.message.date) {
                                msg.push(`Date: ${r.message.date}`);
                            }
                            if (r.message.document_url) {
                                msg.push(`<a href="${r.message.document_url}" target="_blank">View Document</a>`);
                            }
                            frappe.msgprint(msg.join('<br>'));
                        }
                    }
                });
            }, __('E-Invoice'));
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
