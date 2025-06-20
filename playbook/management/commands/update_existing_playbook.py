from django.core.management.base import BaseCommand

from playbook.utils import update_ongoing_project_playbook, update_ongoing_proposal_playbook


class Command(BaseCommand):
    help = 'Update existing projects and proposals and add new playbook items'

    def handle(self, *args, **options):
        update_ongoing_project_playbook()
        update_ongoing_proposal_playbook()