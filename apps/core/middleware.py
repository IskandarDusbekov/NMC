from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils import timezone

from apps.accounts.security import SecurityService
from apps.logs.services import AuditLogService


class SecurityHardeningMiddleware:
    SESSION_KEY = '_last_activity_at'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        blocked_ip = SecurityService.active_block_for_request(request)
        if blocked_ip:
            return HttpResponseForbidden('Ushbu IP manzil vaqtincha bloklangan.')

        if self._should_logout_for_timeout(request):
            AuditLogService.log_from_request(
                request,
                user=request.user,
                action='session_timeout_logout',
                model_name='User',
                object_id=str(request.user.pk),
                description=f'{request.user} harakatsizlik sabab tizimdan chiqarildi.',
            )
            logout(request)
            messages.warning(request, 'Sessiya muddati tugadi. Qayta kiring.')
            return redirect(settings.LOGIN_URL)

        response = self.get_response(request)
        self._touch_session(request)
        return response

    def _should_logout_for_timeout(self, request):
        timeout_seconds = getattr(settings, 'SESSION_TIMEOUT_SECONDS', 0)
        if not timeout_seconds or not getattr(request, 'user', None) or not request.user.is_authenticated:
            return False
        if request.path.startswith('/accounts/access/') or request.path.startswith('/accounts/telegram/'):
            return False

        last_activity = request.session.get(self.SESSION_KEY)
        if last_activity is None:
            return False
        return (timezone.now().timestamp() - float(last_activity)) > timeout_seconds

    def _touch_session(self, request):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            request.session[self.SESSION_KEY] = timezone.now().timestamp()


class AuthenticatedNoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get('Content-Type', '')
        if getattr(request, 'user', None) and request.user.is_authenticated and 'text/html' in content_type:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
