import unittest

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profiles
from apps.classrooms.models import Classrooms
from apps.assignments.models import Assignments, Testcases
from apps.assignments.forms import AssignmentForm, TestcaseImportForm
from apps.assignments.views import _parse_testcases_csv, _parse_testcases_json


class AssignmentFormTemplateTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='pass12345')
        Profiles.objects.create(id=self.teacher, role='teacher', status='approved')
        self.classroom = Classrooms.objects.create(
            name='Lop Python',
            invite_code='PY1234',
            teacher=self.teacher,
            status='approved',
            is_active=True,
        )
        self.client.force_login(self.teacher)

    def test_create_assignment_page_uses_shared_form_and_renders_exam_controls(self):
        response = self.client.get(reverse('assignments:create', kwargs={'classroom_pk': self.classroom.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'assignments/_assignment_form.html')
        self.assertContains(response, 'id="exam-toggle"')
        self.assertContains(response, 'aria-controls="exam-section"')

    def test_assignment_form_rejects_invalid_scoring_attempts_and_exam_policy(self):
        form = AssignmentForm(data={
            'title': 'Bai thi',
            'description': 'Mo ta',
            'instructions': 'Lam bai',
            'type': 'auto_grade',
            'difficulty': 'easy',
            'late_submission_allowed': 'on',
            'late_penalty_percent': '120',
            'max_score': '0',
            'max_attempts': '0',
            'show_testcase_result': 'on',
            'enable_leaderboard': '',
            'is_exam': 'on',
            'exam_duration_minutes': '0',
            'exam_max_run_count': '0',
            'exam_grace_seconds': '-1',
            'classroom_subject': '',
        }, classroom=self.classroom)

        self.assertFalse(form.is_valid())
        self.assertIn('max_score', form.errors)
        self.assertIn('max_attempts', form.errors)
        self.assertIn('late_penalty_percent', form.errors)
        self.assertIn('exam_duration_minutes', form.errors)
        self.assertIn('exam_max_run_count', form.errors)
        self.assertIn('exam_grace_seconds', form.errors)

    def test_testcase_import_validates_file_size_and_schema(self):
        large_file = SimpleUploadedFile('tests.json', b'0' * (1024 * 1024 + 1))
        form = TestcaseImportForm(data={'import_format': 'json'}, files={'file': large_file})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

        with self.assertRaisesMessage(ValueError, 'expected_output'):
            _parse_testcases_json('[{"name": "T1", "input": "1"}]')
        with self.assertRaisesMessage(ValueError, 'CSV thiếu cột'):
            _parse_testcases_csv('name,input\nT1,1\n')

    @unittest.skipIf(
        connection.vendor == 'sqlite',
        'Assignment publish preflight touches PostgreSQL ArrayField-backed model.',
    )
    def test_assignment_publish_preflight_requires_ready_auto_grade_assignment(self):
        assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Bai chua san sang',
            type='auto_grade',
            is_published=False,
            created_by=self.teacher,
        )

        response = self.client.post(reverse('assignments:toggle_publish', kwargs={'pk': assignment.pk}))
        assignment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(assignment.is_published)

        assignment.description = 'Mo ta bai tap'
        assignment.instructions = 'In hello'
        assignment.save(update_fields=['description', 'instructions'])
        Testcases.objects.create(
            assignment=assignment,
            name='Sample',
            input_data='',
            expected_output='hello',
            is_sample=True,
            is_hidden=False,
            weight=1,
        )

        response = self.client.post(reverse('assignments:toggle_publish', kwargs={'pk': assignment.pk}))
        assignment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(assignment.is_published)
