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
-- Generate date range recursively between from_date and to_date
WITH RECURSIVE DateRange AS (
    SELECT %(from_date)s AS attendance_date
    UNION ALL
    SELECT DATE_ADD(attendance_date, INTERVAL 1 DAY)
    FROM DateRange
    WHERE attendance_date < %(to_date)s
),

-- Fetch check-in records within date range and optionally for a specific employee
-- Assign row numbers to each IN/OUT log per day to help with pairing
CheckinRecords AS (
    SELECT 
        ci.employee,
        DATE(ci.time) AS attendance_date,
        ci.time AS checkin_time,
        ci.log_type,
        ci.shift,
        ci.shift_start,
        ROW_NUMBER() OVER (PARTITION BY ci.employee, DATE(ci.time), ci.log_type ORDER BY ci.time) AS rn
    FROM `tabEmployee Checkin` ci
    WHERE DATE(ci.time) BETWEEN %(from_date)s AND %(to_date)s
      AND (%(employee)s IS NULL OR ci.employee = %(employee)s)
),

-- Pair IN records with the nearest OUT record, ensuring OUT is after IN
-- Consider overnight OUT logs (between 6AM and 10AM next day)
-- Avoid pairing if there's another IN between the IN and OUT
PairedINOUT AS (
    SELECT 
        i.employee,
        i.attendance_date,
        i.checkin_time AS in_time,
        i.shift,
        i.shift_start,
        MIN(o.checkin_time) AS out_time
    FROM CheckinRecords i
    LEFT JOIN CheckinRecords o
        ON o.employee = i.employee
        AND o.log_type = 'OUT'
        AND o.checkin_time > i.checkin_time
        AND (
            DATE(o.checkin_time) = i.attendance_date
            OR (
                DATE(o.checkin_time) = DATE_ADD(i.attendance_date, INTERVAL 1 DAY)
                AND TIME(o.checkin_time) BETWEEN '06:00:00' AND '10:00:00'
            )
        )
        AND NOT EXISTS (
            -- Make sure there's no intermediate IN record between i and o
            SELECT 1
            FROM CheckinRecords i2
            WHERE i2.employee = i.employee
              AND i2.log_type = 'IN'
              AND i2.checkin_time > i.checkin_time
              AND i2.checkin_time < o.checkin_time
        )
    WHERE i.log_type = 'IN'
    GROUP BY i.employee, i.checkin_time, i.attendance_date, i.shift, i.shift_start
),

-- Identify OUT records that were not paired with any IN
UnpairedOUT AS (
    SELECT 
        o.employee,
        o.attendance_date,
        NULL AS in_time,
        NULL AS shift,
        NULL AS shift_start,
        o.checkin_time AS out_time
    FROM CheckinRecords o
    WHERE o.log_type = 'OUT'
      AND NOT EXISTS (
          SELECT 1
          FROM PairedINOUT p
          WHERE p.employee = o.employee
            AND p.out_time = o.checkin_time
      )
),

-- Combine both valid IN/OUT pairs and unmatched OUTs into a single list
CheckinPairs AS (
    SELECT employee, attendance_date, in_time, shift, shift_start, out_time
    FROM PairedINOUT
    UNION ALL
    SELECT employee, attendance_date, in_time, shift, shift_start, out_time
    FROM UnpairedOUT
),

-- Prepare Present records based on CheckinPairs, calculate working hours, and flag late entries
PresentRecords AS (
    SELECT
        cp.employee,
        emp.employee_name,
        cp.attendance_date,
        DAYNAME(cp.attendance_date) AS attendance_day,
        'Present' AS status,
        cp.shift,
        cp.in_time,
        cp.out_time,
        ROUND(
            CASE
                WHEN cp.in_time IS NOT NULL AND cp.out_time IS NOT NULL
                THEN TIMESTAMPDIFF(SECOND, cp.in_time, cp.out_time) / 3600
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

-- Identify Absent records: employees with no check-in records on that date
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
        0 AS working_hours,
        0 AS late_entry,
        0 AS is_total
    FROM DateRange dr
    CROSS JOIN `tabEmployee` emp
    LEFT JOIN CheckinRecords ci
        ON emp.employee = ci.employee
        AND ci.attendance_date = dr.attendance_date
    WHERE (%(employee)s IS NULL OR emp.employee = %(employee)s)
      AND ci.employee IS NULL
    GROUP BY emp.employee, dr.attendance_date
),

-- Combine all Present and Absent records into final set
AllRecords AS (
    SELECT * FROM PresentRecords
    UNION
    SELECT * FROM AbsentRecords
),

-- Compute grand total working hours for selected employee
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

-- Final result: all attendance records plus the total row
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