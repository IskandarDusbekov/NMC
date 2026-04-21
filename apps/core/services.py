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
            NavigationItem('Dashboard', 'dashboard:index', '/dashboard/', ('ADMIN', 'DIRECTOR', 'MANAGER'), True),
            NavigationItem('Obyektlar', 'objects:list', '/objects/', ('ADMIN', 'DIRECTOR', 'MANAGER'), True),
            NavigationItem('Ish turlari', 'objects:work-item-list', '/work-items/', ('ADMIN', 'DIRECTOR', 'MANAGER')),
            NavigationItem('Kompaniya moliyasi', 'finance:transaction-list', '/finance/', ('ADMIN', 'DIRECTOR', 'MANAGER'), True),
            NavigationItem('Manager hisoblari', 'finance:manager-account-list', '/finance/manager-accounts/', ('ADMIN', 'DIRECTOR', 'MANAGER')),
            NavigationItem('Ishchilar', 'workforce:worker-list', '/workers/', ('ADMIN', 'DIRECTOR', 'MANAGER'), True),
            NavigationItem('Ish haqi', 'workforce:salary-payment-list', '/salary-payments/', ('ADMIN', 'DIRECTOR', 'MANAGER')),
            NavigationItem('Hisobotlar', 'reports:index', '/reports/', ('ADMIN', 'DIRECTOR')),
            NavigationItem('Loglar', 'logs:index', '/logs/', ('ADMIN', 'DIRECTOR')),
            NavigationItem('Sozlamalar', 'admin:index', '/admin/', ('ADMIN',)),
        ]

    @classmethod
    def build_navigation(cls, user: Any) -> list[dict[str, Any]]:
        if not getattr(user, 'is_authenticated', False):
            return []

        user_role = 'ADMIN' if getattr(user, 'is_superuser', False) else getattr(user, 'role', '')
        items = []
        for item in cls.base_items():
            if user_role in item.roles:
                label = item.label
                if item.url_name == 'finance:manager-account-list' and user_role == 'MANAGER':
                    label = 'Mening hisobim'
                items.append(
                    {
                        'label': label,
                        'url': item.url,
                        'prefix': item.prefix,
                        'mobile': item.mobile,
                    }
                )
        return items
