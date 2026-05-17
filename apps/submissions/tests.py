import json
import unittest
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profiles
from apps.assignments.models import AssignmentStatistics, Assignments, Rubrics
from apps.classrooms.models import ClassroomApprovalStatus, ClassroomMembers, Classrooms
from apps.submissions.models import CodeDrafts, ExamEvents, ExamSessions, RubricScores, Submissions


@unittest.skipIf(
    connection.vendor == 'sqlite',
    'Submission workflow uses PostgreSQL ArrayField; run with PostgreSQL DATABASE_URL.',
)
class SubmissionPermissionTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='pass12345')
        Profiles.objects.create(id=self.teacher, role='teacher', status='approved')

        self.student = User.objects.create_user(username='student', password='pass12345')
        Profiles.objects.create(id=self.student, role='student', status='approved')

        self.other_student = User.objects.create_user(username='otherstudent', password='pass12345')
        Profiles.objects.create(id=self.other_student, role='student', status='approved')

        self.other_teacher = User.objects.create_user(username='otherteacher', password='pass12345')
        Profiles.objects.create(id=self.other_teacher, role='teacher', status='approved')

        self.classroom = Classrooms.objects.create(
            name='Python co ban',
            invite_code='PYT001',
            teacher=self.teacher,
            status=ClassroomApprovalStatus.APPROVED,
            is_active=True,
        )
        ClassroomMembers.objects.create(
            classroom=self.classroom,
            student=self.student,
            status='approved',
        )
        ClassroomMembers.objects.create(
            classroom=self.classroom,
            student=self.other_student,
            status='approved',
        )
        self.assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Bai tap 1',
            description='In hello',
            type='auto_grade',
            is_published=True,
            created_by=self.teacher,
        )
        self.submission = Submissions.objects.create(
            assignment=self.assignment,
            student=self.student,
            code_content='print("hello")',
            language='python',
            status='finished',
            total_score=100,
            max_score=100,
        )

    def test_student_cannot_open_another_students_submission_detail(self):
        self.client.force_login(self.other_student)

        response = self.client.get(
            reverse('submissions:detail', kwargs={'pk': self.submission.pk})
        )

        self.assertEqual(response.status_code, 302)

    def test_student_cannot_open_teacher_grade_view(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse('submissions:grade', kwargs={'pk': self.submission.pk})
        )

        self.assertEqual(response.status_code, 302)

    def test_teacher_cannot_grade_or_control_exam_session_of_another_class(self):
        self.assignment.is_exam = True
        self.assignment.exam_duration_minutes = 30
        self.assignment.save(update_fields=['is_exam', 'exam_duration_minutes'])
        session = ExamSessions.objects.create(
            assignment=self.assignment,
            student=self.student,
            status=ExamSessions.STATUS_RUNNING,
            started_at=timezone.now(),
            ends_at=timezone.now() + timedelta(minutes=30),
            current_language='python',
        )
        self.client.force_login(self.other_teacher)

        grade_response = self.client.post(
            reverse('submissions:grade', kwargs={'pk': self.submission.pk}),
            {'manual_score': '90', 'teacher_comment': 'ok'},
        )
        extend_response = self.client.post(
            reverse('submissions:extend_exam_session', kwargs={'session_pk': session.pk}),
            {'minutes': '10'},
        )
        force_response = self.client.post(
            reverse('submissions:force_submit_exam_session', kwargs={'session_pk': session.pk}),
        )

        session.refresh_from_db()
        self.submission.refresh_from_db()
        self.assertEqual(grade_response.status_code, 302)
        self.assertEqual(extend_response.status_code, 302)
        self.assertEqual(force_response.status_code, 302)
        self.assertIsNone(self.submission.manual_score)
        self.assertEqual(session.extra_time_minutes, 0)
        self.assertIsNone(session.final_submission)

    def test_exam_custom_input_is_blocked_by_policy(self):
        self.assignment.is_exam = True
        self.assignment.exam_duration_minutes = 30
        self.assignment.exam_allow_custom_input = False
        self.assignment.is_published = True
        self.assignment.save(update_fields=[
            'is_exam',
            'exam_duration_minutes',
            'exam_allow_custom_input',
            'is_published',
        ])
        ExamSessions.objects.create(
            assignment=self.assignment,
            student=self.student,
            status=ExamSessions.STATUS_RUNNING,
            started_at=timezone.now(),
            ends_at=timezone.now() + timedelta(minutes=30),
            current_language='python',
        )
        self.client.force_login(self.student)

        response = self.client.post(
            reverse('submissions:run_test', kwargs={'assignment_pk': self.assignment.pk}),
            data=json.dumps({
                'code': 'print(input())',
                'language': 'python',
                'custom_input': 'hello',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('custom input', response.json()['message'])

    def test_save_draft_run_test_submit_permissions_and_language_validation(self):
        self.assignment.allowed_languages = ['python']
        self.assignment.save(update_fields=['allowed_languages'])

        outsider = User.objects.create_user(username='outsider', password='pass12345')
        Profiles.objects.create(id=outsider, role='student', status='approved')

        self.client.force_login(self.student)
        save_response = self.client.post(
            reverse('submissions:save_draft'),
            data=json.dumps({
                'assignment_id': self.assignment.pk,
                'code': 'console.log("hi")',
                'language': 'javascript',
            }),
            content_type='application/json',
        )
        submit_response = self.client.post(
            reverse('submissions:submit', kwargs={'assignment_pk': self.assignment.pk}),
            data=json.dumps({
                'code': 'console.log("hi")',
                'language': 'javascript',
            }),
            content_type='application/json',
        )

        self.client.force_login(outsider)
        run_response = self.client.post(
            reverse('submissions:run_test', kwargs={'assignment_pk': self.assignment.pk}),
            data=json.dumps({
                'code': 'print("hi")',
                'language': 'python',
            }),
            content_type='application/json',
        )

        self.assertEqual(save_response.status_code, 400)
        self.assertEqual(submit_response.status_code, 400)
        self.assertEqual(run_response.status_code, 403)
        self.assertFalse(CodeDrafts.objects.filter(assignment=self.assignment, student=self.student).exists())

    def test_manual_rubric_grade_updates_statistics_gradebook_and_leaderboard(self):
        rubric_a = Rubrics.objects.create(
            assignment=self.assignment,
            name='Dung thuat toan',
            max_points=60,
            order_index=1,
        )
        rubric_b = Rubrics.objects.create(
            assignment=self.assignment,
            name='Trinh bay',
            max_points=40,
            order_index=2,
        )
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('submissions:grade', kwargs={'pk': self.submission.pk}),
            {
                'use_rubric_score': 'on',
                'manual_score': '',
                'teacher_comment': 'Tot',
                f'rubric_score_{rubric_a.pk}': '55',
                f'rubric_comment_{rubric_a.pk}': 'OK',
                f'rubric_score_{rubric_b.pk}': '35',
                f'rubric_comment_{rubric_b.pk}': 'OK',
            },
        )

        self.submission.refresh_from_db()
        stats = AssignmentStatistics.objects.get(assignment=self.assignment)
        from apps.classrooms.models import Leaderboard
        leaderboard = Leaderboard.objects.get(classroom=self.classroom, student=self.student)

        factory = RequestFactory()
        request = factory.get(reverse('classrooms:gradebook', kwargs={'pk': self.classroom.pk}))
        from apps.classrooms.views import _build_gradebook_data
        gradebook = _build_gradebook_data(self.classroom, request)
        student_row = next(row for row in gradebook['rows'] if row['student'].pk == self.student.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.submission.manual_score, 90)
        self.assertEqual(RubricScores.objects.filter(submission=self.submission).count(), 2)
        self.assertEqual(stats.avg_score, 90)
        self.assertEqual(leaderboard.total_score, 90)
        self.assertEqual(student_row['cells'][0]['score'], 90)

    def test_exam_session_lifecycle_from_start_to_monitor_export(self):
        self.assignment.is_exam = True
        self.assignment.exam_duration_minutes = 30
        self.assignment.exam_allow_custom_input = True
        self.assignment.exam_allow_sample_run = True
        self.assignment.save(update_fields=[
            'is_exam',
            'exam_duration_minutes',
            'exam_allow_custom_input',
            'exam_allow_sample_run',
        ])
        self.client.force_login(self.student)

        lobby_response = self.client.get(reverse('submissions:exam_lobby', kwargs={'assignment_pk': self.assignment.pk}))
        start_response = self.client.post(reverse('submissions:start_exam', kwargs={'assignment_pk': self.assignment.pk}))
        session = ExamSessions.objects.get(assignment=self.assignment, student=self.student)
        ide_response = self.client.get(reverse('submissions:exam_ide', kwargs={'assignment_pk': self.assignment.pk}))
        event_response = self.client.post(
            reverse('submissions:exam_event', kwargs={'assignment_pk': self.assignment.pk}),
            data=json.dumps({'event_type': 'focus_lost', 'metadata': {'visible': False}}),
            content_type='application/json',
        )
        submit_response = self.client.post(
            reverse('submissions:submit', kwargs={'assignment_pk': self.assignment.pk}),
            data=json.dumps({
                'code': 'print("hello")',
                'language': 'python',
                'session_id': session.pk,
            }),
            content_type='application/json',
        )

        session.refresh_from_db()
        self.client.force_login(self.teacher)
        monitor_response = self.client.get(reverse('submissions:exam_monitor', kwargs={'assignment_pk': self.assignment.pk}))
        export_response = self.client.get(reverse('submissions:exam_monitor_export', kwargs={'assignment_pk': self.assignment.pk}))
        gradebook_export_response = self.client.get(reverse('classrooms:gradebook_export', kwargs={'pk': self.classroom.pk}))

        self.assertEqual(lobby_response.status_code, 200)
        self.assertEqual(start_response.status_code, 302)
        self.assertEqual(ide_response.status_code, 200)
        self.assertEqual(event_response.status_code, 200)
        self.assertEqual(submit_response.status_code, 200)
        self.assertEqual(submit_response.json()['status'], 'ok')
        self.assertEqual(session.status, ExamSessions.STATUS_SUBMITTED)
        self.assertIsNotNone(session.final_submission)
        self.assertTrue(ExamEvents.objects.filter(session=session, event_type='focus_lost').exists())
        self.assertEqual(monitor_response.status_code, 200)
        self.assertEqual(export_response.status_code, 200)
        self.assertTrue(export_response.content.startswith('\ufeff'.encode('utf-8')))
        self.assertEqual(gradebook_export_response.status_code, 200)
        self.assertTrue(gradebook_export_response.content.startswith('\ufeff'.encode('utf-8')))

    def test_student_direct_url_security_smoke(self):
        self.assignment.is_exam = True
        self.assignment.exam_duration_minutes = 30
        self.assignment.save(update_fields=['is_exam', 'exam_duration_minutes'])
        self.client.force_login(self.student)

        responses = [
            self.client.get(reverse('submissions:grade', kwargs={'pk': self.submission.pk})),
            self.client.get(reverse('submissions:exam_monitor', kwargs={'assignment_pk': self.assignment.pk})),
            self.client.get(reverse('assignments:plagiarism', kwargs={'pk': self.assignment.pk})),
            self.client.get(reverse('administation:dashboard')),
            self.client.post(reverse('administation:user_bulk_action'), {'action': 'deactivate', 'user_ids': [str(self.student.pk)]}),
        ]

        self.assertTrue(all(response.status_code in (302, 403) for response in responses))
