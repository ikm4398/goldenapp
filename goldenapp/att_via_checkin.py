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
            "add_total_row": 0,  # Disable automatic total row
            "query": """
            WITH RECURSIVE DateRange AS (
    SELECT %(from_date)s AS attendance_date
    UNION ALL
    SELECT DATE_ADD(attendance_date, INTERVAL 1 DAY)
    FROM DateRange
    WHERE attendance_date < %(to_date)s
),
CheckinRecords AS (
    SELECT 
        ci.employee,
        DATE(ci.time) AS attendance_date,
        ci.time AS checkin_time,
        ci.log_type,
        ci.shift,
        ci.shift_start
    FROM `tabEmployee Checkin` ci
    WHERE DATE(ci.time) BETWEEN %(from_date)s AND %(to_date)s
      AND (%(employee)s IS NULL OR ci.employee = %(employee)s)
),
CheckinPairs AS (
    SELECT 
        employee,
        attendance_date,
        checkin_time AS in_time,
        log_type,
        shift,
        shift_start,
        CASE 
            WHEN log_type = 'IN' THEN (
                SELECT MIN(co.checkin_time)
                FROM CheckinRecords co
                WHERE co.employee = ci.employee
                  AND co.log_type = 'OUT'
                  AND co.checkin_time > ci.checkin_time
                  AND (
                      (DATE(co.checkin_time) = ci.attendance_date)
                      OR (
                          DATE(co.checkin_time) = DATE_ADD(ci.attendance_date, INTERVAL 1 DAY)
                          AND TIME(co.checkin_time) BETWEEN '06:00:00' AND '10:00:00'
                      )
                  )
            )
            ELSE NULL
        END AS out_time
    FROM CheckinRecords ci
    WHERE log_type = 'IN'
    UNION ALL
    SELECT 
        employee,
        attendance_date,
        NULL AS in_time,
        log_type,
        NULL AS shift,
        NULL AS shift_start,
        checkin_time AS out_time
    FROM CheckinRecords ci
    WHERE log_type = 'OUT'
      AND NOT EXISTS (
          SELECT 1
          FROM CheckinRecords co
          WHERE co.employee = ci.employee
            AND co.log_type = 'IN'
            AND (
                (DATE(co.checkin_time) = ci.attendance_date
                 AND co.checkin_time < ci.checkin_time)
                OR (
                    DATE(co.checkin_time) = DATE_SUB(ci.attendance_date, INTERVAL 1 DAY)
                    AND TIME(ci.checkin_time) BETWEEN '06:00:00' AND '10:00:00'
                    AND TIME(co.checkin_time) >= '18:00:00'
                )
            )
      )
),
PresentRecords AS (
    SELECT
        cp.employee,
        emp.employee_name,
        cp.attendance_date,
        DAYNAME(cp.attendance_date) AS attendance_day,
        CASE 
            WHEN cp.in_time IS NULL AND cp.out_time IS NOT NULL THEN 'Present'
            ELSE 'Present'
        END AS status,
        cp.shift,
        cp.in_time,
        COALESCE(
            CASE
                WHEN cp.out_time IS NOT NULL THEN cp.out_time
                WHEN cp.in_time IS NOT NULL 
                AND TIME(cp.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                    SELECT co.checkin_time
                    FROM CheckinRecords co
                    WHERE co.employee = cp.employee
                      AND DATE(co.checkin_time) = cp.attendance_date
                      AND co.log_type = 'OUT'
                      AND co.checkin_time > cp.in_time
                      AND TIME(co.checkin_time) BETWEEN '09:00:00' AND '15:00:00'
                    LIMIT 1
                )
                WHEN cp.in_time IS NOT NULL 
                AND TIME(cp.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                    SELECT co.checkin_time
                    FROM CheckinRecords co
                    WHERE co.employee = cp.employee
                      AND DATE(co.checkin_time) = cp.attendance_date
                      AND co.log_type = 'OUT'
                      AND co.checkin_time > cp.in_time
                      AND TIME(co.checkin_time) BETWEEN '15:00:00' AND '21:00:00'
                    LIMIT 1
                )
                WHEN cp.in_time IS NOT NULL 
                AND TIME(cp.in_time) >= '18:00:00' THEN (
                    SELECT co.checkin_time
                    FROM CheckinRecords co
                    WHERE co.employee = cp.employee
                      AND DATE(co.checkin_time) = DATE_ADD(cp.attendance_date, INTERVAL 1 DAY)
                      AND co.log_type = 'OUT'
                      AND TIME(co.checkin_time) BETWEEN '06:00:00' AND '10:00:00'
                    LIMIT 1
                )
                ELSE cp.out_time
            END,
            NULL
        ) AS out_time,
        ROUND(
            CASE
                WHEN cp.in_time IS NOT NULL AND COALESCE(
                    CASE
                        WHEN cp.out_time IS NOT NULL THEN cp.out_time
                        WHEN TIME(cp.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                            SELECT co.checkin_time
                            FROM CheckinRecords co
                            WHERE co.employee = cp.employee
                              AND DATE(co.checkin_time) = cp.attendance_date
                              AND co.log_type = 'OUT'
                              AND co.checkin_time > cp.in_time
                              AND TIME(co.checkin_time) BETWEEN '09:00:00' AND '15:00:00'
                            LIMIT 1
                        )
                        WHEN TIME(cp.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                            SELECT co.checkin_time
                            FROM CheckinRecords co
                            WHERE co.employee = cp.employee
                              AND DATE(co.checkin_time) = cp.attendance_date
                              AND co.log_type = 'OUT'
                              AND co.checkin_time > cp.in_time
                              AND TIME(co.checkin_time) BETWEEN '15:00:00' AND '21:00:00'
                            LIMIT 1
                        )
                        WHEN TIME(cp.in_time) >= '18:00:00' THEN (
                            SELECT co.checkin_time
                            FROM CheckinRecords co
                            WHERE co.employee = cp.employee
                              AND DATE(co.checkin_time) = DATE_ADD(cp.attendance_date, INTERVAL 1 DAY)
                              AND co.log_type = 'OUT'
                              AND TIME(co.checkin_time) BETWEEN '06:00:00' AND '10:00:00'
                            LIMIT 1
                        )
                        ELSE cp.out_time
                    END,
                    NULL
                ) IS NOT NULL THEN
                    TIMESTAMPDIFF(
                        SECOND,
                        cp.in_time,
                        COALESCE(
                            CASE
                                WHEN cp.out_time IS NOT NULL THEN cp.out_time
                                WHEN TIME(cp.in_time) BETWEEN '05:00:00' AND '10:00:00' THEN (
                                    SELECT co.checkin_time
                                    FROM CheckinRecords co
                                    WHERE co.employee = cp.employee
                                      AND DATE(co.checkin_time) = cp.attendance_date
                                      AND co.log_type = 'OUT'
                                      AND co.checkin_time > cp.in_time
                                      AND TIME(co.checkin_time) BETWEEN '09:00:00' AND '15:00:00'
                                    LIMIT 1
                                )
                                WHEN TIME(cp.in_time) BETWEEN '12:00:00' AND '17:00:00' THEN (
                                    SELECT co.checkin_time
                                    FROM CheckinRecords co
                                    WHERE co.employee = cp.employee
                                      AND DATE(co.checkin_time) = cp.attendance_date
                                      AND co.log_type = 'OUT'
                                      AND co.checkin_time > cp.in_time
                                      AND TIME(co.checkin_time) BETWEEN '15:00:00' AND '21:00:00'
                                    LIMIT 1
                                )
                                WHEN TIME(cp.in_time) >= '18:00:00' THEN (
                                    SELECT co.checkin_time
                                    FROM CheckinRecords co
                                    WHERE co.employee = cp.employee
                                      AND DATE(co.checkin_time) = DATE_ADD(cp.attendance_date, INTERVAL 1 DAY)
                                      AND co.log_type = 'OUT'
                                      AND TIME(co.checkin_time) BETWEEN '06:00:00' AND '10:00:00'
                                    LIMIT 1
                                )
                                ELSE cp.out_time
                            END,
                            NULL
                        )
                    ) / 3600
                ELSE 0
            END, 3
        ) AS working_hours,
        CASE 
            WHEN cp.shift_start IS NOT NULL 
            THEN CASE 
                    WHEN TIMESTAMPDIFF(MINUTE, cp.shift_start, cp.in_time) > 15 THEN 1 
                    ELSE 0 
                 END
            ELSE CASE 
                    WHEN cp.in_time > CONCAT(cp.attendance_date, ' ', '09:00:00') THEN 1 
                    ELSE 0 
                 END
        END AS late_entry,
        0 AS is_total
    FROM CheckinPairs cp
    LEFT JOIN `tabEmployee` emp ON cp.employee = emp.employee
    WHERE cp.in_time IS NOT NULL OR cp.out_time IS NOT NULL
),
AbsentRecords AS (
    SELECT
        emp.employee,
        emp.employee_name,
        dr.attendance_date,
        DAYNAME(dr.attendance_date) AS attendance_day,
        CASE 
            WHEN EXISTS (
                SELECT 1
                FROM CheckinRecords co
                WHERE co.employee = emp.employee
                  AND DATE(co.checkin_time) = dr.attendance_date
                  AND co.log_type = 'OUT'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM CheckinRecords ci
                      WHERE ci.employee = emp.employee
                        AND DATE(ci.checkin_time) = dr.attendance_date
                        AND ci.log_type = 'IN'
                  )
                  AND EXISTS (
                      SELECT 1
                      FROM CheckinRecords ci
                      WHERE ci.employee = emp.employee
                        AND DATE(ci.checkin_time) = DATE_SUB(dr.attendance_date, INTERVAL 1 DAY)
                        AND ci.log_type = 'IN'
                  )
            ) THEN 'Absent'
            ELSE 'Absent'
        END AS status,
        NULL AS shift,
        NULL AS in_time,
        NULL AS out_time,
        0 AS working_hours,
        0 AS late_entry,
        0 AS is_total
    FROM DateRange dr
    CROSS JOIN `tabEmployee` emp
    LEFT JOIN CheckinRecords ci
        ON emp.employee = ci.employee
        AND DATE(ci.checkin_time) = dr.attendance_date
    WHERE (%(employee)s IS NULL OR emp.employee = %(employee)s)
      AND ci.employee IS NULL
    GROUP BY emp.employee, dr.attendance_date
),
AllRecords AS (
    SELECT * FROM PresentRecords
    UNION
    SELECT * FROM AbsentRecords
),
GrandTotal AS (
    SELECT 
        'Total' AS employee,
        NULL AS employee_name,
        NULL AS attendance_date,
        NULL AS attendance_day,
        NULL AS status,
        NULL AS shift,
        NULL AS in_time,
        NULL AS out_time,
        SUM(working_hours) AS working_hours,
        NULL AS late_entry,
        1 AS is_total
    FROM AllRecords
    WHERE employee = %(employee)s
)
SELECT * FROM AllRecords
UNION
SELECT * FROM GrandTotal
ORDER BY is_total, attendance_date, employee;
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
                {"label": "Late Entry", "fieldname": "late_entry", "fieldtype": "Check", "width": 130},
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
    },
    "formatter": function(value, row, column, data, default_formatter) {
        if (data && data.is_total === 1) {
            return `<b>${default_formatter(value, row, column, data)}</b>`;
        }
        return default_formatter(value, row, column, data);
    }
}
            """
        })
        report.insert(ignore_permissions=True)
        frappe.db.commit()
