from django.core.management.base import BaseCommand

from farmbase.permissions_init import init_func_perms


class Command(BaseCommand):
    help = '权限的数据维护在farmbase.permissions_init中'

    def handle(self, *args, **options):
        init_func_perms(build_groups=False)
