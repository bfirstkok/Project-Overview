from django.conf import settings
from django.core.checks import register, Tags, Warning

@register(Tags.security, deploy=True)
def sso_readiness(app_configs, **kwargs):
    if not settings.DEBUG and not settings.MICROSOFT_SSO_READY:
        return [Warning('Microsoft 365 SSO ยังไม่พร้อม: ตั้ง MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID และ MICROSOFT_CLIENT_SECRET ก่อนเปิดใช้งานจริง',id='work.W001')]
    return []
