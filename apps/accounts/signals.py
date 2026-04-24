from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .security import SecurityService
from .models import User


@receiver(post_save, sender=User)
def ensure_manager_account(sender, instance, created, **kwargs):
    if instance.role != User.Role.MANAGER:
        return
    from apps.finance.models import ManagerAccount

    ManagerAccount.objects.get_or_create(user=instance)


@receiver(user_login_failed)
def capture_login_failure(sender, credentials, request, **kwargs):
    if request is None:
        return
    username = ''
    if isinstance(credentials, dict):
        username = credentials.get('username', '') or credentials.get('email', '')
    SecurityService.register_admin_login_failure(request, username=username)


@receiver(user_logged_in)
def capture_login_success(sender, request, user, **kwargs):
    if request is None:
        return
    SecurityService.register_admin_login_success(request, user)
