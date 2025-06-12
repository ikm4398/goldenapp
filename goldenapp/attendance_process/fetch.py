# #attendance_process/fetch.py
# import frappe
# from frappe import _
# from datetime import datetime, timedelta
# from frappe.utils import get_datetime, get_time, getdate
# from collections import defaultdict

# @frappe.whitelist()
# def fetch_employee_checkins(from_date, to_date):
#     try:
#         # Step 1: Fetch all check-ins in range, including day
#         query = """
#             SELECT name, employee, employee_name, log_type, time, day
#             FROM `tabEmployee Checkin`
#             WHERE DATE(time) BETWEEN %s AND %s
#             ORDER BY employee, time ASC
#         """
#         checkins = frappe.db.sql(query, (from_date, to_date), as_dict=True)

#         # Step 2: Group logs by employee
#         employee_logs = defaultdict(list)
#         for log in checkins:
#             employee_logs[log["employee"]].append(log)

#         attendance_created = []

#         # Step 3: Process each employee's logs
#         for employee, logs in employee_logs.items():
#             # Check number of active shift assignments
#             shift_count = len(frappe.get_all(
#                 "Shift Assignment",
#                 filters={
#                     "employee": employee,
#                     "status": "Active",
#                     "start_date": ["<=", to_date],
#                     "docstatus": 1,
#                 },
#                 fields=["name"]
#             ))

#             stack = []
#             paired_logs = []
#             unpaired_logs = []
#             # Track used timeframes per day to prevent duplicate pairings
#             used_timeframes = defaultdict(set)

#             if shift_count > 1:
#                 # Custom pairing logic for multiple shifts
#                 for log in logs:
#                     log_time = get_datetime(log["time"])
#                     log_hour = log_time.hour + log_time.minute / 60.0
#                     log_date = log_time.date()

#                     if log["log_type"] == "IN":
#                         stack.append(log)
#                     elif log["log_type"] == "OUT":
#                         valid_pair_found = False
#                         for i, in_log in enumerate(stack):
#                             in_time = get_datetime(in_log["time"])
#                             in_hour = in_time.hour + in_time.minute / 60.0
#                             in_date = in_time.date()
#                             out_time = log_time
#                             out_hour = out_time.hour + out_time.minute / 60.0

#                             # Ensure OUT is after IN
#                             if out_time <= in_time:
#                                 continue

#                             # Define timeframe key based on IN time window
#                             timeframe = None
#                             if 5 <= in_hour <= 12 and out_time.date() == in_time.date() and 9 <= out_hour <= 22:
#                                 timeframe = "morning"
#                             elif 12 <= in_hour <= 17 and out_time.date() == in_time.date() and 15 <= out_hour <= 22:
#                                 timeframe = "evening"
#                             elif in_hour > 16 and out_time.date() == in_time.date() + timedelta(days=1) and 5 <= out_hour <= 15:
#                                 timeframe = "night"

#                             # Check if timeframe is already used for this date
#                             if timeframe and timeframe not in used_timeframes[in_date]:
#                                 paired_logs.append((in_log, log))
#                                 used_timeframes[in_date].add(timeframe)
#                                 del stack[i]
#                                 valid_pair_found = True
#                                 break

#                         if not valid_pair_found:
#                             unpaired_logs.append(log)
#                             frappe.log_error(f"Unpaired OUT log for employee {employee} at {log_time}", "Checkin Processing")

#                 # Add unpaired IN logs to unpaired_logs
#                 unpaired_logs.extend(stack)
#                 for in_log in stack:
#                     frappe.log_error(f"Unpaired IN log for employee {employee} at {in_log['time']}", "Checkin Processing")

#             elif shift_count == 1:
#                 # Flexible pairing logic for single shift (IN 08:00–18:00, OUT any time after)
#                 for log in logs:
#                     log_time = get_datetime(log["time"])
#                     log_hour = log_time.hour + log_time.minute / 60.0
#                     log_date = log_time.date()

