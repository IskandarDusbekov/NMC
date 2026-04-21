from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def ensure_manager_account(sender, instance, created, **kwargs):
    if instance.role != User.Role.MANAGER:
        return
    from apps.finance.models import ManagerAccount

    ManagerAccount.objects.get_or_create(user=instance)
