from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .services import AuditLogService


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    AuditLogService.log_from_request(
        request,
        user=user,
        action='login',
        model_name='User',
        object_id=str(user.pk),
        description=f'{user} tizimga kirdi.',
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user is None:
        return
    AuditLogService.log_from_request(
        request,
        user=user,
        action='logout',
        model_name='User',
        object_id=str(user.pk),
        description=f'{user} tizimdan chiqdi.',
    )
