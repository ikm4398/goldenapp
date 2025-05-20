import frappe
from frappe.utils import add_days, nowdate

def create_employee_checkin_query_report():
    if not frappe.db.exists("Report", "New Employee Checkin Report"):
        report = frappe.get_doc({
            "doctype": "Report",
            "report_name": "New Employee Checkin Report",
            "ref_doctype": "Attendance",
            "report_type": "Query Report",
            "is_standard": "No",
            "module": "Goldenapp",
            "add_total_row": 1,
            "query": """
WITH RECURSIVE DateRange AS (
    SELECT %(from_date)s AS attendance_date
    UNION ALL
    SELECT DATE_ADD(attendance_date, INTERVAL 1 DAY)
    FROM DateRange
    WHERE attendance_date < %(to_date)s
),
CheckinPairs AS (
    SELECT 
        ci.employee,
        DATE(ci.time) AS attendance_date,
        ci.time AS in_time,
        ci.shift,
        (
            SELECT MIN(co.time)
            FROM `tabEmployee Checkin` co
            WHERE co.employee = ci.employee
              AND co.log_type = 'OUT'
              AND co.time > ci.time
              AND DATE(co.time) = DATE(ci.time)
        ) AS out_time_same_day,
        (
            SELECT MIN(co.time)
            FROM `tabEmployee Checkin` co
            WHERE co.employee = ci.employee
              AND co.log_type = 'OUT'
              AND DATE(co.time) = DATE_ADD(DATE(ci.time), INTERVAL 1 DAY)
              AND TIME(co.time) BETWEEN '06:00:00' AND '10:00:00'
              AND co.time > ci.time
        ) AS out_time_next_day
    FROM `tabEmployee Checkin` ci
    WHERE ci.log_type = 'IN'
      AND DATE(ci.time) BETWEEN %(from_date)s AND %(to_date)s
      AND (%(employee)s IS NULL OR ci.employee = %(employee)s)
),
PresentRecords AS (
    SELECT
        cp.employee,
        emp.employee_name,
        cp.attendance_date,
        DAYNAME(cp.attendance_date) AS attendance_day,
        'Present' AS status,
        cp.shift,
        cp.in_time,
        COALESCE(
            CASE
                WHEN cp.out_time_same_day IS NOT NULL THEN cp.out_time_same_day
                WHEN cp.in_time IS NOT NULL 
                AND TIME(cp.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                    SELECT co.time
                    FROM `tabEmployee Checkin` co
                    WHERE co.employee = cp.employee
                      AND DATE(co.time) = cp.attendance_date
                      AND co.log_type = 'OUT'
                      AND co.time > cp.in_time
                      AND TIME(co.time) BETWEEN '09:00:00' AND '15:00:00'
                    LIMIT 1
                )
                WHEN cp.in_time IS NOT NULL 
                AND TIME(cp.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                    SELECT co.time
                    FROM `tabEmployee Checkin` co
                    WHERE co.employee = cp.employee
                      AND DATE(co.time) = cp.attendance_date
                      AND co.log_type = 'OUT'
                      AND co.time > cp.in_time
                      AND TIME(co.time) BETWEEN '15:00:00' AND '21:00:00'
                    LIMIT 1
                )
                WHEN cp.in_time IS NOT NULL 
                AND TIME(cp.in_time) >= '18:00:00' 
                AND cp.out_time_next_day IS NOT NULL THEN cp.out_time_next_day
                ELSE NULL
            END,
            NULL
        ) AS out_time,
        ROUND(
            CASE
                WHEN cp.in_time IS NOT NULL AND COALESCE(
                    CASE
                        WHEN cp.out_time_same_day IS NOT NULL THEN cp.out_time_same_day
                        WHEN TIME(cp.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                            SELECT co.time
                            FROM `tabEmployee Checkin` co
                            WHERE co.employee = cp.employee
                              AND DATE(co.time) = cp.attendance_date
                              AND co.log_type = 'OUT'
                              AND co.time > cp.in_time
                              AND TIME(co.time) BETWEEN '09:00:00' AND '15:00:00'
                            LIMIT 1
                        )
                        WHEN TIME(cp.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                            SELECT co.time
                            FROM `tabEmployee Checkin` co
                            WHERE co.employee = cp.employee
                              AND DATE(co.time) = cp.attendance_date
                              AND co.log_type = 'OUT'
                              AND co.time > cp.in_time
                              AND TIME(co.time) BETWEEN '15:00:00' AND '21:00:00'
                            LIMIT 1
                        )
                        WHEN TIME(cp.in_time) >= '18:00:00' 
                        AND cp.out_time_next_day IS NOT NULL THEN cp.out_time_next_day
                        ELSE NULL
                    END,
                    NULL
                ) IS NOT NULL THEN
                    TIMESTAMPDIFF(
                        SECOND,
                        cp.in_time,
                        COALESCE(
                            CASE
                                WHEN cp.out_time_same_day IS NOT NULL THEN cp.out_time_same_day
                                WHEN TIME(cp.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                                    SELECT co.time
                                    FROM `tabEmployee Checkin` co
                                    WHERE co.employee = cp.employee
                                      AND DATE(co.time) = cp.attendance_date
                                      AND co.log_type = 'OUT'
                                      AND co.time > cp.in_time
                                      AND TIME(co.time) BETWEEN '09:00:00' AND '15:00:00'
                                    LIMIT 1
                                )
                                WHEN TIME(cp.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                                    SELECT co.time
                                    FROM `tabEmployee Checkin` co
                                    WHERE co.employee = cp.employee
                                      AND DATE(co.time) = cp.attendance_date
                                      AND co.log_type = 'OUT'
                                      AND co.time > cp.in_time
                                      AND TIME(co.time) BETWEEN '15:00:00' AND '21:00:00'
                                    LIMIT 1
                                )
                                WHEN TIME(cp.in_time) >= '18:00:00' 
                                AND cp.out_time_next_day IS NOT NULL THEN cp.out_time_next_day
                                ELSE NULL
                            END,
                            NULL
                        )
                    ) / 3600
                ELSE 0
            END, 3
        ) AS working_hours
    FROM CheckinPairs cp
    LEFT JOIN `tabEmployee` emp ON cp.employee = emp.employee
    WHERE cp.in_time IS NOT NULL
),
AbsentRecords AS (
    SELECT
        emp.employee,
        emp.employee_name,
        dr.attendance_date,
        DAYNAME(dr.attendance_date) AS attendance_day,
        'Absent' AS status,
        NULL AS shift,
        NULL AS in_time,
        NULL AS out_time,
        0 AS working_hours
    FROM DateRange dr
    CROSS JOIN `tabEmployee` emp
    LEFT JOIN `tabEmployee Checkin` ci
        ON emp.employee = ci.employee
        AND DATE(ci.time) = dr.attendance_date
    WHERE (%(employee)s IS NULL OR emp.employee = %(employee)s)
      AND ci.employee IS NULL
    GROUP BY emp.employee, dr.attendance_date
)
SELECT * FROM PresentRecords
UNION
SELECT * FROM AbsentRecords
ORDER BY employee, attendance_date, in_time;
            """,
            "filters": [
                {
                    "fieldname": "employee",
                    "label": "Employee",
                    "fieldtype": "Link",
                    "options": "Employee",
                    "reqd": 1
                },
                {
                    "fieldname": "from_date",
                    "label": "From Date",
                    "fieldtype": "Date",
                    "reqd": 1
                },
                {
                    "fieldname": "to_date",
                    "label": "To Date",
                    "fieldtype": "Date",
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
            ],
            "javascript": """
frappe.query_reports["New Employee Checkin Report"] = {
    "filters": [
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1
        }
    ],
    "onload": function(report) {
        report.page.add_inner_button(__("Refresh"), function() {
            let filters = report.get_values();
            if (!filters.employee || !filters.from_date || !filters.to_date) {
                frappe.msgprint(__("Please fill all mandatory fields: Employee, From Date, and To Date"));
                return;
            }
            report.refresh();
        });
        
        // Override the default run button behavior
        report.page.set_primary_action(__("Run"), function() {
            let filters = report.get_values();
            if (!filters.employee || !filters.from_date || !filters.to_date) {
                frappe.msgprint(__("Please fill all mandatory fields: Employee, From Date, and To Date"));
                return;
            }
            report.refresh();
        });
    }
}
            """
        })
        report.insert(ignore_permissions=True)
        frappe.db.commit()