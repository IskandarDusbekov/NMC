from django.contrib.auth import get_user_model


User = get_user_model()


def active_users():
    return User.objects.filter(is_active=True).order_by('full_name')


def active_managers():
    return User.objects.filter(is_active=True, role=User.Role.MANAGER).order_by('full_name')
