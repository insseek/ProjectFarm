import uuid
import logging
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericRelation
from django.conf import settings

from proposals.models import Proposal
from farmbase.utils import gen_uuid, seconds_to_format_str
from comments.models import Comment
from .tasks import get_call_record_callee_duration

logger = logging.getLogger()


class HuaWeiVoiceCallAuth(models.Model):
    username = models.CharField(verbose_name='用户名', max_length=100, unique=True)
    password = models.CharField(verbose_name='认证密码', max_length=100)
    access_token = models.CharField(verbose_name='访问令牌', max_length=180, blank=True, null=True)
    refresh_token = models.CharField(verbose_name='刷新令牌', max_length=180, blank=True, null=True)
    is_active = models.BooleanField(verbose_name='用户状态', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    expires_in = models.CharField(verbose_name='token有效期 单位为秒', max_length=32, default='')

    def __str__(self):
        return str(self.username)

    def expire_at(self):
        if self.modified_at and self.expires_in:
            try:
                seconds = int(self.expires_in)
                return self.modified_at + timedelta(seconds=seconds)
            except Exception as e:
                logger.info(e)

    class Meta:
        verbose_name = '华为语音通话认证用户'


class CallRecord(models.Model):
    def generate_filename(self, filename):
        url = "proposals/call_records/{}/{}".format(str(uuid.uuid4())[:8], filename)
        return url

    RECORD_FLAG_CHOICES = (
        (0, '未录音'),
        (1, '有录音'),
    )
    SOURCE_CHOICES = (
        (1, '个人上传'),
        (2, '话单通知'),
    )
    proposal = models.ForeignKey(Proposal, verbose_name='需求', related_name='call_records', blank=True, null=True,
                                 on_delete=models.SET_NULL)
    caller = models.ForeignKey(User, verbose_name="主叫用户", related_name='call_records', blank=True, null=True,
                               on_delete=models.SET_NULL)
    submitter = models.ForeignKey(User, verbose_name="提交人", related_name='submitted_call_records', blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL)
    caller_number = models.CharField(verbose_name="主叫号码", blank=True, null=True, max_length=32)
    callee_number = models.CharField(verbose_name="被叫号码", max_length=128, blank=True, null=True)

    source = models.IntegerField(verbose_name="记录来源", choices=SOURCE_CHOICES, default=2)
    record_flag = models.IntegerField(verbose_name="录音标识", choices=RECORD_FLAG_CHOICES, default=0)
    record_date = models.DateField(verbose_name="录音日期", max_length=128, blank=True, null=True)
    file = models.FileField(upload_to=generate_filename, blank=True, null=True)
    file_size = models.CharField(verbose_name="文件大小", max_length=100, blank=True, null=True)
    filename = models.CharField(verbose_name="文件名称", max_length=100, blank=True, null=True)
    file_suffix = models.CharField(verbose_name="文件后缀", max_length=10, blank=True, null=True)
    number = models.IntegerField(verbose_name="编号", default=0)

    record_start_time = models.DateTimeField(verbose_name="录音开始时间", blank=True, null=True)
    record_file_download_url = models.TextField(verbose_name="录音文件下载地址", blank=True, null=True)

    download_url_updated_at = models.DateTimeField(
        verbose_name="录音文件下载地址更新时间", blank=True, null=True)
    record_object_name = models.CharField(verbose_name="录音文件名", max_length=128, blank=True, null=True)
    record_bucket_name = models.CharField(verbose_name="录音文件名所在的目录名", max_length=128, blank=True, null=True)
    record_domain = models.CharField(verbose_name="存放录音文件的域名", max_length=128, blank=True, null=True)

    session_id = models.CharField(verbose_name="通话链路的会话标识", max_length=256, blank=True, null=True)
    icid = models.CharField(verbose_name="呼叫记录标识", max_length=64, blank=True, null=True)
    uid = models.CharField(max_length=25, blank=True, null=True, unique=True)

    call_in_time = models.DateTimeField(verbose_name="呼入开始时间", blank=True, null=True)
    call_end_time = models.DateTimeField(verbose_name="呼叫结束时间", blank=True, null=True)
    call_out_answer_time = models.DateTimeField(verbose_name="Initcall的呼出应答时间", blank=True, null=True)
    fwd_answer_time = models.DateTimeField(verbose_name="转接应答时间", blank=True, null=True)
    fail_time = models.DateTimeField(verbose_name="呼入、呼出的失败时间", blank=True, null=True)

    user_data = models.CharField(verbose_name="用户", max_length=32, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment, related_query_name="call_records")
    call_duration = models.CharField(verbose_name="通话时长", max_length=32, blank=True, null=True)

    def __str__(self):
        if self.filename:
            title = self.filename
        else:
            title = self.created_at.strftime(settings.DATETIME_FORMAT)
        if self.proposal:
            title = "需求【{}】:".format(self.proposal.id) + title
        return title

    def save(self, *args, **kwargs):
        if self.proposal and not self.number:
            other_records = self.proposal.call_records.exclude(pk=self.id).order_by('-number')
            if other_records.exists():
                self.number = other_records.first().number + 1
            else:
                self.number = 1
        if not self.uid:
            self.uid = gen_uuid()
        if self.file:
            self.record_flag = 1
        else:
            self.record_flag = 0
        super(CallRecord, self).save(*args, **kwargs)

    def get_call_duration(self):
        if self.file and not self.record_flag:
            self.record_flag = 1
            self.save()
        if not self.call_duration and self.file:
            if self.call_end_time and self.fwd_answer_time:
                total_seconds = (self.call_end_time - self.fwd_answer_time).total_seconds()
                call_duration = seconds_to_format_str(total_seconds)
                self.call_duration = call_duration
                self.save()
            else:
                get_call_record_callee_duration.delay(self.id)
        return self.call_duration

    class Meta:
        verbose_name = '通话记录'
        ordering = ['-created_at']
