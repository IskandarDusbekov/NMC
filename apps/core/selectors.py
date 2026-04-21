from __future__ import annotations

from typing import Any


def current_user_role(user: Any) -> str:
    if getattr(user, 'is_superuser', False):
        return 'ADMIN'
    return getattr(user, 'role', '')
