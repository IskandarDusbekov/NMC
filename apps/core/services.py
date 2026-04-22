from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.urls import NoReverseMatch, reverse


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
            NavigationItem('Sozlamalar', 'admin:index', '/admin/', ('ADMIN',), False, 'settings'),
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
