# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from prototypes.models import PrototypeReference

@shared_task
def get_prototype_reference_thumbnail(reference_id):
    references = PrototypeReference.objects.filter(pk=reference_id)
    if references.exists():
        reference = references.first()
        if reference.file and not reference.thumbnail:
            reference.thumbnail = reference.file
            reference.save()

