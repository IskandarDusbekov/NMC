from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class DashboardPermissionTest(TestCase):
    def test_manager_can_open_dashboard(self):
        user = User.objects.create_user(
            username='manager-dashboard',
            password='test12345',
            full_name='Manager Dashboard',
            role='MANAGER',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
