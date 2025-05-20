# goldenapp/install.py

def after_install_all():
    from goldenapp.attendance_report import create_attendance_query_report
    from goldenapp.attendance_summary import create_daily_attendance_report
    from goldenapp.att_monthly  import create_attendance_summary_report
    from goldenapp.att_via_checkin import create_employee_checkin_query_report

    create_attendance_query_report()
    create_daily_attendance_report()
    create_attendance_summary_report()
    create_employee_checkin_query_report()