#                     if log["log_type"] == "IN":
#                         # Only include IN times between 08:00 and 18:00
#                         if 8 <= log_hour <= 18:
#                             stack.append(log)
#                         else:
#                             unpaired_logs.append(log)
#                             frappe.log_error(f"IN log outside 08:00–18:00 for employee {employee} at {log_time}", "Checkin Processing")
#                     elif log["log_type"] == "OUT":
#                         valid_pair_found = False
#                         for i, in_log in enumerate(stack):
#                             in_time = get_datetime(in_log["time"])
#                             in_date = in_time.date()
#                             out_time = log_time

#                             # Ensure OUT is after IN and within same or next day
#                             if in_time < out_time <= in_time + timedelta(days=1):
#                                 # Check if this date's shift is already used
#                                 if in_date not in used_timeframes:
#                                     paired_logs.append((in_log, log))
#                                     used_timeframes[in_date].add("single")
#                                     del stack[i]
#                                     valid_pair_found = True
#                                     break

#                         if not valid_pair_found:
#                             unpaired_logs.append(log)
#                             frappe.log_error(f"Unpaired OUT log for employee {employee} at {log_time}", "Checkin Processing")

#                 # Add unpaired IN logs to unpaired_logs
#                 unpaired_logs.extend(stack)
#                 for in_log in stack:
#                     frappe.log_error(f"Unpaired IN log for employee {employee} at {in_log['time']}", "Checkin Processing")

#             else:
#                 # No shifts: skip processing
#                 frappe.log_error(f"No active shift assignments for employee {employee}", "Checkin Processing")
#                 continue

#             # Step 4: Create attendance records for paired logs
#             for in_log, out_log in paired_logs:
#                 attendance_date = get_datetime(in_log["time"]).date()
#                 checkin_datetime = get_datetime(in_log["time"])
#                 checkin_time = get_time(checkin_datetime.time())
#                 out_datetime = get_datetime(out_log["time"])

#                 # Calculate working hours
#                 working_hours = (out_datetime - checkin_datetime).total_seconds() / 3600

#                 # Fetch shift assignment
#                 shift_details = get_shift_details(employee, checkin_datetime, checkin_time, attendance_date)
#                 if not shift_details:
#                     frappe.log_error(f"No valid shift found for employee {employee} on {attendance_date} at {checkin_time}", "Shift Assignment")
#                     continue

#                 # Calculate late entry and early exit
#                 late_entry = 1 if (checkin_datetime - shift_details["shift_start"]).total_seconds() / 60 > 15 else 0
#                 early_exit = 1 if (shift_details["shift_end"] - out_datetime).total_seconds() / 60 > 15 else 0

#                 # Insert attendance record
#                 attendance = frappe.new_doc("Attendance2")
#                 attendance.employee = employee
#                 attendance.employee_name = in_log["employee_name"]
#                 attendance.attendance_date = attendance_date
#                 attendance.in_time = in_log["time"]
#                 attendance.out_time = out_log["time"]
#                 attendance.working_hours = round(working_hours, 9)
#                 attendance.status = "Present"
#                 attendance.shift = shift_details["shift_type"]
#                 attendance.late_entry = late_entry
#                 attendance.early_exit = early_exit
#                 attendance.day = in_log["day"]  # Set day from IN log
#                 attendance.docstatus = 1
#                 attendance.insert(ignore_permissions=True)
#                 attendance_created.append(attendance.name)

#             # Step 5: Create attendance records for unpaired logs (for both single and multiple shifts)
#             if shift_count >= 1:
#                 for log in unpaired_logs:
#                     log_time = get_datetime(log["time"])
#                     attendance_date = log_time.date()
#                     log_hour = log_time.hour + log_time.minute / 60.0

#                     # Adjust attendance date for OUT logs before 10:00 (Night shift or flexible OUT)
#                     if log["log_type"] == "OUT" and log_hour <= 10:
#                         attendance_date = attendance_date - timedelta(days=1)

#                     # Fetch shift assignment
#                     shift_details = get_shift_details(employee, log_time, get_time(log_time.time()), attendance_date)
#                     if not shift_details:
#                         frappe.log_error(f"No valid shift found for employee {employee} on {attendance_date} at {log_time}", "Shift Assignment")
#                         continue

