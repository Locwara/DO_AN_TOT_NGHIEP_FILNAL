from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profiles, TeacherRegistrations
from apps.administation.models import ActivityLogs


class UserBulkActionSafetyTests(TestCase):
    def setUp(self):
        self.role_admin = User.objects.create_user(
            username='roleadmin',
            password='pass12345',
            is_staff=True,
        )
        Profiles.objects.create(id=self.role_admin, role='admin', status='approved')

        self.superuser = User.objects.create_superuser(
            username='root',
            email='root@example.com',
            password='pass12345',
        )
        Profiles.objects.create(id=self.superuser, role='admin', status='approved')

        self.student = User.objects.create_user(username='student', password='pass12345')
        Profiles.objects.create(id=self.student, role='student', status='approved')

        self.client.force_login(self.role_admin)

    def test_admin_cannot_deactivate_own_account(self):
        response = self.client.post(
            reverse('administation:user_bulk_action'),
            {'action': 'deactivate', 'user_ids': [str(self.role_admin.pk)]},
        )

        self.role_admin.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.role_admin.is_active)

    def test_admin_cannot_deactivate_last_active_superuser(self):
        response = self.client.post(
            reverse('administation:user_bulk_action'),
            {'action': 'deactivate', 'user_ids': [str(self.superuser.pk)]},
        )

        self.superuser.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.superuser.is_active)

    def test_admin_can_deactivate_regular_user(self):
        response = self.client.post(
            reverse('administation:user_bulk_action'),
            {'action': 'deactivate', 'user_ids': [str(self.student.pk)]},
        )

        self.student.refresh_from_db()
        self.student.profiles.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.student.is_active)
        self.assertEqual(self.student.profiles.status, 'inactive')

    def test_admin_role_change_creates_activity_log(self):
        response = self.client.post(
            reverse('administation:user_edit', kwargs={'pk': self.student.pk}),
            {
                'username': self.student.username,
                'email': 'student@example.com',
                'first_name': 'Student',
                'last_name': 'One',
                'role': 'teacher',
                'is_active': 'on',
                'password': '',
            },
        )

        self.student.profiles.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.student.profiles.role, 'teacher')
        log = ActivityLogs.objects.get(
            action='ADMIN_ROLE_CHANGE',
            resource_type='accounts',
            resource_id=self.student.pk,
        )
        self.assertEqual(log.metadata['old_role'], 'student')
        self.assertEqual(log.metadata['new_role'], 'teacher')

    def test_approve_teacher_updates_profile_status(self):
        applicant = User.objects.create_user(username='teacherapp', password='pass12345')
        Profiles.objects.create(id=applicant, role='student', status='pending')
        registration = TeacherRegistrations.objects.create(
            user=applicant,
            institution='Test School',
            reason='I teach programming.',
        )

        response = self.client.post(
            reverse('administation:approve_teacher', kwargs={'pk': registration.pk})
        )

        applicant.profiles.refresh_from_db()
        registration.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(registration.status, 'approved')
        self.assertEqual(applicant.profiles.role, 'teacher')
        self.assertEqual(applicant.profiles.status, 'approved')

    def test_admin_monitor_pages_render(self):
        for route_name in (
            'administation:system_settings',
            'administation:setting_create',
            'administation:metrics',
            'administation:exam_events',
        ):
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200, route_name)

    def test_superuser_without_profile_can_access_admin_dashboard(self):
        superuser_without_profile = User.objects.create_superuser(
            username='noprofile-root',
            email='noprofile@example.com',
            password='pass12345',
        )
        self.client.force_login(superuser_without_profile)

        response = self.client.get(reverse('administation:dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_activity_logs_export_has_utf8_bom_and_filters(self):
        ActivityLogs.objects.create(
            user=self.student,
            action='POST /submissions/submit/1/',
            resource_type='submissions',
            resource_id=1,
            ip_address='127.0.0.1',
            metadata={'status_code': 200},
        )
        ActivityLogs.objects.create(
            user=self.role_admin,
            action='POST /administration/users/bulk/',
            resource_type='administation',
            resource_id=2,
            ip_address='127.0.0.1',
            metadata={'status_code': 302},
        )

        response = self.client.get(
            reverse('administation:activity_logs_export'),
            {'user': 'student', 'action': 'submit'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith('\ufeff'.encode('utf-8')))
        body = response.content.decode('utf-8-sig')
        self.assertIn('student', body)
        self.assertIn('POST /submissions/submit/1/', body)
        self.assertNotIn('roleadmin', body)

    def test_admin_csv_exports_have_utf8_bom(self):
        for route_name in (
            'administation:user_export',
            'administation:classroom_export',
            'administation:subject_export',
            'administation:activity_logs_export',
        ):
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200, route_name)
            self.assertTrue(response.content.startswith('\ufeff'.encode('utf-8')), route_name)
