from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class ReportPermissionTest(TestCase):
    def test_manager_cannot_access_reports(self):
        user = User.objects.create_user(
            username='manager-report',
            password='test12345',
            full_name='Manager Report',
            role='MANAGER',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('reports:index'))
        self.assertEqual(response.status_code, 403)
