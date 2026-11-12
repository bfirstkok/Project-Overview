import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help='ตรวจ readiness ของ Microsoft SSO โดยไม่แสดงค่าลับ'
    def handle(self,*args,**kwargs):
        names=['MICROSOFT_TENANT_ID','MICROSOFT_CLIENT_ID','MICROSOFT_CLIENT_SECRET']
        missing=[name for name in names if not getattr(settings,name)]
        origin=os.getenv('SITE_ADDRESS','http://localhost:8000').rstrip('/')
        if not origin.startswith(('https://','http://')):origin='https://'+origin
        self.stdout.write('Redirect URI: '+origin+'/accounts/oidc/microsoft/login/callback/')
        self.stdout.write('Local password login: '+('development only' if settings.DEBUG and settings.ALLOW_LOCAL_LOGIN else 'disabled'))
        if missing:raise CommandError('Missing configuration: '+', '.join(missing))
        self.stdout.write(self.style.SUCCESS('Configuration present. A real Microsoft 365 login is still required to verify tenant/app permissions.'))
