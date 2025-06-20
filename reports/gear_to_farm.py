import psycopg2
from .models import Report
from django.conf import settings


def import_from_gear():
    conn = psycopg2.connect(dbname="gearhome", user="postgres", password="geargear")
    cur = conn.cursor()
    cur.execute("select * from quiphtml_report;")
    result = cur.fetchall()
    for r in result:
        sql_to_report(r)
    cur.close()
    conn.close()


def sql_to_report(sql_result):
    report_id, uid, html, markdown, created_at, author, date, title, version, user_visible, show_next, show_services = sql_result
    if Report.objects.filter(uid=uid).count() == 0:
        report = Report()
        report.uid = uid
        report.html = html.replace("/media/", settings.QUIPFILE_URL)
        report.markdown = markdown
        report.created_at = created_at
        report.author = author
        report.date = date
        report.title = title
        report.version = version
        report.user_visible = user_visible
        report.show_next = show_next
        report.show_services = show_services
        report.expired_at = created_at
        report.extend_expiration()
        report.save()
