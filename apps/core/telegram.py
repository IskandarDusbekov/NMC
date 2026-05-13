"""
Telegram bot notification service.

Sozlash (.env):
    TELEGRAM_BOT_TOKEN=123456:ABC-xyz
    TELEGRAM_NOTIFY_CHAT_IDS=123456789,987654321   # Director/Admin chat IDlar

Ishlatish:
    from apps.core.telegram import TelegramNotificationService
    TelegramNotificationService.notify_expense(amount=5_000_000, currency='UZS', ...)
"""
from __future__ import annotations

import json
import logging
import threading
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    _BASE_URL = 'https://api.telegram.org/bot{token}/sendMessage'

    # ── public helpers ──────────────────────────────────────────────────────

    @classmethod
    def notify_expense(
        cls,
        *,
        amount,
        currency: str,
        category_name: str = '',
        manager_name: str = '',
        object_name: str = '',
        description: str = '',
        entry_type_label: str = 'Xarajat',
    ) -> None:
        """Manager xarajati kiritilganda directorga xabar yuboradi."""
        lines = [f'📌 <b>Yangi {entry_type_label}</b>']
        lines.append(f'💰 <b>{cls._fmt(amount)} {currency}</b>')
        if category_name:
            lines.append(f'🏷 Kategoriya: {category_name}')
        if manager_name:
            lines.append(f'👤 Manager: {manager_name}')
        if object_name:
            lines.append(f'🏗 Obyekt: {object_name}')
        if description:
            lines.append(f'📝 {description[:120]}')
        cls._send_async('\n'.join(lines))

    @classmethod
    def notify_transfer(
        cls,
        *,
        amount,
        currency: str,
        to_manager_name: str = '',
        description: str = '',
        kind_label: str = 'Transfer',
    ) -> None:
        """Manager ga pul berilganda xabar."""
        lines = [f'💸 <b>{kind_label}</b>']
        lines.append(f'💰 <b>{cls._fmt(amount)} {currency}</b>')
        if to_manager_name:
            lines.append(f'👤 Kimga: {to_manager_name}')
        if description:
            lines.append(f'📝 {description[:100]}')
        cls._send_async('\n'.join(lines))

    @classmethod
    def notify_company_action(
        cls,
        *,
        amount,
        currency: str,
        action_label: str,
        category_name: str = '',
        description: str = '',
    ) -> None:
        """Ferma hisobidan kirim/chiqim kiritilganda."""
        lines = [f'🏦 <b>Ferma: {action_label}</b>']
        lines.append(f'💰 <b>{cls._fmt(amount)} {currency}</b>')
        if category_name:
            lines.append(f'🏷 {category_name}')
        if description:
            lines.append(f'📝 {description[:100]}')
        cls._send_async('\n'.join(lines))

    # ── internal ────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt(amount) -> str:
        try:
            return f'{float(amount):,.0f}'.replace(',', ' ')
        except (TypeError, ValueError):
            return str(amount)

    @classmethod
    def _get_config(cls) -> tuple[str, list[str]]:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''
        chat_ids = getattr(settings, 'TELEGRAM_NOTIFY_CHAT_IDS', []) or []
        if isinstance(chat_ids, str):
            chat_ids = [c.strip() for c in chat_ids.split(',') if c.strip()]
        return token, chat_ids

    @classmethod
    def _send_async(cls, text: str) -> None:
        """Fire-and-forget: fon threadda yuboradi, request ni sekinlashtirmaydi."""
        token, chat_ids = cls._get_config()
        if not token or not chat_ids:
            return
        thread = threading.Thread(
            target=cls._send_all,
            args=(token, chat_ids, text),
            daemon=True,
        )
        thread.start()

    @classmethod
    def _send_all(cls, token: str, chat_ids: list[str], text: str) -> None:
        url = cls._BASE_URL.format(token=token)
        for chat_id in chat_ids:
            try:
                payload = json.dumps({
                    'chat_id': chat_id,
                    'text': text,
                    'parse_mode': 'HTML',
                }).encode()
                req = Request(url, data=payload, headers={'Content-Type': 'application/json'})
                with urlopen(req, timeout=8) as resp:
                    resp.read()
            except (URLError, OSError, Exception) as exc:
                logger.warning('Telegram notification failed (chat_id=%s): %s', chat_id, exc)
