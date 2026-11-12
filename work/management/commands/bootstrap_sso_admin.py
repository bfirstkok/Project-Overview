import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from work.models import User, Team, Activity
from work.sso import corporate_email

class Command(BaseCommand):
    help='เตรียม Admin จาก SSO_ADMIN_EMAIL โดยไม่สร้างรหัสผ่านและไม่ข้าม Microsoft SSO'
    @transaction.atomic
    def handle(self,*args,**kwargs):
        try: email=corporate_email(os.getenv('SSO_ADMIN_EMAIL',''))
        except Exception as exc: raise CommandError('ตั้ง SSO_ADMIN_EMAIL เป็นอีเมล @askme.co.th จริงก่อน') from exc
        team=Team.objects.get_or_create(name='Sales & Engineering')[0]
        user=User.objects.filter(email__iexact=email).first()
        if not user: user=User(username=email,email=email,team=team)
        user.role='admin'; user.is_active=True; user.set_unusable_password(); user.save()
        Activity.objects.create(actor=user,summary=f'เตรียม Admin สำหรับ Microsoft 365 SSO: {email}')
        self.stdout.write(self.style.SUCCESS('SSO Admin provisioned. No local password was created.'))
