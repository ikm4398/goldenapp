// // // goldenapp/public/attendance_process.js
// // frappe.listview_settings["Employee Attendance"] = {
// // 	onload: function (listview) {
// // 		// Add from_date field
// // 		listview.page.add_field({
// // 			fieldname: "from_date",
// // 			label: __("From Date"),
// // 			fieldtype: "Date",
// // 		});

// // 		// Add to_date field
// // 		listview.page.add_field({
// // 			fieldname: "to_date",
// // 			label: __("To Date"),
// // 			fieldtype: "Date",
// // 		});

// // 		// Add a custom button directly in the list view header
// // 		listview.page.add_button(__("Process Attendance"), function () {
// // 			let from_date = listview.page.fields_dict.from_date.get_value();
// // 			let to_date = listview.page.fields_dict.to_date.get_value();

// // 			if (from_date && to_date) {
// // 				// Call server-side method to fetch employee check-in data
// // 				frappe.call({
// // 					method: "goldenapp.attendance_process.fetch.fetch_employee_checkins",
// // 					args: {
// // 						from_date: from_date,
// // 						to_date: to_date,
// // 					},
// // 					callback: function (response) {
// // 						if (response.message) {
// // 							// Log the fetched data
// // 							console.log("Fetched Check-in Data:", response.message);
// // 						}
// // 					},
// // 					error: function (err) {
// // 						frappe.msgprint(__("An error occurred while fetching check-in data."));
// // 						console.error("Error:", err);
// // 					},
// // 				});
// // 			} else {
// // 				frappe.msgprint(__("Please select both From Date and To Date."));
// // 			}
// // 		});
// // 	},
// // };

// frappe.listview_settings["Employee Attendance"] = {
// 	onload: function (listview) {
// 		listview.page.add_field({
// 			fieldname: "from_date",
// 			label: __("From Date"),
// 			fieldtype: "Date",
// 		});
// 		listview.page.add_field({
// 			fieldname: "to_date",
// 			label: __("To Date"),
// 			fieldtype: "Date",
// 		});

// 		listview.page.add_button(__("Process Attendance"), function () {
// 			let from_date = listview.page.fields_dict.from_date.get_value();
// 			let to_date = listview.page.fields_dict.to_date.get_value();

// 			if (from_date && to_date) {
// 				frappe.confirm(
// 					__("Are you sure you want to process attendance from {0} to {1}?", [
// 						from_date,
// 						to_date,
// 					]),
// 					function () {
// 						frappe.call({
// 							method: "goldenapp.attendance_process.fetch.fetch_employee_checkins",
// 							args: {
// 								from_date: from_date,
// 								to_date: to_date,
// 							},
// 							callback: function (response) {
// 								if (response.message) {
// 									frappe.msgprint(
// 										response.message.message ||
// 											"Attendance data processing started."
// 									);
// 								}
// 							},
// 							error: function (err) {
// 								frappe.msgprint(
// 									__("An error occurred while starting the background process.")
// 								);
// 								console.error("Error:", err);
// 							},
// 						});
// 					}
// 				);
// 			} else {
// 				frappe.msgprint(__("Please select both From Date and To Date."));
// 			}
// 		});
// 	},
// };
frappe.listview_settings["Employee Attendance"] = {
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
				// Show confirmation dialog
				frappe.confirm(
					__("Are you sure you want to process attendance records from {0} to {1}?", [
						from_date,
						to_date,
					]),
					function () {
						// On confirmation, show processing message
						frappe.show_alert({
							message: __(
								"Attendance data is now being processed in the background..."
							),
							indicator: "blue",
						});

						// Call server-side method to fetch employee check-in data
						frappe.call({
							method: "goldenapp.attendance_process.fetch.fetch_employee_checkins",
							args: {
								from_date: from_date,
								to_date: to_date,
							},
							freeze: false, // Run in background without freezing UI
							freeze_message: null,
							callback: function (response) {
								if (response.message) {
									// Show success message with number of records created
									frappe.show_alert({
										message: __(
											"Successfully processed {0} attendance records.",
											[response.message.created.length]
										),
										indicator: "green",
									});
									// Refresh the list view to show new records
									listview.refresh();
									// Log the fetched data
									console.log("Fetched Check-in Data:", response.message);
								}
							},
							error: function (err) {
								frappe.msgprint(
									__("An error occurred while processing attendance data.")
								);
								console.error("Error:", err);
							},
						});
					},
					function () {
						// On cancel, show cancellation message
						frappe.show_alert({
							message: __("Attendance processing cancelled."),
							indicator: "orange",
						});
					}
				);
			} else {
				frappe.msgprint(__("Please select both From Date and To Date."));
			}
		});
	},
};
