from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.core.validators import validate_email
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.auth_backends import AuthenticationBackend
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from .models import User, Team, Activity
import uuid

def corporate_email(value):
    email=(value or '').strip().casefold()
    validate_email(email)
    if email.rpartition('@')[2]!='askme.co.th': raise ValidationError('ใช้อีเมล @askme.co.th เท่านั้น')
    return email

def local_login_allowed(): return settings.DEBUG and settings.ALLOW_LOCAL_LOGIN

class LocalDevelopmentBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if local_login_allowed(): return super().authenticate(request,username,password,**kwargs)
    def user_can_authenticate(self,user):
        return super().user_can_authenticate(user) and local_login_allowed()

class SSOBackend(AuthenticationBackend):
    # Password authentication is intentionally unavailable through allauth too.
    def authenticate(self, request, **credentials): return None
    def user_can_authenticate(self,user):
        try: corporate_email(user.email)
        except ValidationError: return False
        return user.is_active

class ClosedAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self,request): return False

class CorporateSocialAdapter(DefaultSocialAccountAdapter):
    def reject(self):
        raise ImmediateHttpResponse(HttpResponseForbidden('เข้าใช้งานได้เฉพาะพนักงาน @askme.co.th ใน Microsoft tenant ที่บริษัทกำหนด กรุณาติดต่อผู้ดูแลระบบ'))

    def pre_social_login(self,request,sociallogin):
        if sociallogin.state.get('process') == 'connect': self.reject()
        claims=sociallogin.account.extra_data.get('id_token',{})
        tenant=settings.MICROSOFT_TENANT_ID.casefold()
        issuer=f'https://login.microsoftonline.com/{tenant}/v2.0'
        if not settings.MICROSOFT_SSO_READY or sociallogin.account.provider!='microsoft': self.reject()
        if str(claims.get('tid','')).casefold()!=tenant or claims.get('iss','').casefold()!=issuer: self.reject()
        try: object_id=str(uuid.UUID(claims.get('oid','')))
        except (ValueError,TypeError,AttributeError): self.reject()
        if sociallogin.account.uid.casefold()!=object_id: self.reject()
        if claims.get('acct') in [1,'1']: self.reject()
        identity_provider=claims.get('idp','').casefold()
        if identity_provider and identity_provider not in [issuer,f'https://sts.windows.net/{tenant}/']: self.reject()
        try: email=corporate_email(claims.get('preferred_username'))
        except ValidationError: self.reject()
        sociallogin.user.email=email
        sociallogin.email_addresses=[EmailAddress(email=email,verified=True,primary=True)]
        # Only connect a pre-provisioned account after validating the tenant and signed identity.
        existing=User.objects.filter(email__iexact=email).first()
        if sociallogin.is_existing:
            if not existing or existing.pk!=sociallogin.user.pk or not existing.is_active: self.reject()
        elif existing:
            if not existing.is_active: self.reject()
            sociallogin.connect(request,existing)

    def is_open_for_signup(self,request,sociallogin): return settings.MICROSOFT_SSO_READY

    def save_user(self,request,sociallogin,form=None):
        sociallogin.user.email=corporate_email(sociallogin.user.email)
        sociallogin.user.role=User.Role.ENGINEER
        sociallogin.user.team=Team.objects.get_or_create(name='Sales & Engineering')[0]
        user=super().save_user(request,sociallogin,form)
        Activity.objects.create(actor=user,summary=f'สร้างบัญชีจาก Microsoft 365 SSO: {user.email} (Engineer; Admin เปลี่ยนบทบาทได้)')
        return user
