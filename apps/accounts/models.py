from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        DIRECTOR = 'DIRECTOR', 'Director'
        MANAGER = 'MANAGER', 'Manager'

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MANAGER)
    telegram_id = models.BigIntegerField(unique=True, blank=True, null=True)
    telegram_username = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.username


class AccessToken(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='access_tokens')
    token = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.user} - {self.expires_at}'


class TelegramLoginSession(TimeStampedModel):
    class State(models.TextChoices):
        NEW = 'NEW', 'New'
        WAITING_CONTACT = 'WAITING_CONTACT', 'Waiting contact'
        LINKED = 'LINKED', 'Linked'
        ACCESS_SENT = 'ACCESS_SENT', 'Access sent'
        BLOCKED = 'BLOCKED', 'Blocked'
        ERROR = 'ERROR', 'Error'

    telegram_id = models.BigIntegerField(unique=True)
    chat_id = models.BigIntegerField(blank=True, null=True)
    telegram_username = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    user = models.ForeignKey(
        'accounts.User',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='telegram_login_sessions',
    )
    state = models.CharField(max_length=32, choices=State.choices, default=State.NEW)
    last_error = models.TextField(blank=True)
    last_interaction_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('-last_interaction_at', '-created_at')

    def __str__(self):
        return f'{self.telegram_id} - {self.state}'


class TelegramBotState(TimeStampedModel):
    name = models.CharField(max_length=64, unique=True, default='default')
    last_update_id = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Telegram bot state'
        verbose_name_plural = 'Telegram bot states'

    def __str__(self):
        return f'{self.name}: {self.last_update_id}'
