from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Notifications


class NotificationReadStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='pass12345')
        self.client.force_login(self.user)
        self.notification = Notifications.objects.create(
            recipient=self.user,
            title='Bài mới',
            message='Có bài tập mới.',
            link='/notifications/',
        )

    def test_open_notification_does_not_mark_read_with_get(self):
        response = self.client.get(reverse('notifications:open', kwargs={'pk': self.notification.pk}))

        self.notification.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.notification.is_read)
        self.assertIsNone(self.notification.read_at)

    def test_mark_read_requires_post_and_marks_owned_notification(self):
        get_response = self.client.get(reverse('notifications:mark_read', kwargs={'pk': self.notification.pk}))
        self.notification.refresh_from_db()
        self.assertEqual(get_response.status_code, 405)
        self.assertFalse(self.notification.is_read)

        post_response = self.client.post(
            reverse('notifications:mark_read', kwargs={'pk': self.notification.pk}),
            {'next': reverse('notifications:list')},
        )
        self.notification.refresh_from_db()
        self.assertEqual(post_response.status_code, 302)
        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)

    def test_user_cannot_open_or_mark_read_notification_of_another_user(self):
        other = User.objects.create_user(username='other', password='pass12345')
        self.client.force_login(other)

        open_response = self.client.get(reverse('notifications:open', kwargs={'pk': self.notification.pk}))
        mark_response = self.client.post(reverse('notifications:mark_read', kwargs={'pk': self.notification.pk}))

        self.notification.refresh_from_db()
        self.assertEqual(open_response.status_code, 404)
        self.assertEqual(mark_response.status_code, 404)
        self.assertFalse(self.notification.is_read)
