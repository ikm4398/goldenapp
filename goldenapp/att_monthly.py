import frappe
from frappe.utils import add_days, nowdate

def create_attendance_summary_report():
    if not frappe.db.exists("Report", "All Employee Attendance Summary Report"):
        today = nowdate()
        from_date = add_days(today, -30)
        to_date = today

        report = frappe.get_doc({
            "doctype": "Report",
            "report_name": "All Employee Attendance Summary Report",
            "ref_doctype": "Attendance",
            "report_type": "Query Report",
            "is_standard": "No",
            "module": "Goldenapp",
            "add_total_row": 0,
            "query": """
SELECT
    emp.employee,
    emp.employee_name,
    DATEDIFF(%(to_date)s, %(from_date)s) + 1 AS total_days,

    (
        SELECT COUNT(DISTINCT att1.attendance_date)
        FROM `tabAttendance` att1
        WHERE att1.employee = emp.employee
            AND att1.status = 'Present'
            AND att1.in_time IS NOT NULL
            AND att1.docstatus = 1
            AND att1.attendance_date BETWEEN %(from_date)s AND %(to_date)s
    ) AS present_days,

    (
        SELECT COUNT(DISTINCT att3.attendance_date)
        FROM `tabAttendance` att3
        WHERE att3.employee = emp.employee
            AND att3.status = 'Half Day'
            AND att3.docstatus = 1
            AND att3.attendance_date BETWEEN %(from_date)s AND %(to_date)s
    ) AS half_days,

    (
        SELECT COUNT(DISTINCT att4.attendance_date)
        FROM `tabAttendance` att4
        WHERE att4.employee = emp.employee
            AND att4.status = 'On Leave'
            AND att4.docstatus = 1
            AND att4.attendance_date BETWEEN %(from_date)s AND %(to_date)s
    ) AS leave_days,

    (
        DATEDIFF(%(to_date)s, %(from_date)s) + 1
        - (
            SELECT COUNT(DISTINCT att1.attendance_date)
            FROM `tabAttendance` att1
            WHERE att1.employee = emp.employee
                AND att1.status = 'Present'
                AND att1.in_time IS NOT NULL
                AND att1.docstatus = 1
                AND att1.attendance_date BETWEEN %(from_date)s AND %(to_date)s
        )
        - (
            SELECT COUNT(DISTINCT att3.attendance_date)
            FROM `tabAttendance` att3
            WHERE att3.employee = emp.employee
                AND att3.status = 'Half Day'
                AND att3.docstatus = 1
                AND att3.attendance_date BETWEEN %(from_date)s AND %(to_date)s
        )
        - (
            SELECT COUNT(DISTINCT att4.attendance_date)
            FROM `tabAttendance` att4
            WHERE att4.employee = emp.employee
                AND att4.status = 'On Leave'
                AND att4.docstatus = 1
                AND att4.attendance_date BETWEEN %(from_date)s AND %(to_date)s
        )
    ) AS absent_days,

    (
        SELECT COUNT(DISTINCT att5.attendance_date)
        FROM `tabAttendance` att5
        WHERE att5.employee = emp.employee
            AND att5.docstatus = 1
            AND att5.attendance_date BETWEEN %(from_date)s AND %(to_date)s
    ) AS marked_days,

    (
        DATEDIFF(%(to_date)s, %(from_date)s) + 1
        - (
            SELECT COUNT(DISTINCT att5.attendance_date)
            FROM `tabAttendance` att5
            WHERE att5.employee = emp.employee
                AND att5.docstatus = 1
                AND att5.attendance_date BETWEEN %(from_date)s AND %(to_date)s
        )
    ) AS unmarked_days

FROM `tabEmployee` emp
WHERE emp.status = 'Active'
ORDER BY emp.employee;
            """,
            "filters": [
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
            ],
            "columns": [
                {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
                {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
                {"label": "Total Days", "fieldname": "total_days", "fieldtype": "Int", "width": 100},
                {"label": "Present Days", "fieldname": "present_days", "fieldtype": "Int", "width": 110},
                {"label": "Half Days", "fieldname": "half_days", "fieldtype": "Int", "width": 100},
                {"label": "Leave Days", "fieldname": "leave_days", "fieldtype": "Int", "width": 100},
                {"label": "Absent Days", "fieldname": "absent_days", "fieldtype": "Int", "width": 110},
                {"label": "Marked Days", "fieldname": "marked_days", "fieldtype": "Int", "width": 110},
                {"label": "Unmarked Days", "fieldname": "unmarked_days", "fieldtype": "Int", "width": 120}
            ]
        })
        report.insert(ignore_permissions=True)
        frappe.db.commit()
