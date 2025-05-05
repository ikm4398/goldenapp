
import frappe
from frappe.utils import add_days, nowdate

def create_daily_attendance_report():
    if not frappe.db.exists("Report", "All Employee Attendance Summary Report"):
        today = nowdate()
        from_date = add_days(today, -7)
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
WITH date_range AS (
    SELECT ADDDATE(%(from_date)s, INTERVAL t4.num * 1000 + t3.num * 100 + t2.num * 10 + t1.num DAY) AS attendance_date
    FROM (SELECT 0 AS num UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
          UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t1,
         (SELECT 0 AS num UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
          UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t2,
         (SELECT 0 AS num UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
          UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t3,
         (SELECT 0 AS num UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
          UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t4
    WHERE ADDDATE(%(from_date)s, INTERVAL t4.num * 1000 + t3.num * 100 + t2.num * 10 + t1.num DAY) <= %(to_date)s
),
emp_list AS (
    SELECT employee, employee_name FROM `tabEmployee`
    WHERE status = 'Active' AND (%(employee)s IS NULL OR employee = %(employee)s)
),
present_logs AS (
    SELECT
        att.employee,
        att.attendance_date,
        att.in_time,
        att.out_time,
        att.shift,
        'Present' AS status
    FROM `tabAttendance` att
    WHERE att.docstatus = 1
      AND att.in_time IS NOT NULL
      AND att.attendance_date BETWEEN %(from_date)s AND %(to_date)s
),
combined_logs AS (
    SELECT
        e.employee,
        e.employee_name,
        d.attendance_date,
        p.status,
        p.in_time,
        COALESCE(
            p.out_time,
            CASE
                WHEN p.in_time IS NOT NULL AND TIME(p.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                    SELECT ao.out_time
                    FROM `tabAttendance` ao
                    WHERE ao.employee = p.employee
                      AND ao.attendance_date = p.attendance_date
                      AND ao.out_time IS NOT NULL
                      AND TIME(ao.out_time) BETWEEN '09:00:00' AND '15:00:00'
                    LIMIT 1
                )
                WHEN p.in_time IS NOT NULL AND TIME(p.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                    SELECT ao.out_time
                    FROM `tabAttendance` ao
                    WHERE ao.employee = p.employee
                      AND ao.attendance_date = p.attendance_date
                      AND ao.out_time IS NOT NULL
                      AND TIME(ao.out_time) BETWEEN '15:00:00' AND '21:00:00'
                    LIMIT 1
                )
                WHEN p.in_time IS NOT NULL AND TIME(p.in_time) >= '18:00:00' THEN (
                    SELECT next_att.out_time
                    FROM `tabAttendance` next_att
                    WHERE next_att.employee = p.employee
                      AND next_att.attendance_date = DATE_ADD(p.attendance_date, INTERVAL 1 DAY)
                      AND next_att.out_time IS NOT NULL
                      AND TIME(next_att.out_time) BETWEEN '06:00:00' AND '10:00:00'
                    LIMIT 1
                )
                ELSE NULL
            END
        ) AS out_time,
        p.shift
    FROM emp_list e
    CROSS JOIN date_range d
    LEFT JOIN present_logs p
        ON e.employee = p.employee AND d.attendance_date = p.attendance_date
)
-- 1. Detailed Attendance Records (Hiding these rows)
SELECT
    employee,
    employee_name,
    attendance_date,
    COALESCE(status, 'Absent') AS status,
    in_time,
    out_time,
    shift
FROM combined_logs
WHERE attendance_date IS NOT NULL

-- 2. Summary Marker (Making it bold using HTML)
UNION ALL
SELECT
    employee,
    employee_name,
    NULL,
    CONCAT('<b>--- Summary ---</b>'),
    NULL,
    NULL,
    NULL
FROM combined_logs
GROUP BY employee, employee_name

-- 3. Shift-wise Total Present (Making it bold using HTML)
UNION ALL
SELECT
    employee,
    employee_name,
    NULL,
    CONCAT('<b>Shift: ', shift, ' -> ', COUNT(*), '</b>'),
    NULL,
    NULL,
    shift
FROM combined_logs
WHERE status = 'Present'
GROUP BY employee, employee_name, shift

-- 4. Total Present (Making it bold using HTML)
UNION ALL
SELECT
    employee,
    employee_name,
    NULL,
    CONCAT('<b>Total Present: ', COUNT(*), '</b>'),
    NULL,
    NULL,
    NULL
FROM combined_logs
WHERE status = 'Present'
GROUP BY employee, employee_name

-- 5. Total Absent (Making it bold using HTML)
UNION ALL
SELECT
    employee,
    employee_name,
    NULL,
    CONCAT('<b>Total Absent: ', COUNT(*), '</b>'),
    NULL,
    NULL,
    NULL
FROM combined_logs
WHERE status IS NULL
GROUP BY employee, employee_name

-- Final sort: summary last
ORDER BY employee, attendance_date IS NULL, attendance_date, status, shift;
            """,
            "filters": [
                {
                    "fieldname": "employee",
                    "label": "Employee",
                    "fieldtype": "Link",
                    "options": "Employee",
                    "default": "HR-EMP-00001",
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
            ],
            "columns": [
    {
        "label": "Employee",
        "fieldname": "employee",
        "fieldtype": "Link",
        "options": "Employee",
        "width": 120
    },
    {
        "label": "Employee Name",
        "fieldname": "employee_name",
        "fieldtype": "Data",
        "width": 150
    },
    {
        "label": "Date",
        "fieldname": "attendance_date",
        "fieldtype": "Date",
        "width": 100
    },
    {
        "label": "Status",
        "fieldname": "status",
        "fieldtype": "Data",
        "width": 100
    },
    {
        "label": "In Time",
        "fieldname": "in_time",
        "fieldtype": "Datetime",
        "width": 150
    },
    {
        "label": "Out Time",
        "fieldname": "out_time",
        "fieldtype": "Datetime",
        "width": 150
    },
    {
        "label": "Shift",
        "fieldname": "shift",
        "fieldtype": "Data",
        "width": 100
    }
]

        })
        report.insert(ignore_permissions=True)
        frappe.db.commit()
