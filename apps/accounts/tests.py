from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import Profiles


class LoginSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='pass12345')
        Profiles.objects.create(id=self.user, role='student', status='approved')

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            '/accounts/login/?next=https://evil.example/phish',
            {'username': 'student', 'password': 'pass12345'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.headers['Location'].startswith('https://evil.example'))

    def test_login_accepts_safe_relative_next_url(self):
        response = self.client.post(
            '/accounts/login/?next=/classrooms/',
            {'username': 'student', 'password': 'pass12345'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/classrooms/')
