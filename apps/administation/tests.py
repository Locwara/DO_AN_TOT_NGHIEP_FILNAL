from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profiles, TeacherRegistrations
from apps.administation.forms import SystemSettingForm
from apps.administation.models import ActivityLogs, SystemSettings
from apps.assignments.forms import AssignmentForm
from apps.assignments.models import Assignments
from apps.classrooms.models import Classrooms


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

    def test_assignment_v2_system_settings_drive_defaults(self):
        SystemSettings.objects.create(
            setting_key='uploads.submission_allowed_extensions',
            setting_value=['.pdf', '.py'],
            updated_by=self.role_admin,
        )
        SystemSettings.objects.create(
            setting_key='uploads.submission_default_max_mb',
            setting_value=12,
            updated_by=self.role_admin,
        )
        SystemSettings.objects.create(
            setting_key='uploads.submission_default_max_files',
            setting_value=3,
            updated_by=self.role_admin,
        )
        SystemSettings.objects.create(
            setting_key='uploads.submission_scan_required_default',
            setting_value=True,
            updated_by=self.role_admin,
        )
        SystemSettings.objects.create(
            setting_key='quiz.default_max_attempts',
            setting_value=4,
            updated_by=self.role_admin,
        )
        SystemSettings.objects.create(
            setting_key='quiz.random_choices_default',
            setting_value=True,
            updated_by=self.role_admin,
        )

        file_form = AssignmentForm(initial={'submission_mode': Assignments.SUBMISSION_FILE})
        self.assertEqual(file_form.initial['file_allowed_extensions'], ['.pdf', '.py'])
        self.assertEqual(file_form.initial['file_max_size_mb'], 12)
        self.assertEqual(file_form.initial['file_max_files'], 3)
        self.assertTrue(file_form.initial['file_scan_required'])

        quiz_form = AssignmentForm(data={
            'title': 'Quiz defaults',
            'description': 'Mo ta',
            'instructions': 'Lam quiz',
            'submission_mode': Assignments.SUBMISSION_QUIZ,
            'grading_mode': Assignments.GRADING_AUTO,
            'type': 'auto_grade',
            'difficulty': 'easy',
            'late_penalty_percent': '0',
            'max_score': '100',
            'show_testcase_result': '',
            'exam_grace_seconds': '30',
            'classroom_subject': '',
            'quiz_random_choices': 'on',
            'quiz_show_score_after_submit': 'on',
            'quiz_allow_review': 'on',
        })
        self.assertTrue(quiz_form.is_valid(), quiz_form.errors)
        self.assertEqual(quiz_form.cleaned_data['max_attempts'], 4)

    def test_system_setting_form_accepts_upload_extension_array(self):
        form = SystemSettingForm(data={
            'setting_key': 'uploads.submission_allowed_extensions',
            'setting_value': '[".pdf", ".docx", ".py"]',
            'description': 'Default extensions',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['setting_value'], ['.pdf', '.docx', '.py'])

    def test_upload_and_quiz_policy_setting_changes_are_audited(self):
        quiz_response = self.client.post(
            reverse('administation:setting_create'),
            {
                'setting_key': 'quiz.random_questions_default',
                'setting_value': 'true',
                'description': 'Random quiz questions',
            },
        )
        upload_response = self.client.post(
            reverse('administation:setting_create'),
            {
                'setting_key': 'uploads.submission_default_max_files',
                'setting_value': '3',
                'description': 'Default file count',
            },
        )

        self.assertEqual(quiz_response.status_code, 302)
        self.assertEqual(upload_response.status_code, 302)
        quiz_log = ActivityLogs.objects.get(
            action='ADMIN_POLICY_SETTING_CREATE',
            metadata__policy_category='quiz',
        )
        upload_log = ActivityLogs.objects.get(
            action='ADMIN_POLICY_SETTING_CREATE',
            metadata__policy_category='uploads',
        )
        self.assertTrue(quiz_log.metadata['is_upload_or_quiz_policy'])
        self.assertTrue(upload_log.metadata['is_upload_or_quiz_policy'])

    def test_admin_can_hide_and_publish_assignment(self):
        teacher = User.objects.create_user(username='teacher2', password='pass12345')
        Profiles.objects.create(id=teacher, role='teacher', status='approved')
        classroom = Classrooms.objects.create(
            name='Audit class',
            invite_code='AUDIT123',
            teacher=teacher,
            status='approved',
            is_active=True,
        )
        assignment = Assignments.objects.create(
            classroom=classroom,
            title='File exam audit',
            submission_mode=Assignments.SUBMISSION_FILE,
            is_exam=True,
            is_published=True,
            created_by=teacher,
        )

        hide = self.client.post(
            reverse('administation:assignment_visibility_toggle', kwargs={'pk': assignment.pk}),
            {'action': 'hide'},
        )
        assignment.refresh_from_db()
        self.assertEqual(hide.status_code, 302)
        self.assertFalse(assignment.is_published)
        self.assertTrue(ActivityLogs.objects.filter(action='ADMIN_ASSIGNMENT_HIDE', resource_id=assignment.pk).exists())

        publish = self.client.post(
            reverse('administation:assignment_visibility_toggle', kwargs={'pk': assignment.pk}),
            {'action': 'publish'},
        )
        assignment.refresh_from_db()
        self.assertEqual(publish.status_code, 302)
        self.assertTrue(assignment.is_published)

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