#                     # Calculate late entry or early exit
#                     late_entry = 1 if log["log_type"] == "IN" and (log_time - shift_details["shift_start"]).total_seconds() / 60 > 15 else 0
#                     early_exit = 1 if log["log_type"] == "OUT" and (shift_details["shift_end"] - log_time).total_seconds() / 60 > 15 else 0

#                     # Insert attendance record
#                     attendance = frappe.new_doc("Attendance2")
#                     attendance.employee = employee
#                     attendance.employee_name = log["employee_name"]
#                     attendance.attendance_date = attendance_date
#                     attendance.in_time = log["time"] if log["log_type"] == "IN" else None
#                     attendance.out_time = log["time"] if log["log_type"] == "OUT" else None
#                     attendance.working_hours = 0.0
#                     attendance.status = "Present"
#                     attendance.shift = shift_details["shift_type"]
#                     attendance.late_entry = late_entry
#                     attendance.early_exit = early_exit
#                     attendance.day = log["day"]  # Set day from log
#                     attendance.docstatus = 1
#                     attendance.insert(ignore_permissions=True)
#                     attendance_created.append(attendance.name)

#         return {
#             "status": "success",
#             "created": attendance_created
#         }

#     except Exception as e:
#         frappe.log_error(f"Error processing check-ins: {str(e)}", "Checkin Processing")
#         frappe.throw(_("An error occurred while processing check-in data: {0}").format(str(e)))

# def get_shift_details(employee, checkin_datetime, checkin_time, checkin_date):
#     try:
#         # Fetch active shift assignments for the employee
#         shift_assignments = frappe.get_all(
#             "Shift Assignment",
#             filters={
#                 "employee": employee,
#                 "status": "Active",
#                 "start_date": ["<=", checkin_date],
#                 "docstatus": 1,
#             },
#             fields=["shift_type", "start_time", "end_time"],
#         )

#         if not shift_assignments:
#             frappe.log_error(f"No active shift assignments for employee: {employee} on {checkin_date}", "Shift Assignment")
#             return None

#         # Buffer period: 120 minutes before shift start
#         buffer_minutes = 120
#         best_shift = None
#         min_time_diff = float('inf')

#         for shift in shift_assignments:
#             try:
#                 shift_start_time = get_time(shift.start_time)
#                 shift_end_time = get_time(shift.end_time)
#             except Exception as e:
#                 frappe.log_error(f"Error parsing shift times for {shift.shift_type}: {str(e)}", "Shift Assignment")
#                 continue

#             # Calculate shift start and end datetimes
#             shift_start_datetime = datetime.combine(checkin_date, shift_start_time)
#             buffer_start_datetime = shift_start_datetime - timedelta(minutes=buffer_minutes)
#             shift_end_date = checkin_date
#             if shift_end_time < shift_start_time:  # Night shift
#                 shift_end_date += timedelta(days=1)
#             shift_end_datetime = datetime.combine(shift_end_date, shift_end_time)

#             # Check if check-in is within buffer or shift duration
#             if buffer_start_datetime <= checkin_datetime <= shift_end_datetime:
#                 time_diff = abs((checkin_datetime - shift_start_datetime).total_seconds() / 60)
#                 if time_diff < min_time_diff:
#                     min_time_diff = time_diff
#                     best_shift = {
#                         "shift_type": shift.shift_type,
#                         "shift_start": shift_start_datetime,
#                         "shift_end": shift_end_datetime
#                     }

#         # Try next day for Night shifts
#         if not best_shift:
#             next_day = checkin_date + timedelta(days=1)
#             shift_assignments = frappe.get_all(
#                 "Shift Assignment",
#                 filters={
#                     "employee": employee,
#                     "status": "Active",
#                     "start_date": ["<=", next_day],
#                     "docstatus": 1,
#                 },
#                 fields=["shift_type", "start_time", "end_time"],
#             )

#             for shift in shift_assignments:
#                 try:
#                     shift_start_time = get_time(shift.start_time)
#                     shift_end_time = get_time(shift.end_time)
#                 except Exception as e:
#                     frappe.log_error(f"Error parsing shift times for {shift.shift_type}: {str(e)}", "Shift Assignment")
#                     continue

