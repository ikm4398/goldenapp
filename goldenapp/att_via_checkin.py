import frappe
from frappe.utils import add_days, nowdate

def create_employee_checkin_query_report():
    if not frappe.db.exists("Report", "New Employee Attendance Report"):
        report = frappe.get_doc({
            "doctype": "Report",
            "report_name": "New Employee Attendance Report",
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

            -- Fetch all check-in/out records within date range for each employee, including shift info
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

            -- Get all valid and active shift assignments for employees
            ShiftAssignments AS (
                SELECT 
                    sa.employee,
                    sa.shift_type,
                    sa.start_time,
                    sa.end_time,
                    sa.start_date
                FROM `tabShift Assignment` sa
                WHERE sa.status = 'Active'
                AND sa.docstatus = 1
                AND sa.start_date <= %(to_date)s
                AND (%(employee)s IS NULL OR sa.employee = %(employee)s)
            ),

            -- Match each IN check-in with the closest shift based on time difference
            MatchedShifts AS (
                SELECT 
                    ci.employee,
                    ci.checkin_time,
                    ci.attendance_date,
                    MIN(ABS(TIMESTAMPDIFF(MINUTE, 
                        CASE 
                            WHEN sa.end_time >= sa.start_time 
                            THEN CONCAT(ci.attendance_date, ' ', sa.start_time)
                            ELSE CONCAT(DATE_ADD(ci.attendance_date, INTERVAL 1 DAY), ' ', sa.end_time)
                        END,
                        ci.checkin_time
                    ))) AS min_time_diff,
                    MIN(sa.shift_type) AS shift_type,
                    MIN(
                        CASE 
                            WHEN sa.end_time >= sa.start_time 
                            THEN CONCAT(ci.attendance_date, ' ', sa.start_time)
                            ELSE CONCAT(ci.attendance_date, ' ', sa.start_time)
                        END
                    ) AS shift_start,
                    MIN(
                        CASE 
                            WHEN sa.end_time >= sa.start_time 
                            THEN CONCAT(ci.attendance_date, ' ', sa.end_time)
                            ELSE CONCAT(DATE_ADD(ci.attendance_date, INTERVAL 1 DAY), ' ', sa.end_time)
                        END
                    ) AS shift_end
                FROM CheckinRecords ci
                LEFT JOIN ShiftAssignments sa
                    ON sa.employee = ci.employee
                    AND sa.start_date <= ci.attendance_date
                    AND (
                        ci.checkin_time >= DATE_SUB(
                            CASE 
                                WHEN sa.end_time >= sa.start_time 
                                THEN CONCAT(ci.attendance_date, ' ', sa.start_time)
                                ELSE CONCAT(ci.attendance_date, ' ', sa.start_time)
                            END, 
                            INTERVAL 120 MINUTE
                        )
                        AND ci.checkin_time <= 
                            CASE 
                                WHEN sa.end_time >= sa.start_time 
                                THEN CONCAT(ci.attendance_date, ' ', sa.end_time)
                                ELSE CONCAT(DATE_ADD(ci.attendance_date, INTERVAL 1 DAY), ' ', sa.end_time)
                            END
                    )
                WHERE ci.log_type = 'IN'
                GROUP BY ci.employee, ci.checkin_time, ci.attendance_date
            ),

            -- Pair each IN check-in with the next valid OUT check-in (no other IN between), within 2 days
            PairedINOUT AS (
                SELECT 
                    ci.employee,
                    ci.attendance_date,
                    ci.checkin_time AS in_time,
                    ms.shift_type,
                    ms.shift_start,
                    ms.shift_end,
                    MIN(o.checkin_time) AS out_time
                FROM CheckinRecords ci
                LEFT JOIN CheckinRecords o
                    ON o.employee = ci.employee
                    AND o.log_type = 'OUT'
                    AND o.checkin_time > ci.checkin_time
                    AND o.checkin_time <= DATE_ADD(ci.checkin_time, INTERVAL 2 DAY) -- Limit OUT to within 2 days
                    AND (
                        DATE(o.checkin_time) = ci.attendance_date
                        OR (
                            DATE(o.checkin_time) = DATE_ADD(ci.attendance_date, INTERVAL 1 DAY)
                            AND TIME(o.checkin_time) BETWEEN '06:00:00' AND '10:00:00'
                        )
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM CheckinRecords i2
                        WHERE i2.employee = ci.employee
                        AND i2.log_type = 'IN'
                        AND i2.checkin_time > ci.checkin_time
                        AND i2.checkin_time < o.checkin_time
                    )
                LEFT JOIN MatchedShifts ms
                    ON ms.employee = ci.employee
                    AND ms.checkin_time = ci.checkin_time
                WHERE ci.log_type = 'IN'
                GROUP BY ci.employee, ci.checkin_time, ci.attendance_date, ms.shift_type, ms.shift_start, ms.shift_end
            ),

            -- Find all OUT entries that couldn’t be paired with any IN
            UnpairedOUT AS (
                SELECT 
                    o.employee,
                    o.attendance_date,
                    NULL AS in_time,
                    NULL AS shift_type,
                    NULL AS shift_start,
                    NULL AS shift_end,
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

            -- Combine Paired IN/OUT and unpaired OUTs
            CheckinPairs AS (
                SELECT employee, attendance_date, in_time, shift_type, shift_start, shift_end, out_time
                FROM PairedINOUT
                UNION ALL
                SELECT employee, attendance_date, in_time, shift_type, shift_start, shift_end, out_time
                FROM UnpairedOUT
            ),

            -- Generate present records when in_time is available (out_time may be null)
            PresentRecords AS (
                SELECT
                    cp.employee,
                    emp.employee_name,
                    cp.attendance_date,
                    DAYNAME(cp.attendance_date) AS attendance_day,
                    'Present' AS status,
                    cp.shift_type,
                    cp.in_time,
                    cp.out_time,
                    ROUND(
                        CASE
                            WHEN cp.in_time IS NOT NULL AND cp.out_time IS NOT NULL
                            AND cp.out_time <= DATE_ADD(cp.in_time, INTERVAL 2 DAY) -- Validate OUT time
                            THEN TIMESTAMPDIFF(SECOND, cp.in_time, cp.out_time) / 3600
                            ELSE 0
                        END, 3
                    ) AS working_hours,
                    CASE 
                        WHEN cp.in_time IS NOT NULL THEN
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
                            END
                        ELSE 0
                    END AS late_entry,
                    0 AS is_total
                FROM CheckinPairs cp
                LEFT JOIN `tabEmployee` emp ON cp.employee = emp.employee
                WHERE cp.in_time IS NOT NULL
                AND cp.attendance_date = DATE(cp.in_time)
            ),

            -- Employees with no IN records and no unpaired OUT records are considered absent
            AbsentRecords AS (
                SELECT
                    emp.employee,
                    emp.employee_name,
                    dr.attendance_date,
                    DAYNAME(dr.attendance_date) AS attendance_day,
                    'Absent' AS status,
                    NULL AS shift_type,
                    NULL AS in_time,
                    NULL AS out_time,
                    0 AS working_hours,
                    0 AS late_entry,
                    0 AS is_total
                FROM DateRange dr
                CROSS JOIN `tabEmployee` emp
                LEFT JOIN CheckinPairs cp
                    ON emp.employee = cp.employee
                    AND cp.attendance_date = dr.attendance_date
                    AND cp.in_time IS NOT NULL
                LEFT JOIN UnpairedOUT uo
                    ON emp.employee = uo.employee
                    AND uo.attendance_date = dr.attendance_date
                WHERE (%(employee)s IS NULL OR emp.employee = %(employee)s)
                AND cp.employee IS NULL
                AND uo.employee IS NULL -- Exclude days with unpaired OUTs
                GROUP BY emp.employee, dr.attendance_date
            ),

            -- Unpaired OUT records marked as Present
            UnpairedOutRecords AS (
                SELECT
                    uo.employee,
                    emp.employee_name, -- Join with tabEmployee for correct name
                    uo.attendance_date,
                    DAYNAME(uo.attendance_date) AS attendance_day,
                    'Present' AS status, -- Per Requirement 1: Only OUT marked as Present
                    NULL AS shift_type,
                    NULL AS in_time,
                    uo.out_time,
                    0 AS working_hours,
                    0 AS late_entry,
                    0 AS is_total
                FROM UnpairedOUT uo
                LEFT JOIN `tabEmployee` emp ON uo.employee = emp.employee
            ),

            -- Combine all present/absent/unpaired records
            AllRecords AS (
                SELECT * FROM PresentRecords
                UNION
                SELECT * FROM AbsentRecords
                UNION
                SELECT * FROM UnpairedOutRecords
            ),

            -- Add a grand total summary for working hours
            GrandTotal AS (
                SELECT 
                    'Total' AS employee,
                    NULL AS employee_name,
                    NULL AS attendance_date,
                    NULL AS attendance_day,
                    NULL AS status,
                    NULL AS shift_type,
                    NULL AS in_time,
                    NULL AS out_time,
                    SUM(working_hours) AS working_hours,
                    NULL AS late_entry,
                    1 AS is_total
                FROM AllRecords
                WHERE employee = %(employee)s
            )

            -- Final output: daily records + total working hours(indra)
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
frappe.query_reports["New Employee Attendance Report"] = {
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