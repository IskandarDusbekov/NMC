from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import AuditLog
from .services import AuditLogService


User = get_user_model()


class AuditLogServiceTest(TestCase):
    def test_log_is_created(self):
        user = User.objects.create_user(
            username='admin',
            password='test12345',
            full_name='Admin User',
            role='ADMIN',
        )
        AuditLogService.log(user=user, action='created', model_name='Transaction', object_id='1')
        self.assertEqual(AuditLog.objects.count(), 1)
