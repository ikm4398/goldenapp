# import frappe
# from datetime import datetime
# import nepali_datetime
# import pytz  # Add this for explicit timezone handling

# @frappe.whitelist()
# def ad_to_bs_with_time(date_time_str=None):
#     if not date_time_str:
#         date_time_str = frappe.utils.now_datetime()  # Fallback to current datetime
#     try:
#         # Ensure input is timezone-aware and in Nepal timezone (+0545)
#         nepal_tz = pytz.timezone('Asia/Kathmandu')
#         ad_datetime = frappe.utils.get_datetime(date_time_str)
#         if ad_datetime.tzinfo is None:
#             ad_datetime = nepal_tz.localize(ad_datetime)  # Localize if naive
#         frappe.log("AD Datetime before conversion: {0}".format(ad_datetime))

#         # Convert to BS datetime
#         bs_datetime = nepali_datetime.datetime.from_datetime_datetime(ad_datetime)
#         frappe.log("BS Datetime after conversion: {0}".format(bs_datetime))

#         return bs_datetime.strftime("%Y-%m-%d %H:%M:%S")  # Returns BS date and time
#     except Exception as e:
#         frappe.log_error(f"AD to BS conversion error: {e}")
#         return "Invalid date/time"

import frappe
from datetime import datetime
import nepali_datetime
import pytz

@frappe.whitelist()
def ad_to_bs_with_time(date_time_str=None):
    if not date_time_str:
        date_time_str = frappe.utils.now_datetime()  # fallback to current datetime
    try:
        # Nepal timezone
        nepal_tz = pytz.timezone('Asia/Kathmandu')
        ad_datetime = frappe.utils.get_datetime(date_time_str)
        if ad_datetime.tzinfo is None:
            ad_datetime = nepal_tz.localize(ad_datetime)
        frappe.log("AD Datetime before conversion: {0}".format(ad_datetime))

        # Convert to BS datetime
        bs_datetime = nepali_datetime.date.from_datetime_date(ad_datetime.date())
        frappe.log("BS Date after conversion: {0}".format(bs_datetime))

        return bs_datetime.strftime("%Y-%m-%d")  # Only BS date
    except Exception as e:
        frappe.log_error(f"AD to BS conversion error: {e}")
        return "Invalid date/time"
