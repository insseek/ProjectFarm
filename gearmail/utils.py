import re
import logging
import threading
from email.header import make_header

from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from django.core import mail


def email_message_attach_file(email_message, file):
    content = file.file.read()

    filename = file.file.name.split("-", 1)[1]
    filename = make_header([(filename, 'utf-8')]).encode('utf-8')
    email_message.attach(filename=filename, content=content)


def farm_send_email(email_record, email_signature):
    # 发件人
    from_email = email_record.from_email
    # 导师、产品、BD的邮箱
    manager_email = None
    mentor_email = None
    bd_email = None
    # 获取收件人 抄送人 密送人 回复人列表
    project = email_record.project
    if project.manager:
        manager_email = project.manager.email
    if project.mentor:
        mentor_email = project.mentor.email
    if getattr(project, 'proposal', None):
        if project.proposal.bd and project.proposal.bd.is_active:
            bd_email = project.proposal.bd.email

    to = email_record.to
    cc = email_record.cc
    bcc = email_record.bcc
    if to != None:
        to = re.sub(r'[;；,，]', ' ', email_record.to).split()
    if cc != None:
        cc = re.sub(r'[;；,，]', ' ', email_record.cc).split()
        if manager_email and from_email != manager_email and manager_email not in cc:
            cc.append(manager_email)
        if mentor_email and from_email != mentor_email and mentor_email not in cc:
            cc.append(mentor_email)
        if bd_email and from_email != bd_email and bd_email not in cc:
            cc.append(bd_email)

    if bcc != None:
        bcc = re.sub(r'[;；,，]', ' ', email_record.bcc).split()
        if from_email not in bcc:
            bcc.append(from_email)
    else:
        bcc = [from_email]
    email_record.bcc = ','.join(bcc)
    email_record.cc = ','.join(cc)
    reply_to = re.sub(r'[;；,，]', ' ', from_email).split()
    headers = {'From': from_email}
    body = email_record.content + email_signature
    sent = False
    # 发送邮件
    try:
        email_message = EmailMessage(subject=email_record.subject, body=body,
                                     from_email=settings.CLIENT_CONTACT_EMAIL_HOST_USER, to=to, bcc=bcc,
                                     headers=headers, cc=cc, reply_to=reply_to)
        threads = []
        for file in email_record.files.all():
            thread = threading.Thread(target=email_message_attach_file, args=(email_message, file))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        connection = mail.get_connection(username=settings.CLIENT_CONTACT_EMAIL_HOST_USER,
                                         password=settings.CLIENT_CONTACT_EMAIL_HOST_PASSWORD)
        success_num = connection.send_messages([email_message])
        #
        # success_num = email_message.send()
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)
        email_record.status = 0
        message = "项目【{}】邮件发送服务错误, 邮件记录已保存至草稿。错误详情：{}".format(email_record.project.name, str(e))
    else:
        if success_num:
            email_record.sent_at = timezone.now()
            email_record.status = 1
            sent = True
            message = "项目【{}】邮件发送成功".format(email_record.project.name)
            email_record.content = body
        else:
            email_record.status = 0
            message = "项目【{}】邮件发送失败 邮件记录已保存至草稿".format(email_record.project.name)
    email_record.save()
    return (sent, message)
