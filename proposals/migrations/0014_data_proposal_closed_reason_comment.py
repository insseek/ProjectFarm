# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import re

from django.contrib.contenttypes.models import ContentType
from django.db import migrations

logger = logging.getLogger(__name__)


def get_closed_reason_from_log(log):
    p = re.compile(r'[\S\s]*;(?P<comment>[\S\s]*)$', re.M)
    logger.info('latest log:' + log.content)
    m = p.match(log.content)
    if m:
        return m.group('comment').strip()
    return ''


def extract_closed_reason(apps, schema_editor):
    Proposal = apps.get_model("proposals", "Proposal")
    try:
        Log = apps.get_model("projects", "Log")
    except LookupError:
        return
    proposal_type = ContentType.objects.get(app_label="proposals", model="proposal")
    closed_proposals = Proposal.objects.filter(status=6)

    for proposal in closed_proposals:
        logs = Log.objects.filter(
            content_type_id=proposal_type.id,
            object_id=proposal.id,
            content__contains="关闭理由"
        ).order_by(
            '-id'
        )

        logger.info('proposal id: %d' % (proposal.id))
        if logs.count() > 0:
            closed_reason = get_closed_reason_from_log(logs.first())
            logger.info(proposal.name or ' '.join(proposal.description[:10].splitlines()) + ": " + closed_reason)
            proposal.closed_reason_comment = closed_reason
            proposal.save()


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0013_proposal_closed_reason_comment'),
    ]
    operations = [
        migrations.RunPython(extract_closed_reason, migrations.RunPython.noop),
    ]
