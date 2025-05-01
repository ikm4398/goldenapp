
import frappe
from frappe.utils import add_days, nowdate

def create_attendance_query_report():
    if not frappe.db.exists("Report", "Golden Attendance Report"):
        today = nowdate()
        from_date = add_days(today, -30)
        to_date = today

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
            WHEN att.in_time IS NOT NULL AND att.shift = 'Evening' THEN (
                SELECT ao.out_time
                FROM `tabAttendance` ao
                WHERE ao.employee = att.employee
                  AND ao.attendance_date = att.attendance_date
                  AND ao.out_time IS NOT NULL
                  AND TIME(ao.out_time) BETWEEN '14:00:00' AND '21:00:00'
                  LIMIT 1
            )
            WHEN att.in_time IS NOT NULL AND att.shift = 'Morning' THEN (
                SELECT ao.out_time
                FROM `tabAttendance` ao
                WHERE ao.employee = att.employee
                  AND ao.attendance_date = att.attendance_date
                  AND ao.out_time IS NOT NULL
                  AND TIME(ao.out_time) BETWEEN '08:00:00' AND '15:00:00'
                  LIMIT 1
            )
            WHEN att.in_time IS NOT NULL AND att.shift = 'Night' THEN next_att.out_time
            ELSE NULL
        END
    ) AS out_time,
    ROUND(
        CASE
            WHEN att.in_time IS NOT NULL AND att.out_time IS NOT NULL THEN TIMESTAMPDIFF(SECOND, att.in_time, att.out_time)/3600
            WHEN att.in_time IS NOT NULL AND att.out_time IS NULL THEN
                TIMESTAMPDIFF(
                    SECOND,
                    att.in_time,
                    COALESCE(
                        CASE
                            WHEN att.shift = 'Evening' THEN (
                                SELECT ao.out_time
                                FROM `tabAttendance` ao
                                WHERE ao.employee = att.employee
                                  AND ao.attendance_date = att.attendance_date
                                  AND ao.out_time IS NOT NULL
                                  AND TIME(ao.out_time) BETWEEN '14:00:00' AND '21:00:00'
                                  LIMIT 1
                            )
                            WHEN att.shift = 'Morning' THEN (
                                SELECT ao.out_time
                                FROM `tabAttendance` ao
                                WHERE ao.employee = att.employee
                                  AND ao.attendance_date = att.attendance_date
                                  AND ao.out_time IS NOT NULL
                                  AND TIME(ao.out_time) BETWEEN '08:00:00' AND '15:00:00'
                                  LIMIT 1
                            )
                            WHEN att.shift = 'Night' THEN next_att.out_time
                            ELSE NULL
                        END,
                        next_att.out_time
                    )
                ) / 3600
            ELSE 0
        END, 3
    ) AS working_hours,
    att.late_entry
FROM
    `tabAttendance` att
LEFT JOIN `tabAttendance` next_att
    ON att.employee = next_att.employee
    AND next_att.attendance_date = DATE_ADD(att.attendance_date, INTERVAL 1 DAY)
    AND next_att.in_time IS NULL
    AND next_att.out_time IS NOT NULL
    AND TIME(next_att.out_time) BETWEEN '08:00:00' AND '10:00:00'
LEFT JOIN `tabEmployee` emp
    ON att.employee = emp.employee
WHERE
    att.docstatus = 1
    AND att.attendance_date BETWEEN %(from_date)s AND %(to_date)s
    AND (%(employee)s IS NULL OR att.employee = %(employee)s)
ORDER BY att.employee, att.attendance_date;
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
