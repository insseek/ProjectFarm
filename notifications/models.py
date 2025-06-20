from django.db import models
from django.contrib.auth.models import User

from developers.models import Developer
from auth_top.models import TopUser


class Notification(models.Model):
    PRIORITY_CHOICES = (
        ('normal', '普通'),
        ('important', '重要'),
    )
    APP_CHOICES = (
        ('gear_farm', 'Gear-Farm'),
        ('gear_developer', '开发者端'),
        ('gear_test', 'Gear-Test'),
        ('gear_client', '客户端'),
    )

    user = models.ForeignKey(User, verbose_name='用户', related_name='notifications', on_delete=models.CASCADE, null=True,
                             blank=True)
    developer = models.ForeignKey(Developer, verbose_name='工程师', related_name='notifications', on_delete=models.CASCADE,
                                  null=True, blank=True)
    owner = models.ForeignKey(TopUser, verbose_name='所属人', related_name='notifications', null=True, blank=True,
                              on_delete=models.CASCADE)

    sender = models.ForeignKey(User, verbose_name='用户', related_name='send_notifications', on_delete=models.SET_NULL,
                               null=True,
                               blank=True)

    content = models.TextField(verbose_name='内容')
    url = models.URLField(verbose_name='网址', null=True, blank=True)

    is_read = models.BooleanField(verbose_name='已阅读', default=False)
    priority = models.CharField(verbose_name="优先级", max_length=15, choices=PRIORITY_CHOICES, default='normal')
    need_alert = models.BooleanField(verbose_name='需要弹窗提示', default=False)

    app_id = models.CharField(verbose_name="app", max_length=15, choices=APP_CHOICES, default='gear_farm')

    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    read_at = models.DateTimeField(verbose_name='阅读时间', null=True, blank=True)

    class Meta:
        verbose_name = '消息通知'
        ordering = ['-created_at']

    def __str__(self):
        return "{}: {}".format(self.developer.name, self.content)

    def save(self, *args, **kwargs):
        self.is_read = True if self.read_at else False

        if not self.owner:
            if self.user:
                owner, created = TopUser.get_or_create(user=self.user)
                self.owner = owner
            elif self.developer:
                owner, created = TopUser.get_or_create(developer=self.developer)
                self.owner = owner
        else:
            if self.owner.is_employee:
                self.user = self.owner.authentication
            elif self.owner.is_freelancer:
                self.developer = self.owner.authentication

        super(Notification, self).save(*args, **kwargs)

    @classmethod
    def read_notifications(cls):
        return cls.objects.exclude(read_at=None)

    @classmethod
    def unread_notifications(cls):
        return cls.objects.filter(read_at__isnull=True)
