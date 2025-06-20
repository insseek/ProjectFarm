from django.conf import settings
from django.core.cache import cache

from oauth.feishu_client import FeiShu


def get_feishu_client():
    tenant_access_token = cache.get('feishu_tenant_access_token')
    app_access_token = cache.get('feishu_app_access_token')
    if app_access_token and tenant_access_token:
        client = FeiShu(app_id=settings.FEISHU_FARM_APP_ID, app_secret=settings.FEISHU_FARM_APP_SECRET,
                        tenant_access_token=tenant_access_token, app_access_token=app_access_token)
    else:
        client = FeiShu(app_id=settings.FEISHU_FARM_APP_ID, app_secret=settings.FEISHU_FARM_APP_SECRET)
        tenant_access_token = client.tenant_access_token
        app_access_token = client.app_access_token
        if tenant_access_token:
            cache.set('feishu_tenant_access_token', tenant_access_token, 60 * 100)
        if app_access_token:
            cache.set('feishu_app_access_token', app_access_token, 60 * 100)
    return client
