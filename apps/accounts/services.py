from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from urllib.parse import parse_qsl

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from config.settings.env import env

from .models import AccessToken, User


class UserAccessService:
    @staticmethod
    def is_director_or_admin(user) -> bool:
        return bool(user.is_authenticated and (user.is_superuser or user.role in {'ADMIN', 'DIRECTOR'}))


class TokenService:
    @staticmethod
    def invalidate_tokens(user):
        AccessToken.objects.filter(user=user, is_used=False, expires_at__gt=timezone.now()).update(is_used=True, used_at=timezone.now())

    @classmethod
    def create_access_token(cls, user, lifetime_minutes=5):
        cls.invalidate_tokens(user)
        return AccessToken.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(minutes=lifetime_minutes),
        )

    @staticmethod
    @transaction.atomic
    def consume_token(raw_token: str):
        try:
            access_token = AccessToken.objects.select_for_update().select_related('user').get(token=raw_token)
        except AccessToken.DoesNotExist as exc:
            raise ValidationError('Token topilmadi.') from exc

        now = timezone.now()
        if access_token.is_used:
            raise ValidationError('Token allaqachon ishlatilgan.')
        if access_token.expires_at <= now:
            access_token.is_used = True
            access_token.used_at = now
            access_token.save(update_fields=['is_used', 'used_at', 'updated_at'])
            raise ValidationError('Token muddati tugagan.')

        access_token.is_used = True
        access_token.used_at = now
        access_token.save(update_fields=['is_used', 'used_at', 'updated_at'])
        user = access_token.user
        user._consumed_access_token_id = access_token.pk
        return user


class TelegramAuthService:
    @staticmethod
    def get_active_user_by_telegram_id(telegram_id):
        try:
            return User.objects.get(telegram_id=telegram_id, is_active=True)
        except User.DoesNotExist as exc:
            raise ValidationError('Bu Telegram akkaunti tizimga biriktirilmagan.') from exc

    @staticmethod
    def _bot_token():
        token = env('TELEGRAM_BOT_TOKEN', '')
        if not token:
            raise ValidationError('TELEGRAM_BOT_TOKEN sozlanmagan.')
        return token

    @staticmethod
    def parse_init_data(init_data: str):
        if not init_data:
            raise ValidationError('Telegram initData yuborilmadi.')
        return dict(parse_qsl(init_data, keep_blank_values=True))

    @classmethod
    def verify_init_data(cls, init_data: str):
        data = cls.parse_init_data(init_data)
        received_hash = data.pop('hash', None)
        if not received_hash:
            raise ValidationError('Hash yuborilmadi.')

        auth_date = int(data.get('auth_date', '0') or '0')
        max_age = int(env('TELEGRAM_AUTH_MAX_AGE', '300') or '300')
        if not auth_date or timezone.now().timestamp() - auth_date > max_age:
            raise ValidationError('Telegram auth muddati tugagan.')

        data_check_string = '\n'.join(f'{key}={value}' for key, value in sorted(data.items()))
        secret_key = hmac.new(b'WebAppData', cls._bot_token().encode('utf-8'), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated_hash, received_hash):
            raise ValidationError('Telegram initData hash noto`g`ri.')
        return data

    @classmethod
    def authenticate_from_init_data(cls, init_data: str):
        payload = cls.verify_init_data(init_data)
        telegram_id = payload.get('user')
        if telegram_id:
            user_payload = json.loads(telegram_id)
            telegram_id = user_payload.get('id')
            telegram_username = user_payload.get('username', '')
        else:
            telegram_id = payload.get('id')
            telegram_username = payload.get('username', '')
        if not telegram_id:
            raise ValidationError('Telegram user aniqlanmadi.')
        user = cls.get_active_user_by_telegram_id(telegram_id)
        if telegram_username and user.telegram_username != telegram_username:
            user.telegram_username = telegram_username
            user.save(update_fields=['telegram_username'])
        return user
