import random

from django.db import models
from django.contrib.auth.models import User, Group


class Team(models.Model):
    name = models.CharField(verbose_name="名称", max_length=64, unique=True)
    leader = models.ForeignKey(User, verbose_name='团队负责人', related_name='lead_teams', on_delete=models.SET_NULL,
                               null=True, blank=True)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '团队'

    def __str__(self):
        return self.name

    @property
    def members(self):
        members = User.objects.filter(team_users__team_id=self.id).distinct()
        return members


class TeamUser(models.Model):
    team = models.ForeignKey(Team, verbose_name='团队', related_name='team_users',
                             on_delete=models.CASCADE)
    user = models.ForeignKey(User, verbose_name='用户',
                             related_name='team_users',
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '团队成员'


class Profile(models.Model):
    AVATAR_COLORS = (
        ('#212736', 'Black'),
        ('#2161FD', 'Blue'),
        ('#36B37E', 'Green'),
        ('#F5121D', 'Red'),
        ('#FE802F', 'Orange'),
        ('#9254DE', 'Purple'),
        ('#EB2F96', 'Magenta'),
    )

    def generate_filename(self, filename):
        url = "avatar-{}-{}".format(self.user.username, filename)
        return url

    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to=generate_filename, verbose_name='头像', null=True, blank=True)
    avatar_color = models.CharField(verbose_name='头像颜色', choices=AVATAR_COLORS, max_length=10, blank=True, null=True)
    phone_number = models.CharField(max_length=20, verbose_name='手机号', null=True, blank=True)
    email_signature = models.TextField(verbose_name='邮箱签名', null=True, blank=True)
    project_capacity = models.IntegerField(verbose_name="接受项目最大数", null=True, blank=True)

    dd_id = models.CharField(verbose_name="钉钉ID", max_length=30, blank=True, null=True)
    feishu_user_id = models.CharField(verbose_name="飞书ID", max_length=30, blank=True, null=True)
    gitlab_user_id = models.IntegerField(verbose_name="对应gitlab账户的id", blank=True, null=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.avatar_color:
            self.avatar_color = self.get_random_avatar_color()
        super(Profile, self).save(*args, **kwargs)

    def get_random_avatar_color(self):
        randint = random.randint(0, len(self.AVATAR_COLORS) - 1)
        return self.AVATAR_COLORS[randint][0]

    def send_feishu_message(self, message):

        from notifications.tasks import send_feishu_message_to_individual

        if self.feishu_user_id:
            send_feishu_message_to_individual.delay(self.feishu_user_id, message)

    @property
    def phone(self):
        return self.phone_number


class Documents(models.Model):
    title = models.CharField(max_length=100, verbose_name='文档标题')
    url = models.URLField(verbose_name='文档链接')
    groups = models.ManyToManyField(Group, verbose_name='文档分组', related_name='documents')
    index = models.IntegerField(verbose_name="排序位置", default=0)

    def __str__(self):
        return self.title


class FunctionModule(models.Model):
    name = models.CharField(verbose_name='name', max_length=50, unique=True)
    codename = models.CharField(verbose_name='codename', max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '功能模块'


class FunctionPermission(models.Model):
    module = models.ForeignKey(FunctionModule, related_name='func_perms', verbose_name='模块', on_delete=models.SET_NULL,
                               null=True,
                               blank=True)
    name = models.CharField(verbose_name='name', max_length=100, )
    codename = models.CharField(verbose_name='codename', max_length=100, unique=True)
    users = models.ManyToManyField(User, related_name='func_perms', verbose_name='用户')
    groups = models.ManyToManyField(Group, related_name='func_perms', verbose_name='用户组')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '功能模块权限'
        ordering = ('module__name', 'codename')
