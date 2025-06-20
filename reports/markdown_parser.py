import contextlib
import logging
import os.path
import re

import markdown
from django.conf import settings
from django.utils import timezone

from gearfarm.utils.common_utils import gen_uuid
from reports import quip
from reports.models import Report, Section, DocRecord, Plan
from reports.utils import get_report_uid


class ReportMarkDownParser:
    QUIP_TOKEN = settings.QUIP_TOKEN

    def __init__(self, mdtext, request=None):
        self.mdtext = mdtext  # input
        self.html = mdtext  # output
        self.title = None
        self.docRecord = None
        self.docRecords = []
        self.plans = []
        self.request = request

        # 报告内容列表 以h2分割
        self.sections = []
        self.catalogue = []

    def parse(self):
        self.removeComments()
        self.html = markdown.markdown(self.html)
        self.parseBlobs()
        self.extractInfo()
        self.extractSections()
        self.extractPlans()
        return self.html

    def removeComments(self):
        self.html = self.html.split('* * *')[0]
        return self.html

    def parseBlobs(self):
        p = re.compile('(\[Image[^\]]+blob\/(\S+)\/(\S+)\])')
        for m in p.finditer(self.html):
            filepath = self.saveBlobFromMatch(m)
            self.replaceImageTag(m.group(1), filepath)
        return (self.html)

    def replaceImageTag(self, mdimagetag, filepath):
        self.html = self.html.replace(mdimagetag, '<img src="{}" />'.format(filepath))

    def saveBlob(self, threadId, blobId):
        client = quip.QuipClient(access_token=self.QUIP_TOKEN)
        file_path = settings.QUIPFILE_ROOT + threadId + '/' + blobId
        dir_path = os.path.dirname(file_path)

        logger = logging.getLogger(__name__)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        file_url = settings.QUIPFILE_URL + threadId + '/' + blobId
        if os.path.exists(file_path):
            logger.info("%s exists, skipping download" % (file_path))
            return file_url

        for i in range(0, 8):
            try:
                with open(file_path, 'wb') as imageFile:
                    imageFile.write(client.get_blob(threadId, blobId).read())
                    logger.info(file_path + ' saved as ' + file_url)
                    return file_url
            except Exception as ex:
                with contextlib.suppress(FileNotFoundError):
                    os.remove(file_path)
                logger.warning("Attemp to save %s failed" % (blobId))
                logger.warning(ex)

        logger.error('Failed to save %s' % (blobId))
        return

    # 根据正则匹配保存blob
    def saveBlobFromMatch(self, imageMatch):
        threadId = imageMatch.group(2)
        blobId = imageMatch.group(3)
        return self.saveBlob(threadId, blobId)

    def new_report(self, proposal, show_next, show_services):
        uid = get_report_uid()
        report = Report(
            proposal=proposal,
            markdown=self.mdtext,
            creation_source='markdown',
            published_at=timezone.now(),
            html=self.html,
            title=self.title,
            version=self.docRecord.version,
            author=self.docRecord.author,
            date=self.docRecord.date,
            uid=uid,
            show_next=show_next,
            show_services=show_services)
        if self.request:
            report.creator = self.request.user
        return report

    def save(self, proposal, show_next, show_services):
        report = self.new_report(proposal, show_next=show_next, show_services=show_services)
        report.save()
        report.extend_expiration()
        return report

    def replace_report(self, proposal, show_next, show_services, repeated_report=None):
        if repeated_report:
            repeated_report.proposal = proposal
            repeated_report.markdown = self.mdtext
            repeated_report.html = self.html
            repeated_report.title = self.title
            repeated_report.version = self.docRecord.version
            repeated_report.author = self.docRecord.author
            repeated_report.date = self.docRecord.date
            repeated_report.show_next = show_next
            repeated_report.show_services = show_services
            repeated_report.created_at = timezone.now()
            repeated_report.published_at = timezone.now()
            if self.request:
                repeated_report.creator = self.request.user
            repeated_report.save()
            repeated_report.extend_expiration()
            return repeated_report

    def extractInfo(self):
        p_info = re.compile(
            r'版本[:：](?P<version>[\S\s]*?)[\n\r]日期[:：](?P<date>[\S\s]*?)[\n\r]制作人[:：](?P<author>[\S\s]*?)[\n\r]')
        p_title = re.compile('<h1>([\S\s]*)</h1>')
        for m in p_info.finditer(self.html):
            docRecord = DocRecord()
            docRecord.version = m.group('version').replace('<br>', '').replace('<p>', '').replace('</p>', '')
            docRecord.date = m.group('date').replace('<br>', '').replace('<p>', '').replace('</p>', '')
            docRecord.author = m.group('author').replace('<br>', '').replace('<p>', '').replace('</p>', '')
            self.docRecords.append(docRecord)
        self.docRecord = self.docRecords[0]
        for m in p_title.finditer(self.html):
            self.title = m.group(1)

    def extractSections(self):
        self.html = re.sub(r'<h2>[\s]*</h2>', '', self.html).strip()
        p_section = re.compile(r'<h2>(?P<title>[\S\s]*?)</h2>(?P<content>[\S\s]*?)(?=<h2>)')
        for m in p_section.finditer(self.html):
            content = re.sub(r'<p>[\s]*(<br[/]?>)?[\s]*</p>', '', m.group('content')).strip()
            content = re.sub(r'\s+', '', content)
            title = re.sub(r'<[\S\s]*?>', '', m.group('title')).strip()
            if content:
                section = Section()
                section.title = title
                section.content = m.group('content')
                self.sections.append(section)
                catalogue_data = {"title": title, "uid": section.uid, "type": "h2",
                                  "children": []}
                self.catalogue.append(catalogue_data)

    def extractPlans(self):
        p_oneplan = re.compile(r'<h3>(?P<title>[\S\s]*?)</h3>\s*<p>(?P<plan>[\S\s]*?)</p>')
        p_sect = re.compile(r'(?P<name>[\S]*?)[:：](?P<content>[^\r\n]*)')
        for m in p_oneplan.finditer(self.html):
            plan = Plan()
            plan.title = m.group('title').replace('<br>', '').replace('<p>', '').replace('</p>', '')
            plantext = m.group('plan')
            for m in p_sect.finditer(plantext):
                name = m.group('name').replace('<br>', '').replace('<p>', '').replace('</p>', '')
                content = m.group('content').replace('<br>', '').replace('<p>', '').replace('</p>', '')
                item = (name, content)
                if name in ['报价估算', '报价']:
                    plan.price = content
                    if content and "万" in content:
                        plan.price = content.replace("万", '')
                        plan.price_unit = "万"
                else:
                    plan.items.append(item)
            self.plans.append(plan)
