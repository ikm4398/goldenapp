import frappe
from frappe.utils import get_time
from datetime import datetime, timedelta

def get_shift_details(employee, checkin_datetime, checkin_time, checkin_date):
    try:
        # Fetch active shift assignments for the employee
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
            frappe.log_error(f"No active shift assignments for employee: {employee} on {checkin_date}", "Shift Assignment")
            return None

        # Buffer period: 120 minutes before shift start
        buffer_minutes = 120
        best_shift = None
        min_time_diff = float('inf')

        for shift in shift_assignments:
            try:
                shift_start_time = get_time(shift.start_time)
                shift_end_time = get_time(shift.end_time)
            except Exception as e:
                frappe.log_error(f"Error parsing shift times for {shift.shift_type}: {str(e)}", "Shift Assignment")
                continue

            # Calculate shift start and end datetimes
            shift_start_datetime = datetime.combine(checkin_date, shift_start_time)
            buffer_start_datetime = shift_start_datetime - timedelta(minutes=buffer_minutes)
            shift_end_date = checkin_date
            if shift_end_time < shift_start_time:  # Night shift
                shift_end_date += timedelta(days=1)
            shift_end_datetime = datetime.combine(shift_end_date, shift_end_time)

            # Check if check-in is within buffer or shift duration
            if buffer_start_datetime <= checkin_datetime <= shift_end_datetime:
                time_diff = abs((checkin_datetime - shift_start_datetime).total_seconds() / 60)
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    best_shift = {
                        "shift_type": shift.shift_type,
                        "shift_start": shift_start_datetime,
                        "shift_end": shift_end_datetime
                    }

        # Try next day for Night shifts
        if not best_shift:
            next_day = checkin_date + timedelta(days=1)
            shift_assignments = frappe.get_all(
                "Shift Assignment",
                filters={
                    "employee": employee,
                    "status": "Active",
                    "start_date": ["<=", next_day],
                    "docstatus": 1,
                },
                fields=["shift_type", "start_time", "end_time"],
            )

            for shift in shift_assignments:
                try:
                    shift_start_time = get_time(shift.start_time)
                    shift_end_time = get_time(shift.end_time)
                except Exception as e:
                    frappe.log_error(f"Error parsing shift times for {shift.shift_type}: {str(e)}", "Shift Assignment")
                    continue

                shift_start_datetime = datetime.combine(checkin_date, shift_start_time)
                buffer_start_datetime = shift_start_datetime - timedelta(minutes=buffer_minutes)
                shift_end_date = checkin_date
                if shift_end_time < shift_start_time:
                    shift_end_date += timedelta(days=1)
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

        if not best_shift:
            frappe.log_error(f"No matching shift for employee {employee} on {checkin_date} at {checkin_time}", "Shift Assignment")
            return None

        return best_shift

    except Exception as e:
        frappe.log_error(f"Error in shift assignment for {employee}: {str(e)}", "Shift Assignment")
        return None
