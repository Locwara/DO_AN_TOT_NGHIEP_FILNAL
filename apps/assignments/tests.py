import unittest

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profiles
from apps.administation.models import ActivityLogs
from apps.classrooms.models import ClassroomMembers, Classrooms
from apps.assignments.models import (
    AssignmentFileRequirements, Assignments, QuizChoices, QuizQuestionImports,
    QuizQuestions, QuizSettings, Testcases,
)
from apps.assignments.forms import AssignmentForm, TestcaseImportForm
from apps.assignments.views import _parse_quiz_csv_rows, _parse_testcases_csv, _parse_testcases_json
from apps.submissions.models import QuizAnswers, QuizAttempts, SubmissionFiles, Submissions
from apps.notifications.models import Notifications


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
        self.assertContains(response, 'id="submission-mode-control"')
        self.assertContains(response, 'value="file"')
        self.assertContains(response, 'value="quiz"')
        self.assertContains(response, 'id="assignment-grading-mode"')

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

    def test_assignment_form_v2_modes_keep_legacy_type_compatible(self):
        file_form = AssignmentForm(data={
            'title': 'Nop file',
            'description': 'Mo ta',
            'instructions': 'Nop PDF',
            'submission_mode': 'file',
            'grading_mode': 'auto',
            'type': 'auto_grade',
            'difficulty': 'easy',
            'late_penalty_percent': '0',
            'max_score': '100',
            'max_attempts': '2',
            'show_testcase_result': 'on',
            'exam_grace_seconds': '30',
            'classroom_subject': '',
            'file_allowed_extensions': ['.pdf', '.docx'],
            'file_max_size_mb': '20',
            'file_max_files': '2',
            'file_allow_resubmit': 'on',
            'file_require_all_files_before_submit': 'on',
        }, classroom=self.classroom)

        self.assertTrue(file_form.is_valid(), file_form.errors)
        self.assertEqual(file_form.cleaned_data['submission_mode'], 'file')
        self.assertEqual(file_form.cleaned_data['grading_mode'], 'manual')
        self.assertEqual(file_form.cleaned_data['type'], 'project')
        self.assertFalse(file_form.cleaned_data['show_testcase_result'])

        quiz_exam_form = AssignmentForm(data={
            'title': 'Thi quiz',
            'description': 'Mo ta',
            'instructions': 'Lam trac nghiem',
            'submission_mode': 'quiz',
            'grading_mode': 'auto',
            'type': 'auto_grade',
            'difficulty': 'medium',
            'late_penalty_percent': '0',
            'max_score': '100',
            'show_testcase_result': 'on',
            'is_exam': 'on',
            'exam_duration_minutes': '30',
            'exam_grace_seconds': '30',
            'classroom_subject': '',
        }, classroom=self.classroom)

        self.assertTrue(quiz_exam_form.is_valid(), quiz_exam_form.errors)
        self.assertEqual(quiz_exam_form.cleaned_data['submission_mode'], 'quiz')
        self.assertEqual(quiz_exam_form.cleaned_data['grading_mode'], 'auto')
        self.assertEqual(quiz_exam_form.cleaned_data['type'], 'auto_grade')
        self.assertEqual(quiz_exam_form.cleaned_data['max_attempts'], 1)

    def test_teacher_can_create_file_file_exam_and_quiz_assignments_from_route(self):
        file_response = self.client.post(reverse('assignments:create', kwargs={'classroom_pk': self.classroom.pk}), {
            'title': 'Nop file route',
            'description': 'Mo ta file',
            'instructions': 'Nop PDF',
            'submission_mode': Assignments.SUBMISSION_FILE,
            'grading_mode': Assignments.GRADING_MANUAL,
            'type': 'project',
            'difficulty': 'easy',
            'late_penalty_percent': '0',
            'max_score': '100',
            'max_attempts': '2',
            'show_testcase_result': '',
            'enable_leaderboard': '',
            'exam_grace_seconds': '30',
            'classroom_subject': '',
            'file_allowed_extensions': ['.pdf', '.zip'],
            'file_max_size_mb': '20',
            'file_max_files': '2',
            'file_require_comment': 'on',
            'file_allow_resubmit': 'on',
            'file_require_all_files_before_submit': 'on',
        })
        file_assignment = Assignments.objects.get(title='Nop file route')

        exam_response = self.client.post(reverse('assignments:create', kwargs={'classroom_pk': self.classroom.pk}), {
            'title': 'Thi nop file route',
            'description': 'Mo ta thi file',
            'instructions': 'Nop file trong phong thi',
            'submission_mode': Assignments.SUBMISSION_FILE,
            'grading_mode': Assignments.GRADING_MANUAL,
            'type': 'project',
            'difficulty': 'medium',
            'late_penalty_percent': '0',
            'max_score': '100',
            'max_attempts': '3',
            'show_testcase_result': '',
            'enable_leaderboard': '',
            'is_exam': 'on',
            'exam_duration_minutes': '45',
            'exam_grace_seconds': '30',
            'classroom_subject': '',
            'file_allowed_extensions': ['.pdf'],
            'file_max_size_mb': '30',
            'file_max_files': '1',
            'file_require_all_files_before_submit': 'on',
        })
        file_exam = Assignments.objects.get(title='Thi nop file route')

        quiz_response = self.client.post(reverse('assignments:create', kwargs={'classroom_pk': self.classroom.pk}), {
            'title': 'Quiz route',
            'description': 'Mo ta quiz',
            'instructions': 'Lam trac nghiem',
            'submission_mode': Assignments.SUBMISSION_QUIZ,
            'grading_mode': Assignments.GRADING_AUTO,
            'type': 'auto_grade',
            'difficulty': 'easy',
            'late_penalty_percent': '0',
            'max_score': '10',
            'max_attempts': '3',
            'show_testcase_result': '',
            'enable_leaderboard': '',
            'exam_grace_seconds': '30',
            'classroom_subject': '',
            'quiz_random_questions': 'on',
            'quiz_random_choices': 'on',
            'quiz_show_score_after_submit': 'on',
            'quiz_allow_review': 'on',
            'quiz_passing_score': '5',
        })
        quiz_assignment = Assignments.objects.get(title='Quiz route')

        self.assertEqual(file_response.status_code, 302)
        self.assertEqual(file_assignment.submission_mode, Assignments.SUBMISSION_FILE)
        self.assertEqual(file_assignment.file_requirements.max_files, 2)
        self.assertTrue(file_assignment.file_requirements.require_comment)
        self.assertEqual(exam_response.status_code, 302)
        self.assertTrue(file_exam.is_exam)
        self.assertEqual(file_exam.submission_mode, Assignments.SUBMISSION_FILE)
        self.assertEqual(file_exam.max_attempts, 1)
        self.assertFalse(file_exam.file_requirements.allow_resubmit)
        self.assertEqual(quiz_response.status_code, 302)
        self.assertEqual(quiz_assignment.submission_mode, Assignments.SUBMISSION_QUIZ)
        self.assertEqual(quiz_assignment.quiz_settings.question_order_mode, QuizSettings.ORDER_RANDOM)
        self.assertEqual(quiz_assignment.quiz_settings.choice_order_mode, QuizSettings.ORDER_RANDOM)
        self.assertEqual(quiz_assignment.quiz_settings.passing_score, 5)

    def test_file_requirements_route_updates_file_policy(self):
        assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Nop file rieng',
            description='Mo ta',
            instructions='Nop PDF',
            submission_mode=Assignments.SUBMISSION_FILE,
            grading_mode=Assignments.GRADING_MANUAL,
            type='project',
            created_by=self.teacher,
        )

        page = self.client.get(reverse('assignments:file_requirements', kwargs={'pk': assignment.pk}))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Yêu cầu nộp file')

        response = self.client.post(
            reverse('assignments:file_requirements', kwargs={'pk': assignment.pk}),
            {
                'allowed_extensions': ['.pdf', '.zip'],
                'max_file_size_mb': '30',
                'max_files': '2',
                'require_comment': 'on',
                'allow_resubmit': 'on',
                'require_all_files_before_submit': 'on',
                'scan_required': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        requirements = AssignmentFileRequirements.objects.get(assignment=assignment)
        self.assertEqual(requirements.allowed_extensions, ['.pdf', '.zip'])
        self.assertEqual(requirements.max_file_size_mb, 30)
        self.assertEqual(requirements.max_files, 2)
        self.assertTrue(requirements.require_comment)
        self.assertTrue(requirements.scan_required)
        self.assertIn('application/pdf', requirements.allowed_mime_types)
        self.assertTrue(ActivityLogs.objects.filter(action='ASSIGNMENT_FILE_REQUIREMENTS_UPDATE').exists())

    def test_publishing_file_assignment_notifies_students_with_mode_context(self):
        student = User.objects.create_user(username='student-notify', password='pass12345')
        Profiles.objects.create(id=student, role='student', status='approved')
        ClassroomMembers.objects.create(classroom=self.classroom, student=student, status='approved')
        assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Nop file publish',
            description='Mo ta',
            instructions='Nop PDF',
            submission_mode=Assignments.SUBMISSION_FILE,
            grading_mode=Assignments.GRADING_MANUAL,
            type='project',
            created_by=self.teacher,
        )
        AssignmentFileRequirements.objects.create(
            assignment=assignment,
            allowed_extensions=['.pdf'],
            max_file_size_mb=10,
            max_files=1,
        )

        response = self.client.post(reverse('assignments:toggle_publish', kwargs={'pk': assignment.pk}))

        self.assertEqual(response.status_code, 302)
        notification = Notifications.objects.get(recipient=student, notification_type='assignment_published')
        self.assertIn('Bài nộp file mới', notification.title)
        self.assertEqual(notification.metadata['submission_mode'], Assignments.SUBMISSION_FILE)

    def test_testcase_import_validates_file_size_and_schema(self):
        large_file = SimpleUploadedFile('tests.json', b'0' * (1024 * 1024 + 1))
        form = TestcaseImportForm(data={'import_format': 'json'}, files={'file': large_file})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

        with self.assertRaisesMessage(ValueError, 'expected_output'):
            _parse_testcases_json('[{"name": "T1", "input": "1"}]')
        with self.assertRaisesMessage(ValueError, 'CSV thiếu cột'):
            _parse_testcases_csv('name,input\nT1,1\n')

    def test_quiz_csv_parser_supports_choices_json_and_validates_answers(self):
        valid_csv = (
            'question_text,question_type,points,choices_json,correct_answers,explanation,tags,difficulty\n'
            '"Framework nào dùng virtual DOM?",single_choice,1,"[""React"",""Django"",""PostgreSQL""]",A,ok,frontend,easy\n'
        )
        rows, errors = _parse_quiz_csv_rows(valid_csv)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]['choices'], ['React', 'Django', 'PostgreSQL'])
        self.assertEqual(rows[0]['correct_answers'], ['A'])

        invalid_csv = (
            'question_text,question_type,points,choice_a,choice_b,correct_answers\n'
            'Sai dap an,single_choice,1,A,B,Z\n'
            'Nhieu dap an,multiple_choice,1,A,B,\n'
        )
        rows, errors = _parse_quiz_csv_rows(invalid_csv)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['line_no'], 2)
        self.assertEqual(errors[1]['line_no'], 3)
        self.assertIn('correct_answers không tồn tại', errors[0]['errors'][0])
        self.assertIn('Thiếu correct_answers.', errors[1]['errors'])

    def test_quiz_import_preview_and_confirm_writes_history(self):
        assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Quiz import',
            description='Mo ta',
            instructions='Lam quiz',
            submission_mode=Assignments.SUBMISSION_QUIZ,
            grading_mode=Assignments.GRADING_AUTO,
            type='auto_grade',
            created_by=self.teacher,
        )
        csv_text = (
            'question_text,question_type,points,choice_a,choice_b,correct_answers,explanation,tags,difficulty\n'
            'CSV smoke?,single_choice,1,Yes,No,A,ok,smoke,easy\n'
        )
        preview = self.client.post(
            reverse('assignments:import_quiz_questions', kwargs={'pk': assignment.pk}),
            {'action': 'preview', 'content': csv_text},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, 'Hợp lệ')

        confirm = self.client.post(
            reverse('assignments:import_quiz_questions', kwargs={'pk': assignment.pk}),
            {'action': 'confirm'},
        )
        self.assertEqual(confirm.status_code, 302)
        self.assertEqual(QuizQuestions.objects.filter(assignment=assignment).count(), 1)
        history = QuizQuestionImports.objects.get(assignment=assignment)
        self.assertEqual(history.total_rows, 1)
        self.assertEqual(history.success_rows, 1)
        self.assertEqual(history.error_rows, 0)
        self.assertTrue(ActivityLogs.objects.filter(action='QUIZ_CSV_IMPORT', resource_id=assignment.pk).exists())

    def test_quiz_short_text_import_switches_assignment_to_mixed_grading(self):
        assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Quiz tu luan ngan',
            description='Mo ta',
            instructions='Lam quiz',
            submission_mode=Assignments.SUBMISSION_QUIZ,
            grading_mode=Assignments.GRADING_AUTO,
            type='auto_grade',
            created_by=self.teacher,
        )
        csv_text = (
            'question_text,question_type,points,correct_answers\n'
            'Giai thich bien la gi?,short_text,2,\n'
        )
        self.client.post(
            reverse('assignments:import_quiz_questions', kwargs={'pk': assignment.pk}),
            {'action': 'preview', 'content': csv_text},
        )
        confirm = self.client.post(
            reverse('assignments:import_quiz_questions', kwargs={'pk': assignment.pk}),
            {'action': 'confirm'},
        )

        assignment.refresh_from_db()
        self.assertEqual(confirm.status_code, 302)
        self.assertEqual(assignment.grading_mode, Assignments.GRADING_MIXED)
        self.assertEqual(assignment.type, 'manual_grade')

    def test_file_assignment_statistics_and_csv_include_file_grading_context(self):
        student = User.objects.create_user(username='student-file', password='pass12345', email='student@example.com')
        Profiles.objects.create(id=student, role='student', status='approved')
        ClassroomMembers.objects.create(classroom=self.classroom, student=student, status='approved')
        assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Bao cao thuc hanh',
            description='Mo ta',
            instructions='Nop PDF',
            submission_mode=Assignments.SUBMISSION_FILE,
            grading_mode=Assignments.GRADING_MANUAL,
            type='project',
            max_score=100,
            created_by=self.teacher,
            is_published=True,
        )
        submission = Submissions.objects.create(
            assignment=assignment,
            student=student,
            submission_mode_snapshot=Assignments.SUBMISSION_FILE,
            status='pending',
            manual_score=88,
            max_score=100,
            graded_by=self.teacher,
            graded_at=timezone.now(),
            teacher_comment='Tot',
        )
        SubmissionFiles.objects.create(
            submission=submission,
            uploaded_by=student,
            file_name='bao-cao.pdf',
            file_url='https://example.com/bao-cao.pdf',
            file_size=1200,
            scan_status=SubmissionFiles.SCAN_CLEAN,
        )

        stats = self.client.get(reverse('assignments:statistics', kwargs={'pk': assignment.pk}))
        self.assertEqual(stats.status_code, 200)
        self.assertContains(stats, 'Tổng file')
        self.assertContains(stats, 'Nộp file')

        export = self.client.get(reverse('assignments:export_submissions', kwargs={'pk': assignment.pk}))
        self.assertEqual(export.status_code, 200)
        content = export.content.decode('utf-8-sig')
        self.assertIn('bao-cao.pdf', content)
        self.assertIn('Đã chấm', content)

    def test_quiz_statistics_and_csv_exports_attempts_and_question_analysis(self):
        student = User.objects.create_user(username='student-quiz', password='pass12345', email='quiz@example.com')
        Profiles.objects.create(id=student, role='student', status='approved')
        ClassroomMembers.objects.create(classroom=self.classroom, student=student, status='approved')
        assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Quiz CSV',
            description='Mo ta',
            instructions='Lam quiz',
            submission_mode=Assignments.SUBMISSION_QUIZ,
            grading_mode=Assignments.GRADING_AUTO,
            type='auto_grade',
            max_score=10,
            created_by=self.teacher,
            is_published=True,
        )
        QuizSettings.objects.create(assignment=assignment)
        question = QuizQuestions.objects.create(
            assignment=assignment,
            question_text='2 + 2 = ?',
            question_type=QuizQuestions.TYPE_SINGLE_CHOICE,
            points=10,
        )
        QuizChoices.objects.create(question=question, choice_text='3', is_correct=False)
        correct_choice = QuizChoices.objects.create(question=question, choice_text='4', is_correct=True)
        submission = Submissions.objects.create(
            assignment=assignment,
            student=student,
            submission_mode_snapshot=Assignments.SUBMISSION_QUIZ,
            language='quiz',
            status='finished',
            total_score=10,
            max_score=10,
        )
        attempt = QuizAttempts.objects.create(
            assignment=assignment,
            student=student,
            submission=submission,
            attempt_no=1,
            status=QuizAttempts.STATUS_SUBMITTED,
            started_at=timezone.now(),
            submitted_at=timezone.now(),
            score=10,
            max_score=10,
            duration_seconds=42,
        )
        answer = QuizAnswers.objects.create(
            attempt=attempt,
            question=question,
            selected_choice_ids=[correct_choice.pk],
            is_correct=True,
            score_awarded=10,
            answered_at=timezone.now(),
        )
        answer.selected_choices.add(correct_choice)

        stats = self.client.get(reverse('assignments:statistics', kwargs={'pk': assignment.pk}))
        self.assertEqual(stats.status_code, 200)
        self.assertContains(stats, 'Điểm TB quiz')
        self.assertContains(stats, '2 + 2')

        attempts_export = self.client.get(reverse('assignments:export_quiz_attempts', kwargs={'pk': assignment.pk}))
        self.assertEqual(attempts_export.status_code, 200)
        attempts_content = attempts_export.content.decode('utf-8-sig')
        self.assertIn('Attempt ID', attempts_content)
        self.assertIn('student-quiz', attempts_content)

        question_export = self.client.get(reverse('assignments:export_quiz_question_analysis', kwargs={'pk': assignment.pk}))
        self.assertEqual(question_export.status_code, 200)
        question_content = question_export.content.decode('utf-8-sig')
        self.assertIn('2 + 2 = ?', question_content)
        self.assertIn('100.0%', question_content)
        self.assertIn('4,4', question_content)

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
