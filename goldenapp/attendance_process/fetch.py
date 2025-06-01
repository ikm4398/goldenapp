#goldenapp/attendance_process/fetch.py
import frappe
from frappe import _

@frappe.whitelist()
def fetch_employee_checkins(from_date, to_date):
 
    try:
        # Build the query
        conditions = [
            "DATE(time) BETWEEN %s AND %s"
        ]
        params = [from_date, to_date]
        query = f"""
            SELECT name, employee, employee_name, log_type, time
            FROM `tabEmployee Checkin`
            WHERE {" AND ".join(conditions)}
            ORDER BY time ASC
        """
        
        # Execute the query
        checkins = frappe.db.sql(query, params, as_dict=True)
        
        return checkins
    except Exception as e:
        frappe.log_error(f"Error fetching employee check-ins: {str(e)}")
        frappe.throw(_("An error occurred while fetching check-in data: {0}").format(str(e)))