import frappe
from frappe.utils import add_days, nowdate

def create_present_absent_summary_report():
    if not frappe.db.exists("Report", "Golden Present Absent Summary"):
        today = nowdate()
        from_date = add_days(today, -30)
        to_date = today

        report = frappe.get_doc({
            "doctype": "Report",
            "report_name": "Golden Present Absent Summary",
            "ref_doctype": "Attendance",
            "report_type": "Query Report",
            "is_standard": "No",
            "module": "Goldenapp",
            "add_total_row": 0,
            "query": """
SELECT
    att.employee,
    emp.employee_name,
    COUNT(CASE WHEN att.status = 'Present' THEN 1 END) AS present_days,
    GROUP_CONCAT(
        CASE WHEN att.status = 'Present'
        THEN DATE_FORMAT(att.attendance_date, '%Y-%m-%d') END
        ORDER BY att.attendance_date
        SEPARATOR ', '
    ) AS present_dates,
    COUNT(CASE WHEN att.status = 'Absent' THEN 1 END) AS absent_days,
    GROUP_CONCAT(
        CASE WHEN att.status = 'Absent'
        THEN DATE_FORMAT(att.attendance_date, '%Y-%m-%d') END
        ORDER BY att.attendance_date
        SEPARATOR ', '
    ) AS absent_dates
FROM `tabAttendance` att
LEFT JOIN `tabEmployee` emp ON att.employee = emp.employee
WHERE
    att.docstatus = 1
    AND att.attendance_date BETWEEN %(from_date)s AND %(to_date)s
    AND (%(employee)s IS NULL OR att.employee = %(employee)s)
GROUP BY att.employee, emp.employee_name
ORDER BY att.employee
            """,
            "filters": [
                {
                    "fieldname": "employee",
                    "label": "Employee",
                    "fieldtype": "Link",
                    "options": "Employee",
                    "reqd": 0
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
