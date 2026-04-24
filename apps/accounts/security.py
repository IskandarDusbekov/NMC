from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.logs.models import AuditLog
from apps.logs.models import BlockedIP
from apps.logs.services import AuditLogService


class SecurityService:
    @staticmethod
    def _ip(request):
        return AuditLogService.get_ip_address(request)

    @staticmethod
    def _is_admin_login_request(request) -> bool:
        admin_login_path = f'/{settings.ADMIN_URL_PATH}login/'
        return request.path == admin_login_path

    @classmethod
    def active_block_for_request(cls, request):
        ip_address = cls._ip(request)
        if not ip_address:
            return None
        return BlockedIP.objects.filter(
            ip_address=ip_address,
            blocked_until__isnull=False,
            blocked_until__gt=timezone.now(),
        ).first()

    @classmethod
    def register_admin_login_failure(cls, request, username=''):
        if not cls._is_admin_login_request(request):
            return
        ip_address = cls._ip(request)
        if not ip_address:
            return

        now = timezone.now()
        window_seconds = getattr(settings, 'ADMIN_LOGIN_FAILURE_WINDOW_SECONDS', 900)
        limit = getattr(settings, 'ADMIN_LOGIN_FAILURE_LIMIT', 5)
        block_seconds = getattr(settings, 'BLOCKED_IP_TTL_SECONDS', 3600)

        blocked_ip, _ = BlockedIP.objects.get_or_create(ip_address=ip_address)
        if not blocked_ip.window_started_at or (now - blocked_ip.window_started_at).total_seconds() > window_seconds:
            blocked_ip.failed_attempts = 0
            blocked_ip.window_started_at = now

        blocked_ip.failed_attempts += 1
        blocked_ip.last_attempt_at = now
        blocked_ip.reason = 'Admin login xato urinishlari'
        should_block = blocked_ip.failed_attempts >= limit
        if should_block:
            blocked_ip.blocked_until = now + timedelta(seconds=block_seconds)
        blocked_ip.save()

        AuditLogService.log_from_request(
            request,
            user=None,
            action='security_admin_login_failed',
            model_name='AdminLogin',
            object_id=username[:64],
            description=f'Admin login xato urinish. Username: {username or "-"}; urinishlar: {blocked_ip.failed_attempts}.',
        )
        if should_block:
            AuditLogService.log_from_request(
                request,
                user=None,
                action='security_ip_blocked',
                model_name='BlockedIP',
                object_id=ip_address,
                description=f'IP vaqtincha bloklandi. Sabab: admin login xato urinishlari. Blok muddati: {blocked_ip.blocked_until}.',
            )

    @classmethod
    def register_admin_login_success(cls, request, user):
        if not cls._is_admin_login_request(request):
            return
        ip_address = cls._ip(request)
        if not ip_address:
            return
        now = timezone.now()
        BlockedIP.objects.update_or_create(
            ip_address=ip_address,
            defaults={
                'failed_attempts': 0,
                'blocked_until': None,
                'reason': '',
                'window_started_at': now,
                'last_attempt_at': now,
            },
        )
        cls.log_new_ip_if_needed(request, user)
        AuditLogService.log_from_request(
            request,
            user=user,
            action='security_admin_login_success',
            model_name='AdminLogin',
            object_id=str(user.pk),
            description=f'{user} admin panelga muvaffaqiyatli kirdi.',
        )

    @classmethod
    def log_new_ip_if_needed(cls, request, user, action='security_new_ip_login'):
        ip_address = cls._ip(request)
        if not ip_address or not user:
            return

        has_previous_ip = AuditLog.objects.filter(
            user=user,
            ip_address=ip_address,
            action__in={
                'security_admin_login_success',
                'telegram_token_login',
                'telegram_mini_app_login',
                'security_new_ip_login',
            },
        ).exists()
        if not has_previous_ip:
            AuditLogService.log_from_request(
                request,
                user=user,
                action=action,
                model_name='User',
                object_id=str(user.pk),
                description=f'{user} tizimga yangi IP manzildan kirdi: {ip_address}.',
            )
