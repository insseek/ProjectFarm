from django.core.management.base import BaseCommand

from farmbase.tasks import sync_permissions_groups_from_production_env


class Command(BaseCommand):
    help = 'sync_permissions_groups_from_production_env'

    def handle(self, *args, **options):
        sync_permissions_groups_from_production_env()
