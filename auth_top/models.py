import binascii
import os

from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.utils import timezone

from developers.models import Developer
from clients.models import Client


# 为了更方便支持  User、Developer的登录认证
class TopUser(models.Model):
    USER_TYPES = ('employee', 'freelancer', 'client')

    user = models.OneToOneField(
        User, related_name='top_user',
        on_delete=models.CASCADE, verbose_name="内部员工",
        blank=True, null=True
    )
    developer = models.OneToOneField(
        Developer, related_name='top_user',
        on_delete=models.CASCADE, verbose_name='自由工程师',
        blank=True, null=True
    )
    client = models.OneToOneField(
        Client, related_name='top_user',
        on_delete=models.CASCADE, verbose_name='客户',
        blank=True, null=True
    )

    USER_TYPE_EMPLOYEE = 'employee'
    USER_TYPE_FREELANCER = 'freelancer'
    USER_TYPE_CLIENT = 'client'

    class Meta:
        verbose_name = "顶层用户"

    def __str__(self):
        return self.authentication.username

    def user_info(self):
        from auth_top.serializers import TopUserViewSerializer
        return TopUserViewSerializer(self).data

    @classmethod
    def get_or_create(cls, user=None, developer=None, client=None):
        top_user = None
        create = False
        if user:
            top_user, create = TopUser.objects.get_or_create(user=user)
        elif developer:
            top_user, create = TopUser.objects.get_or_create(developer=developer)
        elif client:
            top_user, create = TopUser.objects.get_or_create(client=client)
        if top_user:
            TopToken.objects.get_or_create(top_user=top_user)
        return top_user, create

    @classmethod
    def get_obj_by_phone(cls, user_type, phone):
        top_user = None
        if user_type == cls.USER_TYPE_EMPLOYEE:
            auth = User.objects.filter(profile__phone_number=phone, is_active=True).first()
            if auth:
                top_user, create = TopUser.objects.get_or_create(user=auth)
        elif user_type == cls.USER_TYPE_FREELANCER:
            auth = Developer.objects.filter(phone=phone, is_active=True).first()
            if auth:
                top_user, create = TopUser.objects.get_or_create(developer=auth)
        elif user_type == cls.USER_TYPE_CLIENT:
            auth = Client.objects.filter(phone=phone, is_active=True).first()
            if auth:
                top_user, create = TopUser.objects.get_or_create(client=auth)
        return top_user

    @classmethod
    def get_obj_by_gitlab_user_id(cls, user_type, gitlab_user_id):
        top_user = None
        if user_type == cls.USER_TYPE_EMPLOYEE:
            auth = User.objects.filter(profile__gitlab_user_id=gitlab_user_id, is_active=True).first()
            if auth:
                top_user, create = TopUser.objects.get_or_create(user=auth)
        elif user_type == cls.USER_TYPE_FREELANCER:
            auth = Developer.objects.filter(gitlab_user_id=gitlab_user_id, is_active=True).first()
            if auth:
                top_user, create = TopUser.objects.get_or_create(developer=auth)
        return top_user

    @classmethod
    def get_obj_by_feishu_user_id(cls, user_type, feishu_user_id):
        top_user = None
        if user_type == cls.USER_TYPE_EMPLOYEE:
            auth = User.objects.filter(profile__feishu_user_id=feishu_user_id, is_active=True).first()
            if auth:
                top_user, create = TopUser.objects.get_or_create(user=auth)
        elif user_type == cls.USER_TYPE_FREELANCER:
            auth = Developer.objects.filter(feishu_user_id=feishu_user_id, is_active=True).first()
            if auth:
                top_user, create = TopUser.objects.get_or_create(developer=auth)
        return top_user

    @property
    def avatar(self):
        profile = self.authentication.profile if self.is_employee else self.authentication
        if profile.avatar:
            return profile.avatar.url

    @property
    def avatar_url(self):
        return self.avatar

    @property
    def avatar_color(self):
        profile = self.authentication.profile if self.is_employee else self.authentication
        return profile.avatar_color

    @property
    def authentication(self):
        return self.user or self.developer or self.client

    @property
    def is_active(self):
        return self.authentication.is_active

    @property
    def is_superuser(self):
        if self.is_employee:
            return self.authentication.is_superuser
        return False

    @property
    def is_authenticated(self):
        return True

    @property
    def user_type(self):
        if self.user:
            return self.USER_TYPE_EMPLOYEE
        elif self.developer:
            return self.USER_TYPE_FREELANCER
        elif self.client:
            return self.USER_TYPE_CLIENT

    @property
    def is_employee(self):
        if self.user:
            return True
        return False

    @property
    def is_freelancer(self):
        if self.developer:
            return True
        return False

    @property
    def is_developer(self):
        if self.developer:
            return True
        return False

    @property
    def is_client(self):
        if self.client:
            return True
        return False

    @property
    def username(self):
        return self.authentication.username

    @property
    def phone(self):
        if self.is_employee:
            return self.authentication.profile.phone
        return self.authentication.phone

    def set_phone(self, phone):
        if self.is_employee:
            if phone != self.authentication.profile.phone_number:
                self.authentication.profile.phone_number = phone
                self.authentication.profile.save()
        else:
            if phone != self.authentication.phone:
                self.authentication.phone = phone
                self.authentication.save()


class TopToken(models.Model):
    """
    The default authorization token model.
    """
    key = models.CharField('密钥', max_length=40, primary_key=True)
    top_user = models.OneToOneField(
        TopUser, related_name='authentication_token',
        on_delete=models.CASCADE, verbose_name='顶层用户',
    )
    created = models.DateTimeField('创建时间', default=timezone.now)

    class Meta:
        verbose_name = "Token"

    def __str__(self):
        return self.key

    @property
    def user_type(self):
        return self.top_user.user_type

    @classmethod
    def get_or_create(cls, user=None, developer=None, client=None, top_user=None, refresh=False):
        if not top_user:
            if user:
                top_user, create = TopUser.objects.get_or_create(user=user)
            elif developer:
                top_user, create = TopUser.objects.get_or_create(developer=developer)
            elif client:
                top_user, create = TopUser.objects.get_or_create(client=client)
        if top_user:
            token, token_create = cls.objects.get_or_create(top_user=top_user)
            if not token_create and refresh:
                cls.objects.filter(top_user=top_user).delete()
                token = cls.objects.create(top_user=top_user)
            return token, token_create

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(TopToken, self).save(*args, **kwargs)

    @staticmethod
    def generate_key():
        return binascii.hexlify(os.urandom(20)).decode()
