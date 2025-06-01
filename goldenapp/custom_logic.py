from datetime import datetime, timedelta
import frappe
from frappe.utils import get_datetime, get_time, getdate

def override_shift_assignment(doc, method):
    try:
        # Check if employee and check-in time are present
        if not doc.employee or not doc.time:
            frappe.log_error(f"No employee or time in Employee Checkin: {doc.name}", "Shift Assignment Override")
            return

        # Get check-in time and date
        checkin_datetime = get_datetime(doc.time)
        checkin_time = get_time(checkin_datetime.time())
        checkin_date = getdate(checkin_datetime.date())
        log_type = doc.log_type

        # Only process for log_type "IN"
        if log_type != "IN":
            return

        # Fetch active shift assignments for the employee
        shift_assignments = frappe.get_all(
            "Shift Assignment",
            filters={
                "employee": doc.employee,
                "status": "Active",
                "start_date": ["<=", checkin_date],
                "docstatus": 1,
            },
            fields=["shift_type", "start_time", "end_time"],
        )

        # If no shift assignments, skip
        if not shift_assignments:
            frappe.log_error(f"No active shift assignments for employee: {doc.employee}", "Shift Assignment Override")
            return

        # Define buffer period (e.g., 60 minutes before shift start)
        buffer_minutes = 60

        # Check each shift assignment
        for shift in shift_assignments:
            try:
                # Convert shift start and end times to datetime.time
                shift_start_time = get_time(shift.start_time)
                shift_end_time = get_time(shift.end_time)
            except Exception as e:
                frappe.log_error(f"Error parsing shift times for {shift.shift_type}: {str(e)}", "Shift Assignment Override")
                continue

            # Calculate buffer start time
            buffer_start_datetime = datetime.combine(checkin_date, shift_start_time) - timedelta(minutes=buffer_minutes)
            buffer_start_time = get_time(buffer_start_datetime.time())

            # Check if check-in time is within the buffer period or at shift start
            if buffer_start_time <= checkin_time <= shift_start_time:
                # Determine shift end date (handle cross-day shifts)
                shift_end_date = checkin_date
                if shift_end_time < shift_start_time:  # Night shift spanning midnight
                    shift_end_date += timedelta(days=1)

                # Override shift details
                doc.shift = shift.shift_type
                doc.shift_start = datetime.combine(checkin_date, shift_start_time)
                doc.shift_end = datetime.combine(shift_end_date, shift_end_time)
                doc.shift_actual_start = doc.shift_start
                doc.shift_actual_end = doc.shift_end
                frappe.msgprint(f"Shift overridden to {shift.shift_type} for check-in at {checkin_time}")
                break

    except Exception as e:
        frappe.log_error(f"Error in shift assignment override for {doc.employee}: {str(e)}", "Shift Assignment Override")