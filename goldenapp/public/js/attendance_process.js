// goldenapp/public/attendance_process.js
frappe.listview_settings["Attendance2"] = {
	onload: function (listview) {
		// Add from_date field
		listview.page.add_field({
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		});

		// Add to_date field
		listview.page.add_field({
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		});

		// Add a custom button directly in the list view header
		listview.page.add_button(__("Process Attendance"), function () {
			let from_date = listview.page.fields_dict.from_date.get_value();
			let to_date = listview.page.fields_dict.to_date.get_value();

			if (from_date && to_date) {
				// Call server-side method to fetch employee check-in data
				frappe.call({
					method: "goldenapp.attendance_process.fetch.fetch_employee_checkins",
					args: {
						from_date: from_date,
						to_date: to_date,
					},
					callback: function (response) {
						if (response.message) {
							// Log the fetched data
							console.log("Fetched Check-in Data:", response.message);
						}
					},
					error: function (err) {
						frappe.msgprint(__("An error occurred while fetching check-in data."));
						console.error("Error:", err);
					},
				});
			} else {
				frappe.msgprint(__("Please select both From Date and To Date."));
			}
		});
	},
};
