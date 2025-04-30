import frappe
from frappe.utils import add_days, getdate, nowdate

def create_attendance_query_report():
    if not frappe.db.exists("Report", "Golden Attendance Report"):
        # Get today's date and set from_date to 1 month before today if not provided
        today = nowdate()
        from_date = add_days(today, -30)  # Set from_date to 1 month ago
        to_date = today  # Default to today
        
        report = frappe.get_doc({
            "doctype": "Report",
            "report_name": "Golden Attendance Report",
            "ref_doctype": "Attendance",
            "report_type": "Query Report",
            "is_standard": "No",
            "module": "Goldenapp",
            "add_total_row": 1,
            "query": """
SELECT
    `tabEmployee`.`employee`,
    `tabEmployee`.employee_name,
    `tabAttendance`.attendance_date,
    `tabAttendance`.attendance_day,
    COALESCE(`tabAttendance`.status, 'Absent') AS status,
    `tabAttendance`.shift,
    `tabAttendance`.in_time,
    `tabAttendance`.out_time,
    CASE WHEN ABS(`tabAttendance`.working_hours) > 22 THEN 0 ELSE ROUND(ABS(`tabAttendance`.working_hours), 3) END AS working_hours,
    `tabAttendance`.late_entry
FROM
    `tabEmployee`
LEFT JOIN
    `tabAttendance`
ON `tabEmployee`.employee = `tabAttendance`.employee
AND `tabAttendance`.attendance_date BETWEEN %(from_date)s AND %(to_date)s
AND `tabAttendance`.docstatus = 1
AND ABS(`tabAttendance`.working_hours) <= 22
WHERE
    (%(employee)s IS NULL OR `tabEmployee`.employee IN (%(employee)s))
ORDER BY
    `tabEmployee`.employee, `tabAttendance`.attendance_date,
    LEAST(`tabAttendance`.in_time, `tabAttendance`.out_time) ASC,
    GREATEST(`tabAttendance`.in_time, `tabAttendance`.out_time) ASC
            """,
            "filters": [
                {
                    "fieldname": "employee",
                    "label": "Employee",
                    "fieldtype": "Link",
                    "options": "Employee",
                    "reqd": 0,
                    "default": "HR-EMP-00001" 
                },
                {
                    "fieldname": "from_date",
                    "label": "From Date",
                    "fieldtype": "Date",
                    "default": from_date,
                    "reqd": 1
                },
                {
                    "fieldname": "to_date",
                    "label": "To Date",
                    "fieldtype": "Date",
                    "default": to_date,
                    "reqd": 1
                }
            ]
        })
        report.insert(ignore_permissions=True)
        frappe.db.commit()
