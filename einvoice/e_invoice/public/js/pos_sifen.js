frappe.provide("einvoice.pos");

(function () {
	"use strict";

	einvoice.pos._summaries = {};

	frappe.realtime.on("sifen_status_update", function (data) {
		var summary = einvoice.pos._summaries[data.invoice_name];
		if (!summary) return;
		if (data.doctype && data.doctype !== "Sales Invoice") return;

		if (data.estado) summary.doc.custom_sifen_estado = data.estado;
		if (data.cdc) summary.doc.custom_sifen_cdc = data.cdc;
		if (data.correlativo)
			summary.doc.custom_sifen_correlativo = data.correlativo;
		if (data.factura_id)
			summary.doc.custom_sifen_factura_id = data.factura_id;
		if (data.proceso)
			summary.doc.custom_sifen_proceso = data.proceso;

		summary.$summary_container
			.find(".sifen-summary-btns")
			.remove();
		summary._render_sifen_buttons();
	});

	frappe.realtime.on("sifen_status_final", function (data) {
		var summary = einvoice.pos._summaries[data.invoice_name];
		if (!summary) return;
		if (data.doctype && data.doctype !== "Sales Invoice") return;

		if (data.estado) summary.doc.custom_sifen_estado = data.estado;
		if (data.cdc) summary.doc.custom_sifen_cdc = data.cdc;
		if (data.correlativo)
			summary.doc.custom_sifen_correlativo = data.correlativo;
		if (data.factura_id)
			summary.doc.custom_sifen_factura_id = data.factura_id;
		if (data.proceso)
			summary.doc.custom_sifen_proceso = data.proceso;

		summary.$summary_container
			.find(".sifen-summary-btns")
			.remove();
		summary._render_sifen_buttons();

		frappe.show_alert({
			message: __("E-Factura {0}: {1}", [
				data.invoice_name,
				data.estado,
			]),
			indicator: data.estado === "Aceptado" ? "green" : "red",
		});
	});

	function _patch() {
		if (
			!erpnext.PointOfSale ||
			!erpnext.PointOfSale.PastOrderSummary
		) {
			setTimeout(_patch, 200);
			return;
		}

		var _orig_load_summary_of =
			erpnext.PointOfSale.PastOrderSummary.prototype.load_summary_of;

		erpnext.PointOfSale.PastOrderSummary.prototype.load_summary_of =
			function (doc, after_submission) {
				_orig_load_summary_of.call(this, doc, after_submission);
				if (doc && doc.doctype === "Sales Invoice" && doc.name) {
					einvoice.pos._summaries[doc.name] = this;
				}
			};

		var _orig_add_summary_btns =
			erpnext.PointOfSale.PastOrderSummary.prototype.add_summary_btns;

		erpnext.PointOfSale.PastOrderSummary.prototype.add_summary_btns =
			function (map) {
				_orig_add_summary_btns.call(this, map);
				this._render_sifen_buttons();
			};

		erpnext.PointOfSale.PastOrderSummary.prototype._render_sifen_buttons =
			function () {
				var doc = this.doc;
				if (
					!doc ||
					doc.doctype !== "Sales Invoice" ||
					doc.docstatus !== 1
				)
					return;

				var $sifenRow = this.$summary_container.find(
					".sifen-summary-btns"
				);
				if (!$sifenRow.length) {
					$sifenRow = $(
						'<div class="sifen-summary-btns">'
					).css({
						display: "flex",
						gap: "var(--margin-xs, 4px)",
						padding: "0 var(--padding-sm, 8px)",
					});
					this.$summary_btns.after($sifenRow);
				} else {
					$sifenRow.empty();
				}

				var estado = doc.custom_sifen_estado || "";
				var has_factura = !!doc.custom_sifen_factura_id;
				var pdf_listo =
					doc.custom_sifen_proceso === "Completado";
				var is_final = ["Aceptado", "Rechazado", "Error"].includes(
					estado
				);
				var is_processing =
					estado === "Pendiente" || estado === "Procesando";

				if (!has_factura || !is_final) {
					var genText = is_processing
						? "\u23F3 " + __("Generating...")
						: __("Generate E-Invoice");
					$sifenRow.append(
						'<div class="summary-btn btn btn-default generate-einvoice-btn"' +
							(is_processing ? ' disabled="disabled"' : "") +
							">" +
							genText +
							"</div>"
					);
				}

				if (has_factura && pdf_listo) {
					$sifenRow.append(
						'<div class="summary-btn btn btn-default print-einvoice-btn">' +
							"\uD83D\uDDA8\uFE0F " +
							__("Print E-Invoice") +
							"</div>"
					);
				}

				$sifenRow.append(
					'<div class="summary-btn btn btn-default refresh-status-btn">' +
						"\uD83D\uDD04 " +
						__("Refresh Status") +
						"</div>"
				);

				$sifenRow.children().css({
					flex: "1",
					"margin": "0 var(--margin-xs, 4px)",
				});
			};

		var _orig_bind_events =
			erpnext.PointOfSale.PastOrderSummary.prototype.bind_events;

		erpnext.PointOfSale.PastOrderSummary.prototype.bind_events =
			function () {
				_orig_bind_events.call(this);
				this._bind_sifen_events();
			};

		erpnext.PointOfSale.PastOrderSummary.prototype._bind_sifen_events =
			function () {
				var me = this;

				this.$summary_container.on(
					"click",
					".generate-einvoice-btn:not([disabled])",
					function () {
						me._generate_einvoice();
					}
				);

				this.$summary_container.on(
					"click",
					".print-einvoice-btn",
					function () {
						me._print_einvoice();
					}
				);

				this.$summary_container.on(
					"click",
					".refresh-status-btn",
					function () {
						me._refresh_status();
					}
				);
			};

		erpnext.PointOfSale.PastOrderSummary.prototype._generate_einvoice =
			function () {
				var me = this;
				var $btn = this.$summary_container.find(
					".generate-einvoice-btn"
				);
				$btn.text("\u23F3 " + __("Generating...")).prop(
					"disabled",
					true
				);

				frappe.call({
					method:
						"einvoice.e_invoice.doc_events.sales_invoice.trigger_einvoice_generation",
					args: { invoice_name: this.doc.name },
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __(
									"E-Invoice sent to SIFEN. Checking status..."
								),
								indicator: "green",
							});
							$btn.text(__("Sent"));
							var fid =
								r.message.data &&
								r.message.data.facturaId;
							if (fid)
								me.doc.custom_sifen_factura_id = fid;
							var proc =
								r.message.data &&
								r.message.data.proceso;
							if (proc)
								me.doc.custom_sifen_proceso = proc;
							me.$summary_container
								.find(".sifen-summary-btns")
								.remove();
							me._render_sifen_buttons();
						} else {
							$btn.text(__("Generate E-Invoice")).prop(
								"disabled",
								false
							);
							frappe.show_alert({
								message: __("Error: {0}", [
									r.message
										? r.message.message
										: "Unknown",
								]),
								indicator: "red",
							});
						}
					},
					error: function () {
						$btn.text(__("Generate E-Invoice")).prop(
							"disabled",
							false
						);
						frappe.show_alert({
							message: __(
								"Network error. Please try again."
							),
							indicator: "red",
						});
					},
				});
			};

		erpnext.PointOfSale.PastOrderSummary.prototype._print_einvoice =
			function () {
				var doc = this.doc;
				if (!doc.custom_sifen_factura_id) return;

				frappe.show_alert({
					message: __("Obteniendo PDF para impresi\u00F3n..."),
					indicator: "blue",
				});

				frappe.call({
					method:
						"einvoice.e_invoice.utils.api_client.download_sifen_file",
					args: {
						factura_id: doc.custom_sifen_factura_id,
						file_type: "kude",
						invoice_name: doc.name,
					},
					callback: function (r) {
						if (!r.message) return;

						var byteCharacters = atob(r.message.file_content);
						var byteNumbers = new Array(
							byteCharacters.length
						);
						for (var i = 0; i < byteCharacters.length; i++) {
							byteNumbers[i] =
								byteCharacters.charCodeAt(i);
						}
						var byteArray = new Uint8Array(byteNumbers);
						var blob = new Blob([byteArray], {
							type: "application/pdf",
						});
						var blobUrl = window.URL.createObjectURL(blob);

						var iframe = document.createElement("iframe");
						iframe.style.display = "none";
						iframe.src = blobUrl;
						document.body.appendChild(iframe);

						iframe.onload = function () {
							setTimeout(function () {
								iframe.contentWindow.print();
							}, 500);
							setTimeout(function () {
								document.body.removeChild(iframe);
								window.URL.revokeObjectURL(blobUrl);
							}, 60000);
						};

						frappe.show_alert({
							message: __(
								"PDF ready. Opening print dialog..."
							),
							indicator: "green",
						});
					},
					error: function (err) {
						frappe.show_alert({
							message: __("Error: {0}", [err.message]),
							indicator: "red",
						});
					},
				});
			};

		erpnext.PointOfSale.PastOrderSummary.prototype._refresh_status =
			function () {
				var me = this;
				var doc = this.doc;

				if (!doc.custom_sifen_factura_id) {
					frappe.show_alert({
						message: __("No E-Invoice generated yet."),
						indicator: "orange",
					});
					return;
				}

				frappe.call({
					method:
						"einvoice.e_invoice.doc_events.sales_invoice.force_refresh_einvoice_status",
					args: { invoice_name: doc.name },
					callback: function (r) {
						if (!r.message) return;
						frappe.db
							.get_value("Sales Invoice", doc.name, [
								"custom_sifen_estado",
								"custom_sifen_cdc",
								"custom_sifen_correlativo",
								"custom_sifen_factura_id",
								"custom_sifen_proceso",
							])
							.then(function (res) {
								var data = res.message;
								if (data.custom_sifen_estado)
									doc.custom_sifen_estado =
										data.custom_sifen_estado;
								if (data.custom_sifen_cdc)
									doc.custom_sifen_cdc =
										data.custom_sifen_cdc;
								if (data.custom_sifen_correlativo)
									doc.custom_sifen_correlativo =
										data.custom_sifen_correlativo;
								if (data.custom_sifen_factura_id)
									doc.custom_sifen_factura_id =
										data.custom_sifen_factura_id;
								if (data.custom_sifen_proceso)
									doc.custom_sifen_proceso =
										data.custom_sifen_proceso;
								me.$summary_container
									.find(".sifen-summary-btns")
									.remove();
								me._render_sifen_buttons();
							});
					},
				});
			};
	}

	_patch();
})();
