#attendance_process/fetch.py
import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils import get_datetime, get_time, getdate
from collections import defaultdict
from goldenapp.attendance_process.get_shift import get_shift_details

@frappe.whitelist()
def fetch_employee_checkins(from_date, to_date):
    try:
        # Step 1: Fetch all check-ins in range, including day
        query = """
            SELECT name, employee, employee_name, log_type, time, day
            FROM `tabEmployee Checkin`
            WHERE DATE(time) BETWEEN %s AND %s
            ORDER BY employee, time ASC
        """
        checkins = frappe.db.sql(query, (from_date, to_date), as_dict=True)

        # Step 2: Group logs by employee
        employee_logs = defaultdict(list)
        for log in checkins:
            employee_logs[log["employee"]].append(log)

        attendance_created = []

        # Step 3: Process each employee's logs
        for employee, logs in employee_logs.items():
            # Check number of active shift assignments
            shift_count = len(frappe.get_all(
                "Shift Assignment",
                filters={
                    "employee": employee,
                    "status": "Active",
                    "start_date": ["<=", to_date],
                    "docstatus": 1,
                },
                fields=["name"]
            ))

            stack = []
            paired_logs = []
            unpaired_logs = []
            # Track used timeframes per day to prevent duplicate pairings
            used_timeframes = defaultdict(set)

            if shift_count > 1:
                # Custom pairing logic for multiple shifts
                for log in logs:
                    log_time = get_datetime(log["time"])
                    log_hour = log_time.hour + log_time.minute / 60.0
                    log_date = log_time.date()

                    if log["log_type"] == "IN":
                        stack.append(log)
                    elif log["log_type"] == "OUT":
                        valid_pair_found = False
                        for i, in_log in enumerate(stack):
                            in_time = get_datetime(in_log["time"])
                            in_hour = in_time.hour + in_time.minute / 60.0
                            in_date = in_time.date()
                            out_time = log_time
                            out_hour = out_time.hour + out_time.minute / 60.0

                            # Ensure OUT is after IN
                            if out_time <= in_time:
                                continue

                            # Define timeframe key based on IN time window
                            timeframe = None
                            if 5 <= in_hour <= 12 and out_time.date() == in_time.date() and 9 <= out_hour <= 16:
                                timeframe = "morning"
                            elif 12 <= in_hour <= 16 and out_time.date() == in_time.date() and 15 <= out_hour <= 22:
                                timeframe = "evening"
                            elif in_hour > 16 and out_time.date() == in_time.date() + timedelta(days=1) and 5 <= out_hour <= 10:
                                timeframe = "night"

                            # Check if timeframe is already used for this date
                            if timeframe and timeframe not in used_timeframes[in_date]:
                                paired_logs.append((in_log, log))
                                used_timeframes[in_date].add(timeframe)
                                del stack[i]
                                valid_pair_found = True
                                break

                        if not valid_pair_found:
                            unpaired_logs.append(log)
                            frappe.log_error(f"Unpaired OUT log for employee {employee} at {log_time}", "Checkin Processing")

                # Add unpaired IN logs to unpaired_logs
                unpaired_logs.extend(stack)
                for in_log in stack:
                    frappe.log_error(f"Unpaired IN log for employee {employee} at {in_log['time']}", "Checkin Processing")

            elif shift_count == 1:
                # Flexible pairing logic for single shift (IN 08:00–18:00, OUT only same day)
                for log in logs:
                    log_time = get_datetime(log["time"])
                    log_hour = log_time.hour + log_time.minute / 60.0
                    log_date = log_time.date()

                    if log["log_type"] == "IN":
                        # Only include IN times between 08:00 and 18:00
                        if 8 <= log_hour <= 18:
                            stack.append(log)
                        else:
                            unpaired_logs.append(log)
                            frappe.log_error(f"IN log outside 08:00–18:00 for employee {employee} at {log_time}", "Checkin Processing")

                    elif log["log_type"] == "OUT":
                        valid_pair_found = False
                        for i, in_log in enumerate(stack):
                            in_time = get_datetime(in_log["time"])
                            in_date = in_time.date()
                            out_time = log_time

                            # Ensure OUT is after IN and within same day only
                            if in_time < out_time and out_time.date() == in_date:
                                if in_date not in used_timeframes:
                                    paired_logs.append((in_log, log))
                                    used_timeframes[in_date].add("single")
                                    del stack[i]
                                    valid_pair_found = True
                                    break

                        if not valid_pair_found:
                            unpaired_logs.append(log)
                            frappe.log_error(f"Unpaired OUT log (next-day OUT disallowed) for employee {employee} at {log_time}", "Checkin Processing")

                # Add unpaired IN logs to unpaired_logs
                unpaired_logs.extend(stack)
                for in_log in stack:
                    frappe.log_error(f"Unpaired IN log for employee {employee} at {in_log['time']}", "Checkin Processing")

            else:
                # No shifts: skip processing
                frappe.log_error(f"No active shift assignments for employee {employee}", "Checkin Processing")
                continue

            # Step 4: Create attendance records for paired logs
            for in_log, out_log in paired_logs:
                attendance_date = get_datetime(in_log["time"]).date()
                checkin_datetime = get_datetime(in_log["time"])
                checkin_time = get_time(checkin_datetime.time())
                out_datetime = get_datetime(out_log["time"])

                # Calculate working hours
                working_hours = (out_datetime - checkin_datetime).total_seconds() / 3600

                # Fetch shift assignment
                shift_details = get_shift_details(employee, checkin_datetime, checkin_time, attendance_date)
                if not shift_details:
                    frappe.log_error(f"No valid shift found for employee {employee} on {attendance_date} at {checkin_time}", "Shift Assignment")
                    continue

                # Calculate late entry and early exit
                late_entry = 1 if (checkin_datetime - shift_details["shift_start"]).total_seconds() / 60 > 15 else 0
                early_exit = 1 if (shift_details["shift_end"] - out_datetime).total_seconds() / 60 > 15 else 0

                # Insert attendance record
                attendance = frappe.new_doc("Employee Attendance")
                attendance.employee = employee
                attendance.employee_name = in_log["employee_name"]
                attendance.attendance_date = attendance_date
                attendance.in_time = in_log["time"]
                attendance.out_time = out_log["time"]
                attendance.working_hours = round(working_hours, 9)
                attendance.status = "Present"
                attendance.shift = shift_details["shift_type"]
                attendance.late_entry = late_entry
                attendance.early_exit = early_exit
                attendance.day = in_log["day"]  # Set day from IN log
                attendance.docstatus = 1
                attendance.insert(ignore_permissions=True)
                attendance_created.append(attendance.name)

            # Step 5: Create attendance records for unpaired logs (for both single and multiple shifts)
            if shift_count >= 1:
                for log in unpaired_logs:
                    log_time = get_datetime(log["time"])
                    attendance_date = log_time.date()
                    log_hour = log_time.hour + log_time.minute / 60.0

                    # Adjust attendance date for OUT logs before 10:00 (Night shift or flexible OUT)
                    if log["log_type"] == "OUT" and log_hour <= 10:
                        attendance_date = attendance_date - timedelta(days=1)

                    # Fetch shift assignment
                    shift_details = get_shift_details(employee, log_time, get_time(log_time.time()), attendance_date)
                    if not shift_details:
                        frappe.log_error(f"No valid shift found for employee {employee} on {attendance_date} at {log_time}", "Shift Assignment")
                        continue

                    # Calculate late entry or early exit
                    late_entry = 1 if log["log_type"] == "IN" and (log_time - shift_details["shift_start"]).total_seconds() / 60 > 15 else 0
                    early_exit = 1 if log["log_type"] == "OUT" and (shift_details["shift_end"] - log_time).total_seconds() / 60 > 15 else 0

                    # Insert attendance record
                    attendance = frappe.new_doc("Employee Attendance")
                    attendance.employee = employee
                    attendance.employee_name = log["employee_name"]
                    attendance.attendance_date = attendance_date
                    attendance.in_time = log["time"] if log["log_type"] == "IN" else None
                    attendance.out_time = log["time"] if log["log_type"] == "OUT" else None
                    attendance.working_hours = 0.0
                    attendance.status = "Present"
                    attendance.shift = shift_details["shift_type"]
                    attendance.late_entry = late_entry
                    attendance.early_exit = early_exit
                    attendance.day = log["day"]  # Set day from log
                    attendance.docstatus = 1
                    attendance.insert(ignore_permissions=True)
                    attendance_created.append(attendance.name)

        return {
            "status": "success",
            "created": attendance_created
        }

    except Exception as e:
        frappe.log_error(f"Error processing check-ins: {str(e)}", "Checkin Processing")
        frappe.throw(_("An error occurred while processing check-in data: {0}").format(str(e)))

