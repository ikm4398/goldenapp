frappe.ui.form.on("Attendance2", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			// 1 means submitted
			frm.add_custom_button(__("Cancel"), function () {
				frm.trigger("before_cancel");
				frappe.call({
					method: "frappe.client.cancel",
					args: {
						doc: frm.doc,
					},
					callback: function (r) {
						if (!r.exc) {
							frm.reload_doc();
						}
					},
				});
			});
		}
	},
});
