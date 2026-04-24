from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.logs.models import AuditLog


User = get_user_model()


class CoreSmokeTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin-core',
            password='StrongPass123!',
            full_name='Admin Core',
            role='ADMIN',
        )
        self.director_user = User.objects.create_user(
            username='director-core',
            password='StrongPass123!',
            full_name='Director Core',
            role='DIRECTOR',
        )
        User.objects.filter(pk=self.director_user.pk).update(is_staff=True)
        self.director_user.refresh_from_db()

    def test_truthy(self):
        self.assertTrue(True)

    def test_legacy_admin_path_is_hidden(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 404)

    def test_admin_reverse_uses_custom_admin_path(self):
        self.assertEqual(reverse('admin:index'), f"/{settings.ADMIN_URL_PATH}")

    def test_json_backup_requires_superuser(self):
        self.client.force_login(self.director_user)
        response = self.client.get(reverse('admin-backup-json'))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(AuditLog.objects.filter(action='security_backup_download_denied').exists())

    def test_json_backup_allows_superuser(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin-backup-json'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action='backup_json_downloaded').exists())
