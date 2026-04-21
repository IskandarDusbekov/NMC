from django.test import TestCase


class CoreSmokeTest(TestCase):
    def test_truthy(self):
        self.assertTrue(True)
