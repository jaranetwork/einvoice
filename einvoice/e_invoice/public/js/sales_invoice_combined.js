// Combined script for Sales Invoice - includes both custom buttons and E-Invoice Records tab
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

        // Add a button to generate e-invoice manually
        if (!frm.doc.__islocal && frm.doc.docstatus === 1) {  // Only for saved and submitted invoices
            frm.add_custom_button(__('Generate E-Invoice'), () => {
                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.sales_invoice.trigger_einvoice_generation',
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
        if (!frm.doc.__islocal && frm.doc.docstatus === 1) {
            frm.add_custom_button(__('🔄 Refresh Status'), () => {
                frappe.call({
                    method: 'einvoice.e_invoice.doc_events.sales_invoice.force_refresh_einvoice_status',
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
        if (!frm.doc.__islocal && frm.doc.docstatus === 1 && frappe.user.has_role('Administrator')) {
            frm.add_custom_button(__('⚠️ Regenerate and Send'), () => {
                frappe.confirm(
                    __('This will extract all data again from the invoice fields and resend to SIFEN API.<br/><br/>Are you sure you want to continue?'),
                    () => {
                        // User confirmed
                        frappe.call({
                            method: 'einvoice.e_invoice.doc_events.sales_invoice.generate_einvoice_manually_button',
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
            // Download XML button
            frm.add_custom_button(__('Download XML'), () => {
                download_einvoice_file(frm, 'xml');
            }, __('E-Invoice'));

            // Download KUDE button
            frm.add_custom_button(__('Download KUDE'), () => {
                download_einvoice_file(frm, 'kude');
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
                    method: 'einvoice.e_invoice.doc_events.sales_invoice.get_einvoice_status',
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
                            if (r.message.factura_id) {
                                msg.push(`<br/><strong>Factura ID:</strong> ${r.message.factura_id}`);
                            }
                            if (r.message.estado) {
                                msg.push(`<strong>Estado:</strong> ${r.message.estado}`);
                            }
                            if (r.message.cdc) {
                                msg.push(`<strong>CDC:</strong> ${r.message.cdc}`);
                            }
                            if (r.message.xml_link) {
                                msg.push(`<br/><a href="${r.message.xml_link}" target="_blank">Download XML</a>`);
                            }
                            if (r.message.kude_link) {
                                msg.push(`<a href="${r.message.kude_link}" target="_blank" style="margin-left: 10px;">Download KUDE</a>`);
                            }

                            frappe.msgprint(msg.join('<br>'), 'E-Invoice Local Status');
                        }
                    }
                });
            }, __('E-Invoice'));
        }
    }
});

function download_einvoice_file(frm, type) {
    /**
     * Download XML or KUDE file from SIFEN API
     * @param {Object} frm - Frappe form object (Sales Invoice)
     * @param {string} type - 'xml' or 'kude'
     */

    const factura_id = frm.doc.custom_sifen_factura_id;
    const invoice_name = frm.doc.name;

    console.log('[Download] factura_id:', factura_id);
    console.log('[Download] invoice_name:', invoice_name);
    console.log('[Download] type:', type);

    if (!factura_id) {
        frappe.msgprint({
            title: __('Error'),
            indicator: 'red',
            message: __('Factura ID not found.<br><br>' +
                      'Please make sure the invoice has been sent to SIFEN.')
        });
        return;
    }

    // Show loading message
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
            console.error('[Download Error]', err);
            frappe.msgprint({
                title: __('Download Error'),
                indicator: 'red',
                message: __('Failed to download {0}: {1}', [type.toUpperCase(), err.message])
            });
        }
    });
}
