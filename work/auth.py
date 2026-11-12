import hashlib
from datetime import timedelta
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.utils import timezone
from .models import LoginAttempt
from django.conf import settings
from django.shortcuts import render
from .sso import local_login_allowed

class ThrottledLoginView(LoginView):
    template_name = 'registration/login.html'
    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'local_login_allowed':local_login_allowed(), 'sso_ready':settings.MICROSOFT_SSO_READY}
    def post(self, request, *args, **kwargs):
        if not local_login_allowed(): return HttpResponse('กรุณาเข้าสู่ระบบด้วย Microsoft 365 ของบริษัท',status=403)
        self.ip_hash = hashlib.sha256(request.META.get('REMOTE_ADDR', '').encode()).hexdigest()
        self.key_hash = hashlib.sha256((self.ip_hash + request.POST.get('username', '').casefold()).encode()).hexdigest()
        attempts = LoginAttempt.objects.filter(created_at__gte=timezone.now() - timedelta(minutes=15))
        if attempts.filter(key_hash=self.key_hash).count() >= 5 or attempts.filter(ip_hash=self.ip_hash).count() >= 30:
            return HttpResponse('พยายามเข้าสู่ระบบหลายครั้ง กรุณารอ 15 นาทีแล้วลองใหม่', status=429)
        return super().post(request, *args, **kwargs)
    def form_invalid(self, form):
        LoginAttempt.objects.create(ip_hash=self.ip_hash, key_hash=self.key_hash)
        LoginAttempt.objects.filter(created_at__lt=timezone.now() - timedelta(days=1)).delete()
        return super().form_invalid(form)
    def form_valid(self, form):
        LoginAttempt.objects.filter(key_hash=self.key_hash).delete()
        return super().form_valid(form)
