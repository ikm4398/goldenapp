import frappe
from frappe.utils import add_days, nowdate

def create_attendance_query_report():
    if not frappe.db.exists("Report", "New Attendance Report"):
        today = nowdate()
        from_date = add_days(today, -30)
        to_date = today

        report = frappe.get_doc({
            "doctype": "Report",
            "report_name": "New Attendance Report",
            "ref_doctype": "Attendance",
            "report_type": "Query Report",
            "is_standard": "No",
            "module": "Goldenapp",
            "add_total_row": 1,
            "query": """
SELECT
    att.employee,
    emp.employee_name,
    att.attendance_date,
    att.attendance_day,
    att.status,
    att.shift,
    att.in_time,
    COALESCE(
        att.out_time,
        CASE
            WHEN att.in_time IS NOT NULL AND TIME(att.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                SELECT ao.out_time
                FROM `tabAttendance` ao
                WHERE ao.employee = att.employee
                  AND ao.attendance_date = att.attendance_date
                  AND ao.out_time IS NOT NULL
                  AND TIME(ao.out_time) BETWEEN '09:00:00' AND '15:00:00'
                LIMIT 1
            )
            WHEN att.in_time IS NOT NULL AND TIME(att.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                SELECT ao.out_time
                FROM `tabAttendance` ao
                WHERE ao.employee = att.employee
                  AND ao.attendance_date = att.attendance_date
                  AND ao.out_time IS NOT NULL
                  AND TIME(ao.out_time) BETWEEN '15:00:00' AND '21:00:00'
                LIMIT 1
            )
            WHEN att.in_time IS NOT NULL AND TIME(att.in_time) >= '18:00:00' AND next_att.out_time > att.in_time THEN next_att.out_time
            ELSE NULL
        END
    ) AS out_time,
    ROUND(
        CASE
            WHEN att.in_time IS NOT NULL THEN
                TIMESTAMPDIFF(
                    SECOND,
                    att.in_time,
                    COALESCE(
                        CASE
                            WHEN att.out_time IS NOT NULL AND att.out_time > att.in_time THEN att.out_time
                            WHEN TIME(att.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                                SELECT ao.out_time
                                FROM `tabAttendance` ao
                                WHERE ao.employee = att.employee
                                  AND ao.attendance_date = att.attendance_date
                                  AND ao.out_time IS NOT NULL
                                  AND ao.out_time > att.in_time
                                  AND TIME(ao.out_time) BETWEEN '09:00:00' AND '15:00:00'
                                LIMIT 1
                            )
                            WHEN TIME(att.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                                SELECT ao.out_time
                                FROM `tabAttendance` ao
                                WHERE ao.employee = att.employee
                                  AND ao.attendance_date = att.attendance_date
                                  AND ao.out_time IS NOT NULL
                                  AND ao.out_time > att.in_time
                                  AND TIME(ao.out_time) BETWEEN '15:00:00' AND '21:00:00'
                                LIMIT 1
                            )
                            WHEN TIME(att.in_time) >= '18:00:00' AND next_att.out_time > att.in_time THEN next_att.out_time
                            ELSE NULL
                        END,
                        NULL
                    )
                ) / 3600
            ELSE 0
        END, 3
    ) AS working_hours,
    att.late_entry
FROM `tabAttendance` att
LEFT JOIN `tabAttendance` next_att
    ON att.employee = next_att.employee
    AND next_att.attendance_date = DATE_ADD(att.attendance_date, INTERVAL 1 DAY)
    AND next_att.in_time IS NULL
    AND next_att.out_time IS NOT NULL
    AND TIME(next_att.out_time) BETWEEN '06:00:00' AND '10:00:00'
LEFT JOIN `tabEmployee` emp ON att.employee = emp.employee
WHERE
    att.docstatus = 1
    AND att.attendance_date BETWEEN %(from_date)s AND %(to_date)s
    AND (%(employee)s IS NULL OR att.employee = %(employee)s)
ORDER BY att.employee, att.attendance_date, att.in_time;
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
            ],
            "columns": [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Attendance Date", "fieldname": "attendance_date", "fieldtype": "Date", "width": 120},
        {"label": "Day", "fieldname": "attendance_day", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Data", "width": 100},
        {"label": "In Time", "fieldname": "in_time", "fieldtype": "Datetime", "width": 150},
        {"label": "Out Time", "fieldname": "out_time", "fieldtype": "Datetime", "width": 150},
        {"label": "Working Hours", "fieldname": "working_hours", "fieldtype": "Float", "width": 130},
        {"label": "Late Entry", "fieldname": "late_entry", "fieldtype": "Check", "width": 100}
    ],
        })
        report.insert(ignore_permissions=True)
        frappe.db.commit()
