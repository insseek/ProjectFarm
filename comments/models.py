import re

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from files.models import File


class Comment(models.Model):
    parent = models.ForeignKey(to='self', blank=True, related_name='child_comments', null=True,
                               on_delete=models.SET_NULL)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    content = models.TextField(verbose_name='内容', null=True, blank=True)
    content_text = models.TextField(verbose_name='内容文本', null=True, blank=True)
    creator = models.ForeignKey('auth_top.TopUser', verbose_name='创建人', related_name='comments', null=True, blank=True,
                                on_delete=models.SET_NULL)
    author = models.ForeignKey(User, verbose_name='评论人', related_name='comments', on_delete=models.SET_NULL, null=True,
                               blank=True)

    developer = models.ForeignKey('developers.Developer', verbose_name='评论工程师', related_name='comments',
                                  on_delete=models.SET_NULL,
                                  null=True,
                                  blank=True)
    codename = models.CharField(verbose_name='代号', max_length=30, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_sticky = models.BooleanField(default=False)
    file_list = GenericRelation(File, related_query_name="work_orders")

    class Meta:
        verbose_name = '评论'
        ordering = ['-is_sticky', 'created_at']

    def save(self, *args, **kwargs):
        from auth_top.models import TopUser
        if not self.creator:
            if self.author:
                creator, created = TopUser.get_or_create(user=self.author)
                self.creator = creator
            elif self.developer:
                creator, created = TopUser.get_or_create(developer=self.developer)
                self.creator = creator
        else:
            if self.creator.is_employee:
                self.author = self.creator.authentication
            elif self.creator.is_developer:
                self.developer = self.creator.authentication
        if not self.content_text and self.content:
            self.content_text = re.sub(r'<.*?>', '', self.content.replace('&nbsp;', ' '))
        super(Comment, self).save(*args, **kwargs)

    def clean_content(self):
        if self.content_text:
            return self.content_text
        return re.sub(r'<.*?>', '', self.content.replace('&nbsp;', ' '))

    @classmethod
    def get_child_comments(cls, comment):
        # 【code review】'RelatedManager' object is not iterable
        # child_comments = comment.child_comments
        child_comments = comment.child_comments.all()
        for child in child_comments:
            child_comments = child_comments | cls.get_child_comments(child)
        return child_comments

    @property
    def files(self):
        return self.file_list.filter(is_deleted=False).order_by('created_at')
