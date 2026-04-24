from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import models
from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone


@dataclass
class NavigationItem:
    label: str
    url_name: str
    prefix: str
    roles: tuple[str, ...]
    mobile: bool = False
    icon: str = 'circle'

    @property
    def url(self) -> str:
        try:
            return reverse(self.url_name)
        except NoReverseMatch:
            return '#'


class NavigationService:
    @staticmethod
    def base_items() -> list[NavigationItem]:
        return [
            NavigationItem('Dashboard', 'dashboard:index', '/dashboard/', ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER'), True, 'dashboard'),
            NavigationItem('Obyektlar', 'objects:list', '/objects/', ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER'), True, 'building'),
            NavigationItem('Ish turlari', 'objects:work-item-list', '/work-items/', ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER'), False, 'tasks'),
            NavigationItem('Ferma moliyasi', 'finance:transaction-list', '/finance/', ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER'), True, 'wallet'),
            NavigationItem('Manager hisoblari', 'finance:manager-account-list', '/finance/manager-accounts/', ('ADMIN', 'DIRECTOR'), False, 'manager'),
            NavigationItem('Ishchilar', 'workforce:worker-list', '/workers/', ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER'), True, 'users'),
            NavigationItem('Ish haqi', 'workforce:salary-payment-list', '/salary-payments/', ('ADMIN', 'DIRECTOR', 'OBSERVER'), False, 'salary'),
            NavigationItem('Hisobotlar', 'reports:index', '/reports/', ('ADMIN', 'DIRECTOR', 'OBSERVER'), False, 'reports'),
            NavigationItem('Loglar', 'logs:index', '/logs/', ('ADMIN', 'DIRECTOR', 'OBSERVER'), False, 'logs'),
            NavigationItem('Sozlamalar', 'admin:index', f"/{getattr(settings, 'ADMIN_URL_PATH', 'secure-console/')}", ('ADMIN',), False, 'settings'),
        ]

    @classmethod
    def build_navigation(cls, user: Any) -> list[dict[str, Any]]:
        if not getattr(user, 'is_authenticated', False):
            return []

        user_role = getattr(user, 'role', '')
        items = []
        for item in cls.base_items():
            if user_role in item.roles:
                label = item.label
                if item.url_name == 'finance:transaction-list' and user_role == 'MANAGER':
                    label = 'Mening moliyam'
                items.append(
                    {
                        'label': label,
                        'url': item.url,
                        'prefix': item.prefix,
                        'mobile': item.mobile,
                        'icon': item.icon,
                    }
                )
        return items


class SubmissionGuardService:
    SESSION_KEY = '_submission_guard'
    TTL_SECONDS = 8

    @classmethod
    def _normalize(cls, value: Any):
        if isinstance(value, models.Model):
            return f'{value._meta.label}:{value.pk}'
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if hasattr(value, 'name') and hasattr(value, 'size'):
            return {
                'name': getattr(value, 'name', ''),
                'size': getattr(value, 'size', 0),
                'content_type': getattr(value, 'content_type', ''),
            }
        if isinstance(value, dict):
            return {key: cls._normalize(val) for key, val in sorted(value.items())}
        if isinstance(value, (list, tuple, set)):
            return [cls._normalize(item) for item in value]
        return value

    @classmethod
    def _signature(cls, *, action: str, path: str, user_id: int | None, payload: dict[str, Any]) -> str:
        normalized_payload = cls._normalize(payload)
        return json.dumps(
            {
                'action': action,
                'path': path,
                'user_id': user_id,
                'payload': normalized_payload,
            },
            sort_keys=True,
            ensure_ascii=True,
            default=str,
        )

    @classmethod
    def is_duplicate(cls, request, *, action: str, payload: dict[str, Any]) -> bool:
        if not hasattr(request, 'session'):
            return False
        store = request.session.get(cls.SESSION_KEY, {})
        entry = store.get(action)
        if not entry:
            return False
        signature = cls._signature(
            action=action,
            path=request.path,
            user_id=getattr(request.user, 'pk', None),
            payload=payload,
        )
        if entry.get('signature') != signature:
            return False
        try:
            saved_at = float(entry['saved_at'])
        except (KeyError, TypeError, ValueError):
            return False
        return (timezone.now().timestamp() - saved_at) <= cls.TTL_SECONDS

    @classmethod
    def remember(cls, request, *, action: str, payload: dict[str, Any]) -> None:
        if not hasattr(request, 'session'):
            return
        store = request.session.get(cls.SESSION_KEY, {})
        store[action] = {
            'signature': cls._signature(
                action=action,
                path=request.path,
                user_id=getattr(request.user, 'pk', None),
                payload=payload,
            ),
            'saved_at': timezone.now().timestamp(),
        }
        request.session[cls.SESSION_KEY] = store
        request.session.modified = True