#                 shift_start_datetime = datetime.combine(checkin_date, shift_start_time)
#                 buffer_start_datetime = shift_start_datetime - timedelta(minutes=buffer_minutes)
#                 shift_end_date = checkin_date
#                 if shift_end_time < shift_start_time:
#                     shift_end_date += timedelta(days=1)
#                 shift_end_datetime = datetime.combine(shift_end_date, shift_end_time)

#                 if buffer_start_datetime <= checkin_datetime <= shift_end_datetime:
#                     time_diff = abs((checkin_datetime - shift_start_datetime).total_seconds() / 60)
#                     if time_diff < min_time_diff:
#                         min_time_diff = time_diff
#                         best_shift = {
#                             "shift_type": shift.shift_type,
#                             "shift_start": shift_start_datetime,
#                             "shift_end": shift_end_datetime
#                         }

#         if not best_shift:
#             frappe.log_error(f"No matching shift for employee {employee} on {checkin_date} at {checkin_time}", "Shift Assignment")
#             return None

#         return best_shift

#     except Exception as e:
#         frappe.log_error(f"Error in shift assignment for {employee}: {str(e)}", "Shift Assignment")
#         return None
import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils import get_datetime, get_time, getdate
from collections import defaultdict

@frappe.whitelist()
def fetch_employee_checkins(from_date, to_date):
    # Enqueue background job
    frappe.enqueue(
        method="goldenapp.attendance_process.fetch.process_checkins_background",
        queue="long",
        timeout=1500,
        job_name=f"Process Attendance from {from_date} to {to_date}",
        from_date=from_date,
        to_date=to_date
    )
    return {"status": "started", "message": _("Attendance data now processing in background.")}

