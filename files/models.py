import time

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage


class File(models.Model):
    def generate_filename(self, filename):
        url = "files/%s-%s" % (str(time.time()), filename)
        return url

    file = models.FileField(upload_to=generate_filename)
    filename = models.CharField(verbose_name="文件名称", max_length=128, blank=True, null=True)

    remark = models.CharField(verbose_name="备注", max_length=50, blank=True, null=True)
    suffix = models.CharField(max_length=20, verbose_name='后缀', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = '文件'

    def __str__(self):
        return self.filename

    def save(self, *args, **kwargs):
        if not self.suffix:
            self.suffix = self.get_suffix()
        super(File, self).save(*args, **kwargs)

    def get_suffix(self):
        if self.filename and '.' in self.filename:
            return self.filename.rsplit(".", 1)[1]


class PublicFile(models.Model):
    def generate_filename(self, filename):
        url = "public-files/{}-{}".format(str(time.time()), filename)
        return url

    file = models.FileField(upload_to=generate_filename, storage=S3Boto3Storage(acl='public-read'))
    filename = models.CharField(verbose_name="文件名称", max_length=128, blank=True, null=True)
    suffix = models.CharField(max_length=20, verbose_name='后缀', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '文件'

    def __str__(self):
        return self.filename

    def save(self, *args, **kwargs):
        if not self.suffix:
            self.suffix = self.get_suffix()
        super(PublicFile, self).save(*args, **kwargs)

    def get_suffix(self):
        if self.filename and '.' in self.filename:
            return self.filename.rsplit(".", 1)[1]

    @property
    def clean_url(self):
        url = self.file.url
        clean_url = url.rsplit('?')[0]
        return clean_url
