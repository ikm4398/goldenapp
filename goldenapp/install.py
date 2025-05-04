# goldenapp/install.py

def after_install_all():
    from goldenapp.attendance_report import create_attendance_query_report
    from goldenapp.attendance_summary import create_present_absent_summary_report

    create_attendance_query_report()
    create_present_absent_summary_report()
