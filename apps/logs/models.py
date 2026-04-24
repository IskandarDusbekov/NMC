from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=150, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        verbose_name = 'Audit log'
        verbose_name_plural = 'Audit loglar'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.action} - {self.model_name}'


class BlockedIP(TimeStampedModel):
    ip_address = models.GenericIPAddressField(unique=True)
    failed_attempts = models.PositiveIntegerField(default=0)
    window_started_at = models.DateTimeField(blank=True, null=True)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    blocked_until = models.DateTimeField(blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Bloklangan IP'
        verbose_name_plural = 'Bloklangan IP lar'
        ordering = ('-blocked_until', '-last_attempt_at')

    def __str__(self):
        return f'{self.ip_address} ({self.blocked_until or "not-blocked"})'