def process_checkins_background(from_date, to_date):
    try:
        # Step 1: Fetch all check-ins in range
        query = """
            SELECT name, employee, employee_name, log_type, time, day
            FROM `tabEmployee Checkin`
            WHERE DATE(time) BETWEEN %s AND %s
            ORDER BY employee, time ASC
        """
        checkins = frappe.db.sql(query, (from_date, to_date), as_dict=True)

        employee_logs = defaultdict(list)
        for log in checkins:
            employee_logs[log["employee"]].append(log)

        attendance_created = []

        for employee, logs in employee_logs.items():
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
            used_timeframes = defaultdict(set)

            if shift_count > 1:
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

                            if out_time <= in_time:
                                continue

                            timeframe = None
                            if 5 <= in_hour <= 12 and out_time.date() == in_time.date() and 9 <= out_hour <= 22:
                                timeframe = "morning"
                            elif 12 <= in_hour <= 17 and out_time.date() == in_time.date() and 15 <= out_hour <= 22:
                                timeframe = "evening"
                            elif in_hour > 16 and out_time.date() == in_time.date() + timedelta(days=1) and 5 <= out_hour <= 15:
                                timeframe = "night"

                            if timeframe and timeframe not in used_timeframes[in_date]:
                                paired_logs.append((in_log, log))
                                used_timeframes[in_date].add(timeframe)
                                del stack[i]
                                valid_pair_found = True
                                break

                        if not valid_pair_found:
                            unpaired_logs.append(log)
                            frappe.log_error(f"Unpaired OUT log for {employee} at {log_time}", "Checkin Processing")

                unpaired_logs.extend(stack)
                for in_log in stack:
                    frappe.log_error(f"Unpaired IN log for {employee} at {in_log['time']}", "Checkin Processing")

            elif shift_count == 1:
                for log in logs:
                    log_time = get_datetime(log["time"])
                    log_hour = log_time.hour + log_time.minute / 60.0
                    log_date = log_time.date()

                    if log["log_type"] == "IN":
                        if 8 <= log_hour <= 18:
                            stack.append(log)
                        else:
                            unpaired_logs.append(log)
                            frappe.log_error(f"IN log outside 08:00–18:00 for {employee} at {log_time}", "Checkin Processing")
                    elif log["log_type"] == "OUT":
                        valid_pair_found = False
                        for i, in_log in enumerate(stack):
                            in_time = get_datetime(in_log["time"])
                            in_date = in_time.date()
                            out_time = log_time

                            if in_time < out_time <= in_time + timedelta(days=1):
                                if in_date not in used_timeframes:
                                    paired_logs.append((in_log, log))
                                    used_timeframes[in_date].add("single")
                                    del stack[i]
                                    valid_pair_found = True
                                    break

                        if not valid_pair_found:
                            unpaired_logs.append(log)
                            frappe.log_error(f"Unpaired OUT log for {employee} at {log_time}", "Checkin Processing")

                unpaired_logs.extend(stack)
                for in_log in stack:
                    frappe.log_error(f"Unpaired IN log for {employee} at {in_log['time']}", "Checkin Processing")

            else:
                frappe.log_error(f"No active shifts for {employee}", "Checkin Processing")
                continue

            for in_log, out_log in paired_logs:
                attendance_date = get_datetime(in_log["time"]).date()
                checkin_datetime = get_datetime(in_log["time"])
                checkin_time = get_time(checkin_datetime.time())
                out_datetime = get_datetime(out_log["time"])
                working_hours = (out_datetime - checkin_datetime).total_seconds() / 3600

                shift_details = get_shift_details(employee, checkin_datetime, checkin_time, attendance_date)
                if not shift_details:
                    continue

                late_entry = 1 if (checkin_datetime - shift_details["shift_start"]).total_seconds() / 60 > 15 else 0
                early_exit = 1 if (shift_details["shift_end"] - out_datetime).total_seconds() / 60 > 15 else 0

                attendance = frappe.new_doc("Attendance2")
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
                attendance.day = in_log["day"]
                attendance.docstatus = 1
                attendance.insert(ignore_permissions=True)
                attendance_created.append(attendance.name)

            if shift_count >= 1:
                for log in unpaired_logs:
                    log_time = get_datetime(log["time"])
                    attendance_date = log_time.date()
                    log_hour = log_time.hour + log_time.minute / 60.0

                    if log["log_type"] == "OUT" and log_hour <= 10:
                        attendance_date -= timedelta(days=1)

                    shift_details = get_shift_details(employee, log_time, get_time(log_time.time()), attendance_date)
                    if not shift_details:
                        continue

                    late_entry = 1 if log["log_type"] == "IN" and (log_time - shift_details["shift_start"]).total_seconds() / 60 > 15 else 0
                    early_exit = 1 if log["log_type"] == "OUT" and (shift_details["shift_end"] - log_time).total_seconds() / 60 > 15 else 0

                    attendance = frappe.new_doc("Attendance2")
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
                    attendance.day = log["day"]
                    attendance.docstatus = 1
                    attendance.insert(ignore_permissions=True)
                    attendance_created.append(attendance.name)

    except Exception as e:
        frappe.log_error(f"Background error: {str(e)}", "Checkin Background Job")
        raise e

def get_shift_details(employee, checkin_datetime, checkin_time, checkin_date):
    try:
        shift_assignments = frappe.get_all(
            "Shift Assignment",
            filters={
                "employee": employee,
                "status": "Active",
                "start_date": ["<=", checkin_date],
                "docstatus": 1,
            },
            fields=["shift_type", "start_time", "end_time"],
        )

        if not shift_assignments:
            return None

        buffer_minutes = 120
        best_shift = None
        min_time_diff = float('inf')

        for shift in shift_assignments:
            try:
                shift_start_time = get_time(shift.start_time)
                shift_end_time = get_time(shift.end_time)
            except Exception as e:
                continue

            shift_start_datetime = datetime.combine(checkin_date, shift_start_time)
            buffer_start_datetime = shift_start_datetime - timedelta(minutes=buffer_minutes)
            shift_end_date = checkin_date if shift_end_time >= shift_start_time else checkin_date + timedelta(days=1)
            shift_end_datetime = datetime.combine(shift_end_date, shift_end_time)

            if buffer_start_datetime <= checkin_datetime <= shift_end_datetime:
                time_diff = abs((checkin_datetime - shift_start_datetime).total_seconds() / 60)
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    best_shift = {
                        "shift_type": shift.shift_type,
                        "shift_start": shift_start_datetime,
                        "shift_end": shift_end_datetime
                    }

        return best_shift

    except Exception as e:
        frappe.log_error(f"Shift match error for {employee}: {str(e)}", "Shift Assignment")
        return None
