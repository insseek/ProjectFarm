from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation

from projects.models import Project
from files.models import File


class EmailTemplate(models.Model):
    title = models.CharField(max_length=200, verbose_name='模板名称', blank=True, null=True)
    subject = models.CharField(max_length=200, verbose_name='邮件主题')
    content = models.TextField(verbose_name='邮件正文')
    cc = models.CharField(max_length=200, verbose_name='抄送人', blank=True, null=True)

    class Meta:
        ordering = ['title']


class EmailRecord(models.Model):
    RESULT_CODES = (
        (0, "失败"),
        (1, "成功"),
        (2, "草稿")
    )
    user = models.ForeignKey(User, related_name='email_records', on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, related_name='email_records', blank=True, null=True, on_delete=models.CASCADE)
    template = models.ForeignKey(EmailTemplate, related_name='email_records', null=True, blank=True,
                                 on_delete=models.SET_NULL)

    from_email = models.EmailField(verbose_name='发件人')
    to = models.CharField(max_length=200, verbose_name='收件人', blank=True, null=True)
    cc = models.CharField(max_length=200, verbose_name='抄送人', null=True, blank=True)
    bcc = models.CharField(max_length=200, verbose_name='密送人', null=True, blank=True)
    subject = models.CharField(max_length=200, verbose_name='邮件主题')
    content = models.TextField(verbose_name='邮件正文')
    # title = models.CharField(max_length=200, verbose_name="邮件标题")

    status = models.IntegerField(choices=RESULT_CODES, default=2)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    sent_at = models.DateTimeField(verbose_name='发送时间', null=True, blank=True)

    file_list = GenericRelation(File, related_query_name="email_records")

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name = '邮件记录'
        ordering = ['-created_at']
        permissions = (
            ("gear_use_farm_send_email", "使用Farm发送邮件"),
        )

    @property
    def files(self):
        return self.file_list.filter(is_deleted=False).order_by('created_at')
