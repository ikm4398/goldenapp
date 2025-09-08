app_name = "goldenapp"
app_title = "Goldenapp"
app_publisher = "ik"
app_description = "a"
app_email = "ik@gmail.com"
app_license = "mit"

# Apps

after_install = "goldenapp.install.after_install_all"

# # Merge the two doc_events into one
# doc_events = {
#     "Employee Checkin": {
#         "before_save": "goldenapp.custom_logic.override_shift_assignment",
#         "after_insert": "goldenapp.auto_attendance.link_checkins_to_attendance"
#     }
# }

# Fixed indentation (no indent, module-level)
app_include_js = "/assets/goldenapp/js/attendance_process.js"
# goldenapp/hooks.py
app_include_js = [
    "/assets/nepali_calendar/js/bs_converter.js",
    "/assets/nepali_calendar/dist/bs_converter.iife.js",
]

jinja = {
    "methods": [
        "goldenapp.utils.ad_to_bs_with_time"
    ]
}