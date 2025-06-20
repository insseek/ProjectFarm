import time

from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericRelation
from easy_thumbnails.fields import ThumbnailerImageField

from comments.models import Comment
from logs.models import Log
from taggit.managers import TaggableManager


class Platform(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = '平台'

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = '类型'

    def __str__(self):
        return self.name


class Collection(models.Model):
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='prototype_collections', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    platforms = models.ManyToManyField(Platform, related_name='prototype_collections', verbose_name='平台')
    categories = models.ManyToManyField(Category, related_name='prototype_collections', verbose_name='类型')
    created_at = models.DateTimeField(auto_now_add=True)
    logs = GenericRelation(Log, related_query_name="prototype_collections")

    class Meta:
        verbose_name = '原型参考集'
        ordering = ['-created_at']

    def __str__(self):
        platform_str = self.platforms.first().name if self.platforms.exists() else ''
        category_str = self.categories.first().name if self.categories.exists() else ''
        return '{} {}'.format(platform_str, category_str)

    @property
    def cover_picture(self):
        references = self.prototype_references.all()
        if references.exists():
            cover_picture = references.filter(is_cover=True).first()
            if not cover_picture:
                cover_picture = references.first()
                cover_picture.is_cover = True
                cover_picture.save()
            return cover_picture


class PrototypeReference(models.Model):
    def generate_filename(self, filename):
        url = "prototypes/%s-%s" % (str(time.time()), filename)
        return url

    collection = models.ForeignKey(Collection, verbose_name='提交人', related_name='prototype_references', blank=True,
                                   null=True,
                                   on_delete=models.CASCADE)
    file = models.ImageField(upload_to=generate_filename)
    thumbnail = ThumbnailerImageField(upload_to=generate_filename, blank=True, null=True)
    filename = models.CharField(verbose_name="文件名称", max_length=128)
    is_cover = models.BooleanField(verbose_name="封面图", default=False)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='prototype_references', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    platforms = models.ManyToManyField(Platform, related_name='prototypes', verbose_name='平台')
    categories = models.ManyToManyField(Category, related_name='prototypes', verbose_name='类型')

    logs = GenericRelation(Log, related_query_name="prototype_references")
    comments = GenericRelation(Comment, related_query_name="prototype_references")
    tags = TaggableManager()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '原型参考'
        ordering = ['-is_cover', '-created_at']

    def __str__(self):
        return self.filename
