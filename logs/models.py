import json
import re

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Model

from logs.utils import get_field_value


class Log(models.Model):
    content_type = models.ForeignKey(ContentType, related_name='logs', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    content = models.TextField(verbose_name='内容', blank=True, null=True)
    content_data = models.TextField(verbose_name='内容数据', blank=True, null=True)
    operator = models.ForeignKey(
        User,
        verbose_name='操作人-Farm用户',
        related_name='operation_logs',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    operator_developer = models.ForeignKey(
        'developers.Developer',
        verbose_name='操作人-工程师',
        related_name='operation_logs',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    creator = models.ForeignKey('auth_top.TopUser', verbose_name='创建人', related_name='created_logs', null=True,
                                blank=True,
                                on_delete=models.CASCADE)
    codename = models.CharField(verbose_name='代号', max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name = '操作记录'
        ordering = ['-created_at']

    def __str__(self):
        if self.content_data:
            content_data = json.loads(self.content_data)
            if content_data['subtitle']:
                return content_data['title'] + ':' + content_data['subtitle']
            return content_data['title']

    def save(self, *args, **kwargs):
        from auth_top.models import TopUser
        if not self.creator:
            if self.operator:
                creator, created = TopUser.get_or_create(user=self.operator)
                self.creator = creator
            elif self.operator_developer:
                creator, created = TopUser.get_or_create(developer=self.operator_developer)
                self.creator = creator
        else:
            if self.creator.is_employee:
                self.operator = self.creator.authentication
            else:
                self.operator_developer = self.creator.authentication

        super(Log, self).save(*args, **kwargs)

    @classmethod
    def build_create_object_log(cls, operator, created_object, related_object=None, comment=None, codename=None):
        if not operator.is_authenticated:
            return None
        model_name = created_object._meta.model_name
        title = '新建' + created_object._meta.verbose_name
        subtitle = str(created_object)
        content_data = {"type": "create", "model_name": model_name, "title": title, "subtitle": subtitle, "fields": [],
                        "comment": comment}
        return cls.build_log(operator, content_data, created_object, related_object, codename=codename)

    @classmethod
    def build_update_object_log(cls, operator, original, updated, related_object=None, comment=None, codename=None):
        if not operator.is_authenticated:
            return None

        model_name = updated._meta.model_name
        title = '修改' + updated._meta.verbose_name
        subtitle = str(updated)

        content_data = {"type": "update", "model_name": model_name, "title": title, "subtitle": subtitle, "fields": [],
                        "comment": comment}
        fields = updated._meta.get_fields()

        from testing.models import Bug
        is_bug = isinstance(updated, Bug)

        for field in fields:
            if not field.editable:
                continue
            # 多对多deepcopy存不了
            if isinstance(field, models.ManyToManyField):
                continue

            if is_bug:
                if field.name == 'description':
                    continue
                if field.name == 'description_text':
                    old_value = get_field_value(original, field)
                    new_value = get_field_value(updated, field)
                    old_html = old_value if old_value else ''
                    new_html = new_value if new_value else ''
                    if re.sub(r'\r|\n|\s', '', new_html) == re.sub(r'\r|\n|\s', '', old_html):
                        continue

            old_value = get_field_value(original, field)
            new_value = get_field_value(updated, field)

            if old_value != new_value:
                name = field.name
                verbose_name = field.verbose_name
                op_data = {"type": "update", "name": name, "verbose_name": verbose_name,
                           "old_value": old_value,
                           "new_value": new_value}
                content_data["fields"].append(op_data)
        if content_data["fields"]:
            return cls.build_log(operator, content_data, updated, related_object, codename=codename)

    @classmethod
    def build_delete_object_log(cls, operator, deleted_object, related_object=None, comment=None, codename=None):
        if not operator.is_authenticated:
            return None
        model_name = deleted_object._meta.model_name
        title = '删除' + deleted_object._meta.verbose_name
        subtitle = str(deleted_object)
        content_data = {"type": "delete", "model_name": model_name, "title": title, "subtitle": subtitle, "fields": [],
                        "comment": comment}
        return cls.build_log(operator, content_data, deleted_object, related_object, codename=codename)

    @classmethod
    def build_log(cls, operator, content_data, current_object, related_object, codename=None):
        if not related_object:
            related_object = current_object
        content_data = json.dumps(content_data, ensure_ascii=False)
        log = None
        from auth_top.models import TopUser
        from developers.models import Developer

        user = None
        developer = None
        top_user = None
        if isinstance(operator, User):
            user = operator
            top_user, created = TopUser.get_or_create(user=user)
        elif isinstance(operator, Developer):
            developer = operator
            top_user, created = TopUser.get_or_create(developer=developer)
        elif isinstance(operator, TopUser):
            top_user = operator
            developer = operator.authentication if top_user.is_developer else None
            user = operator.authentication if top_user.is_employee else None
        if any([user, developer, top_user]):
            log = cls(operator=user, operator_developer=developer, creator=top_user, content_object=related_object,
                      content_data=content_data)
            log.codename = codename or None
            log.save()
            return log


class BrowsingHistory(models.Model):
    content_type = models.ForeignKey(ContentType, related_name='browsing_histories', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    visitor = models.ForeignKey(
        User,
        verbose_name='浏览者',
        related_name='browsing_histories',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )
    user = models.ForeignKey('auth_top.TopUser', verbose_name='浏览用户', related_name='browsing_histories',
                             null=True,
                             blank=True,
                             on_delete=models.SET_NULL)
    ip_address = models.CharField(max_length=100, verbose_name='IP地址', blank=True, null=True)
    address = models.CharField(max_length=100, verbose_name='地理位置', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    created_date = models.DateField(auto_now_add=True, blank=True, null=True)
    done_at = models.DateTimeField(verbose_name="结束时间", blank=True, null=True)
    browsing_seconds = models.IntegerField(verbose_name="浏览秒数", blank=True, null=True)

    @property
    def browsing_time(self):
        if self.browsing_seconds:
            total_seconds = self.browsing_seconds
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            result_str = '{}秒'.format(seconds)
            if minutes:
                result_str = '{}分钟'.format(minutes) + result_str
            if hours:
                result_str = "{}小时".format(hours) + result_str
            return result_str

    @classmethod
    def build_log(cls, visitor, current_object, ip_address=None, browsing_seconds=None, top_user=None):
        if visitor and visitor.is_authenticated:
            log = cls(visitor=visitor, content_object=current_object, ip_address=ip_address,
                      browsing_seconds=browsing_seconds)
        else:
            log = cls(content_object=current_object, ip_address=ip_address,
                      browsing_seconds=browsing_seconds)
        if top_user:
            log.user = top_user
        log.save()
        return log

    class Meta:
        verbose_name = '浏览记录'
        ordering = ['-created_at']
