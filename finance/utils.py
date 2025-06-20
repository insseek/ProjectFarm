import base64
import hashlib
import subprocess
from datetime import timedelta
import os
import json

from django.conf import settings
from django.contrib.auth.models import User

from gearfarm.utils.pdf_utils import PDFUtil
from gearfarm.utils.common_utils import this_week_friday
from farmbase.utils import get_protocol_host
from notifications.utils import create_notification_to_users
from finance.models import JobPayment


def build_payments_for_regular_job_contract(obj):
    # 固定工程师打款示例
    # {"timedelta_weeks":2,  "amount":9000}
    if obj.status == 'signed' and obj.contract_category == 'regular':
        if not obj.payments.exists() and obj.contract_money:
            developer = obj.developer
            contract_amount = obj.contract_money
            remit_way = json.loads(obj.remit_way) if obj.remit_way else None
            if obj.pay_way == 'installments' and remit_way:
                # exists_amount = 0
                # remaining_amount = contract_amount - exists_amount
                timedelta_weeks = remit_way['timedelta_weeks']
                if not timedelta_weeks or timedelta_weeks < 1:
                    timedelta_weeks = 1
                period_amount = remit_way['amount']
                period_days = timedelta_weeks * 7
                period_count = 1
                start_date = obj.develop_date_start
                while obj.remaining_payment_amount > 0:
                    amount = period_amount
                    if obj.remaining_payment_amount < amount:
                        amount = obj.remaining_payment_amount
                    this_date = start_date + timedelta(days=period_days * period_count - 1)
                    friday = this_week_friday(this_date)
                    JobPayment.objects.create(
                        job_contract=obj,
                        status=0,
                        developer=developer,
                        name=developer.name,
                        payee_name=developer.payee_name,
                        payee_id_card_number=developer.payee_id_card_number,
                        payee_phone=developer.payee_phone,
                        payee_opening_bank=developer.payee_opening_bank,
                        payee_account=developer.payee_account,
                        amount=amount,
                        expected_at=friday,
                    )
                    # exists_amount += amount
                    # remaining_amount -= amount
                    period_count += 1
            else:
                end_date = obj.develop_date_end
                friday = this_week_friday(end_date)
                JobPayment.objects.create(
                    job_contract=obj,
                    status=0,
                    developer=developer,
                    name=developer.name,
                    payee_name=developer.payee_name,
                    payee_id_card_number=developer.payee_id_card_number,
                    payee_phone=developer.payee_phone,
                    payee_opening_bank=developer.payee_opening_bank,
                    payee_account=developer.payee_account,
                    amount=contract_amount,
                    expected_at=friday,
                )


def send_payment_notification(request, payment, origin):
    project = payment.project
    if origin.status != payment.status:
        new_status = payment.status
        notification_users = []
        if payment.job_contract and payment.job_contract.contract_category == 'regular':
            contract_url = get_protocol_host(request) + '/finance/developers/regular_contracts/?status=signed'
            content = '{}负责的固定工程师【{}】的一笔打款{}，金额：【{}】'.format(
                payment.manager, payment.developer.name, payment.status_display, payment.amount)
        else:
            contract_url = get_protocol_host(request) + '/projects/{}/?anchor=roles'.format(project.id)
            content = '{}的项目【{}】的工程师【{}】的一笔打款{}，金额：【{}】'.format(
                project.manager, project, payment.developer.name, payment.status_display, payment.amount)
        finance_url = get_protocol_host(request) + '/finance/developers/payments/'
        if new_status == 1:
            url = finance_url
            finance_users = User.objects.filter(groups__name=settings.GROUP_NAME_DICT["finance"], is_active=True)
            for user in finance_users:
                if user and user != request.user:
                    notification_users.append(user)
        else:
            url = contract_url
            for user in [payment.manager, project.mentor if project else None]:
                if user and user != request.user:
                    notification_users.append(user)
        if notification_users:
            create_notification_to_users(notification_users, content, url)


def word_to_pdf(docPath, contract_id):
    try:
        from comtypes import client
    except ImportError:
        client = None

    try:
        from win32com.client import constants, gencache
    except ImportError:
        constants = None
        gencache = None
    doc2pdf(docPath, client, gencache, constants, contract_id)


def doc2pdf(docPath, client, gencache, constants, contract_id):
    """
        convert a doc/docx document to pdf format
        :param doc: path to document
        """
    docPathTrue = os.path.abspath(docPath)  # bugfix - searching files in windows/system32
    if client:
        import pythoncom
        pythoncom.CoInitialize()
        word = gencache.EnsureDispatch('Word.Application')
        doc = word.Documents.Open(docPathTrue, ReadOnly=1)
        word_name = docPath.split('.')[0]
        pdfPath = word_name + '.pdf'
        doc.ExportAsFixedFormat(pdfPath,
                                constants.wdExportFormatPDF,
                                Item=constants.wdExportDocumentWithMarkup,
                                CreateBookmarks=constants.wdExportCreateHeadingBookmarks)
        word.Quit(constants.wdDoNotSaveChanges)
    else:  # 判断环境，linux环境这里为None
        out_dir = settings.MEDIA_ROOT + 'finance/developer_contract'
        return doc2pdf_linux(docPathTrue, out_dir)


def doc2pdf_linux(docPath, out_dir):
    """
    convert a doc/docx document to pdf format (linux only, requires libreoffice)
    :param doc: path to document
    """
    # cmd = 'libreoffice --invisible --convert-to pdf'.split() + [docPath] + ['--outdir'] + [out_dir]
    # p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    # p.wait(timeout=30)
    # stdout, stderr = p.communicate()
    # if stderr:
    #     raise subprocess.SubprocessError(stderr)
    cmd = ['libreoffice', '--invisible', '--convert-to', 'pdf:writer_pdf_Export', docPath, '--outdir', out_dir]
    subprocess.call(cmd, timeout=30)


def content_encoding(path: str):
    """
    文件转 bytes 加密并使用 base64 编码
    :param path: 文件路径
    :return: 返回加密编码后的字符串
    """
    with open(path, 'rb') as f:
        content = f.read()
    content_md5 = hashlib.md5()
    content_md5.update(content)
    content_base64 = base64.b64encode(content_md5.digest())
    return content_base64.decode("utf-8")


def find_sign_location(file_path, search_value):
    """
    获取指定文字在pdf中的页码和坐标
    """
    pdf_util = PDFUtil()
    data = pdf_util.search_text_boxes_position_y(file_path, search_value)
    if data:
        page_data = data[0]
        page_index = page_data['page']
        position_y = page_data['boxes'][0]['position_y']
        return page_index, position_y
