from __future__ import annotations

from dataclasses import dataclass

from .models import AuditLog


@dataclass
class AuditPayload:
    user: object | None
    action: str
    model_name: str = ''
    object_id: str = ''
    description: str = ''
    ip_address: str | None = None


class AuditLogService:
    @staticmethod
    def get_ip_address(request) -> str | None:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @classmethod
    def log(cls, **kwargs):
        payload = AuditPayload(**kwargs)
        return AuditLog.objects.create(
            user=payload.user,
            action=payload.action,
            model_name=payload.model_name,
            object_id=payload.object_id,
            description=payload.description,
            ip_address=payload.ip_address,
        )

    @classmethod
    def log_from_request(cls, request, **kwargs):
        kwargs.setdefault('user', getattr(request, 'user', None))
        kwargs.setdefault('ip_address', cls.get_ip_address(request))
        return cls.log(**kwargs)
