import json
import unittest
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profiles
from apps.administation.models import ActivityLogs
from apps.assignments.models import (
    AssignmentFiles, AssignmentFileRequirements, AssignmentStatistics, Assignments,
    QuizChoices, QuizQuestions, QuizSettings, Rubrics,
)
from apps.classrooms.models import ClassroomApprovalStatus, ClassroomMembers, Classrooms
from apps.notifications.models import Notifications
from apps.submissions.models import (
    AIScoringSuggestions,
    CodeDrafts, ExamEvents, ExamSessions, RubricScores, Submissions,
    SubmissionFileFeedbacks, SubmissionFiles, QuizAnswers, QuizAttempts,
    GradeChangeLogs,
)
from apps.submissions.utils import build_ai_grading_context


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

    def test_file_submission_models_store_requirements_files_and_feedback(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type'])

        requirements = AssignmentFileRequirements.objects.create(
            assignment=self.assignment,
            allowed_extensions=['.pdf', '.docx', '.zip'],
            allowed_mime_types=['application/pdf'],
            max_file_size_mb=25,
            max_files=3,
            require_comment=True,
            scan_required=True,
        )
        submission = Submissions.objects.create(
            assignment=self.assignment,
            student=self.student,
            submission_mode_snapshot=Assignments.SUBMISSION_FILE,
            submission_text='Em nop file bao cao va source code.',
            status='pending',
            max_score=100,
        )
        uploaded = SubmissionFiles.objects.create(
            submission=submission,
            uploaded_by=self.student,
            file_name='bao-cao.pdf',
            file_url='https://example.com/bao-cao.pdf',
            file_size=1024,
            mime_type='application/pdf',
            extension='.pdf',
            checksum='sha256-demo',
            scan_status=SubmissionFiles.SCAN_PENDING,
        )
        feedback = SubmissionFileFeedbacks.objects.create(
            submission=submission,
            uploaded_by=self.teacher,
            file_name='nhan-xet.pdf',
            file_url='https://example.com/nhan-xet.pdf',
            note='Da annotate file.',
        )

        self.assertEqual(requirements.max_files, 3)
        self.assertEqual(submission.code_content, '')
        self.assertEqual(submission.language, '')
        self.assertEqual(submission.submission_mode_snapshot, Assignments.SUBMISSION_FILE)
        self.assertEqual(submission.files.get(), uploaded)
        self.assertEqual(submission.feedback_files.get(), feedback)

    def test_ai_hook_models_store_clean_context_without_calling_ai(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.save(update_fields=['submission_mode', 'grading_mode'])
        self.submission.submission_mode_snapshot = Assignments.SUBMISSION_FILE
        self.submission.submission_text = 'Em nop file bao cao.'
        self.submission.save(update_fields=['submission_mode_snapshot', 'submission_text'])

        Rubrics.objects.create(
            assignment=self.assignment,
            name='Logic',
            description='Dung yeu cau',
            max_points=10,
            order_index=1,
        )
        SubmissionFiles.objects.create(
            submission=self.submission,
            uploaded_by=self.student,
            file_name='bao-cao.pdf',
            file_url='https://example.com/bao-cao.pdf',
            file_size=2048,
            mime_type='application/pdf',
            extension='.pdf',
            checksum='sha256-ai-hook',
            scan_status=SubmissionFiles.SCAN_CLEAN,
            text_extraction_status=SubmissionFiles.TEXT_EXTRACTED,
            extracted_text='Noi dung da trich xuat de AI doc sau nay.',
        )
        suggestion = AIScoringSuggestions.objects.create(
            submission=self.submission,
            target_type=AIScoringSuggestions.TARGET_FILE_SUBMISSION,
            suggested_score=8.5,
            max_score=10,
            confidence=0.82,
            prompt_version='manual-rubric-v1',
            input_snapshot={'source': 'test-only'},
        )

        payload = build_ai_grading_context(self.submission)

        self.assertEqual(suggestion.status, AIScoringSuggestions.STATUS_DRAFT)
        self.assertEqual(payload['submission']['mode'], Assignments.SUBMISSION_FILE)
        self.assertEqual(payload['files'][0]['text_extraction_status'], SubmissionFiles.TEXT_EXTRACTED)
        self.assertIn('Noi dung da trich xuat', payload['files'][0]['extracted_text'])

    def test_grade_page_contains_hidden_ai_hook(self):
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('submissions:grade', kwargs={'pk': self.submission.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="ai-suggestions-panel"')
        self.assertContains(response, 'data-ai-hook="future"')

    def test_quiz_models_store_settings_questions_attempts_and_submission(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_QUIZ
        self.assignment.grading_mode = Assignments.GRADING_AUTO
        self.assignment.type = 'auto_grade'
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type'])
        settings = QuizSettings.objects.create(
            assignment=self.assignment,
            question_order_mode=QuizSettings.ORDER_RANDOM,
            choice_order_mode=QuizSettings.ORDER_RANDOM,
            show_score_after_submit=True,
            show_correct_answers=False,
            show_explanation=True,
            time_limit_minutes=20,
            passing_score=50,
        )
        question = QuizQuestions.objects.create(
            assignment=self.assignment,
            question_text='Python la ngon ngu thong dich?',
            question_type=QuizQuestions.TYPE_TRUE_FALSE,
            points=2,
            order_index=1,
            explanation='Python thuong duoc thuc thi qua interpreter.',
            tags=['python', 'basic'],
            difficulty='easy',
        )
        true_choice = QuizChoices.objects.create(
            question=question,
            choice_text='Dung',
            is_correct=True,
            order_index=1,
        )
        false_choice = QuizChoices.objects.create(
            question=question,
            choice_text='Sai',
            is_correct=False,
            order_index=2,
        )
        submission = Submissions.objects.create(
            assignment=self.assignment,
            student=self.student,
            submission_mode_snapshot=Assignments.SUBMISSION_QUIZ,
            language='quiz',
            status='finished',
            total_score=2,
            max_score=2,
        )
        session = ExamSessions.objects.create(
            assignment=self.assignment,
            student=self.student,
            status=ExamSessions.STATUS_SUBMITTED,
            final_submission=submission,
        )
        attempt = QuizAttempts.objects.create(
            assignment=self.assignment,
            student=self.student,
            submission=submission,
            exam_session=session,
            attempt_no=1,
            status=QuizAttempts.STATUS_SUBMITTED,
            score=2,
            max_score=2,
            random_seed='seed-1',
        )
        answer = QuizAnswers.objects.create(
            attempt=attempt,
            question=question,
            selected_choice_ids=[true_choice.pk],
            is_correct=True,
            score_awarded=2,
        )
        answer.selected_choices.add(true_choice)

        self.assertEqual(settings.question_order_mode, QuizSettings.ORDER_RANDOM)
        self.assertEqual(question.question_type, QuizQuestions.TYPE_TRUE_FALSE)
        self.assertEqual(question.choices.count(), 2)
        self.assertEqual(question.choices.filter(is_correct=True).get(), true_choice)
        self.assertEqual(false_choice.is_correct, False)
        self.assertEqual(attempt.submission, submission)
        self.assertEqual(attempt.exam_session, session)
        self.assertEqual(answer.selected_choices.get(), true_choice)
        self.assertEqual(submission.submission_mode_snapshot, Assignments.SUBMISSION_QUIZ)
        self.assertEqual(submission.language, 'quiz')

    @patch('apps.submissions.views.cloudinary.uploader.upload')
    def test_student_can_submit_file_assignment(self, upload_mock):
        upload_mock.return_value = {'secure_url': 'https://example.com/bao-cao.pdf'}
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.max_attempts = 2
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type', 'max_attempts'])
        AssignmentFileRequirements.objects.create(
            assignment=self.assignment,
            allowed_extensions=['.pdf'],
            allowed_mime_types=['application/pdf'],
            max_file_size_mb=5,
            max_files=1,
            require_comment=True,
        )
        self.client.force_login(self.student)
        uploaded = SimpleUploadedFile(
            'bao-cao.pdf',
            b'%PDF-1.4 demo',
            content_type='application/pdf',
        )

        response = self.client.post(
            reverse('submissions:submit_file', kwargs={'assignment_pk': self.assignment.pk}),
            {'submission_text': 'Nop bao cao PDF.', 'files': [uploaded]},
        )

        self.assertEqual(response.status_code, 302)
        submission = Submissions.objects.exclude(pk=self.submission.pk).get()
        self.assertEqual(submission.submission_mode_snapshot, Assignments.SUBMISSION_FILE)
        self.assertEqual(submission.status, 'pending')
        self.assertEqual(submission.submission_text, 'Nop bao cao PDF.')
        submission_file = submission.files.get()
        self.assertEqual(submission_file.extension, '.pdf')
        self.assertTrue(submission_file.checksum)
        self.assertEqual(submission_file.scan_status, SubmissionFiles.SCAN_SKIPPED)
        notification = Notifications.objects.get(recipient=self.teacher, notification_type='submission_submitted')
        self.assertEqual(notification.metadata['submission_mode'], 'file')

    def test_student_sees_file_submission_history_detail_and_released_score(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.grades_released_at = timezone.now()
        self.assignment.show_feedback_after_release = True
        self.assignment.save(update_fields=[
            'submission_mode', 'grading_mode', 'type',
            'grades_released_at', 'show_feedback_after_release',
        ])
        self.submission.submission_mode_snapshot = Assignments.SUBMISSION_FILE
        self.submission.status = 'finished'
        self.submission.manual_score = 86
        self.submission.teacher_comment = 'Bai nop file dat yeu cau.'
        self.submission.save(update_fields=[
            'submission_mode_snapshot', 'status', 'manual_score', 'teacher_comment',
        ])
        SubmissionFiles.objects.create(
            submission=self.submission,
            uploaded_by=self.student,
            file_name='bao-cao.pdf',
            file_url='https://example.com/bao-cao.pdf',
            file_size=2048,
            mime_type='application/pdf',
            extension='.pdf',
            scan_status=SubmissionFiles.SCAN_CLEAN,
        )
        SubmissionFileFeedbacks.objects.create(
            submission=self.submission,
            uploaded_by=self.teacher,
            file_name='nhan-xet.pdf',
            file_url='https://example.com/nhan-xet.pdf',
            note='Nhan xet chi tiet.',
        )
        self.client.force_login(self.student)

        history_response = self.client.get(reverse('submissions:history', kwargs={'assignment_pk': self.assignment.pk}))
        detail_response = self.client.get(reverse('submissions:detail', kwargs={'pk': self.submission.pk}))

        self.assertEqual(history_response.status_code, 200)
        self.assertContains(history_response, '86.0/100.0')
        self.assertContains(history_response, '1')
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'File đã nộp')
        self.assertContains(detail_response, 'bao-cao.pdf')
        self.assertContains(detail_response, '86.0')
        self.assertContains(detail_response, 'Bai nop file dat yeu cau.')
        self.assertContains(detail_response, 'nhan-xet.pdf')

    def test_file_submission_alias_and_clear_draft_route(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.max_attempts = 2
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type', 'max_attempts'])
        AssignmentFileRequirements.objects.create(
            assignment=self.assignment,
            allowed_extensions=['.pdf'],
            max_file_size_mb=5,
            max_files=1,
        )
        self.client.force_login(self.student)

        page = self.client.get(
            reverse('submissions:file_submission', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Nộp file')

        draft = Submissions.objects.create(
            assignment=self.assignment,
            student=self.student,
            submission_mode_snapshot=Assignments.SUBMISSION_FILE,
            status='draft',
            max_score=100,
        )
        SubmissionFiles.objects.create(
            submission=draft,
            uploaded_by=self.student,
            file_name='draft.pdf',
            file_url='https://example.com/draft.pdf',
            file_size=10,
            extension='.pdf',
        )
        clear = self.client.post(
            reverse('submissions:clear_file_draft', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(clear.status_code, 200)
        self.assertEqual(clear.json()['deleted_submissions'], 1)
        self.assertFalse(Submissions.objects.filter(pk=draft.pk).exists())

    def test_file_assignment_rejects_invalid_extension(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type'])
        AssignmentFileRequirements.objects.create(
            assignment=self.assignment,
            allowed_extensions=['.pdf'],
            max_file_size_mb=5,
            max_files=1,
        )
        self.submission.delete()
        self.client.force_login(self.student)
        uploaded = SimpleUploadedFile('script.exe', b'bad', content_type='application/octet-stream')

        response = self.client.post(
            reverse('submissions:submit_file', kwargs={'assignment_pk': self.assignment.pk}),
            {'submission_text': 'bad', 'files': [uploaded]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Submissions.objects.filter(submission_mode_snapshot=Assignments.SUBMISSION_FILE).exists())

    def test_file_assignment_rejects_invalid_mime_type(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type'])
        AssignmentFileRequirements.objects.create(
            assignment=self.assignment,
            allowed_extensions=['.pdf'],
            allowed_mime_types=['application/pdf'],
            max_file_size_mb=5,
            max_files=1,
        )
        self.submission.delete()
        self.client.force_login(self.student)
        uploaded = SimpleUploadedFile('report.pdf', b'plain text', content_type='text/plain')

        response = self.client.post(
            reverse('submissions:submit_file', kwargs={'assignment_pk': self.assignment.pk}),
            {'submission_text': 'mime sai', 'files': [uploaded]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Submissions.objects.filter(submission_mode_snapshot=Assignments.SUBMISSION_FILE).exists())

    def test_file_assignment_rejects_oversized_file(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type'])
        AssignmentFileRequirements.objects.create(
            assignment=self.assignment,
            allowed_extensions=['.pdf'],
            allowed_mime_types=['application/pdf'],
            max_file_size_mb=1,
            max_files=1,
        )
        self.submission.delete()
        self.client.force_login(self.student)
        uploaded = SimpleUploadedFile(
            'big-report.pdf',
            b'%PDF' + b'0' * (1024 * 1024 + 1),
            content_type='application/pdf',
        )

        response = self.client.post(
            reverse('submissions:submit_file', kwargs={'assignment_pk': self.assignment.pk}),
            {'submission_text': 'qua lon', 'files': [uploaded]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Submissions.objects.filter(submission_mode_snapshot=Assignments.SUBMISSION_FILE).exists())

    def test_file_download_routes_enforce_owner_and_teacher_permissions(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type'])
        file_obj = SubmissionFiles.objects.create(
            submission=self.submission,
            uploaded_by=self.student,
            file_name='bao-cao.pdf',
            file_url='https://example.com/private/bao-cao.pdf',
            file_size=123,
            mime_type='application/pdf',
            extension='.pdf',
            checksum='sha256-demo',
            scan_status=SubmissionFiles.SCAN_CLEAN,
        )

        self.client.force_login(self.other_student)
        denied = self.client.get(reverse('submissions:open_file', kwargs={'file_pk': file_obj.pk}))
        self.assertEqual(denied.status_code, 302)
        self.assertNotEqual(denied.headers.get('Location'), file_obj.file_url)

        self.client.force_login(self.other_teacher)
        other_teacher_denied = self.client.get(reverse('submissions:open_file', kwargs={'file_pk': file_obj.pk}))
        self.assertEqual(other_teacher_denied.status_code, 302)
        self.assertNotEqual(other_teacher_denied.headers.get('Location'), file_obj.file_url)

        self.client.force_login(self.student)
        owner_response = self.client.get(reverse('submissions:open_file', kwargs={'file_pk': file_obj.pk}))
        self.assertEqual(owner_response.status_code, 302)
        self.assertEqual(owner_response.headers.get('Location'), file_obj.file_url)

        self.client.force_login(self.teacher)
        teacher_response = self.client.get(reverse('submissions:open_file', kwargs={'file_pk': file_obj.pk}))
        self.assertEqual(teacher_response.status_code, 302)
        self.assertEqual(teacher_response.headers.get('Location'), file_obj.file_url)

    def test_student_can_start_autosave_and_submit_quiz_assignment(self):
        self.submission.delete()
        self.assignment.submission_mode = Assignments.SUBMISSION_QUIZ
        self.assignment.grading_mode = Assignments.GRADING_AUTO
        self.assignment.type = 'auto_grade'
        self.assignment.max_score = 5
        self.assignment.max_attempts = 2
        self.assignment.save(update_fields=[
            'submission_mode', 'grading_mode', 'type', 'max_score', 'max_attempts',
        ])
        QuizSettings.objects.create(
            assignment=self.assignment,
            show_score_after_submit=True,
            show_correct_answers=False,
            allow_review=True,
        )
        question = QuizQuestions.objects.create(
            assignment=self.assignment,
            question_text='Python dùng keyword nào để định nghĩa hàm?',
            question_type=QuizQuestions.TYPE_SINGLE_CHOICE,
            points=5,
            order_index=1,
        )
        wrong_choice = QuizChoices.objects.create(
            question=question,
            choice_text='class',
            is_correct=False,
            order_index=1,
        )
        correct_choice = QuizChoices.objects.create(
            question=question,
            choice_text='def',
            is_correct=True,
            order_index=2,
        )
        self.client.force_login(self.student)

        lobby_response = self.client.get(
            reverse('submissions:quiz_lobby', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(lobby_response.status_code, 200)
        self.assertContains(lobby_response, '0 lượt')

        start_response = self.client.post(
            reverse('submissions:start_quiz', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(start_response.status_code, 302)
        attempt = QuizAttempts.objects.get(assignment=self.assignment, student=self.student)
        self.assertEqual(attempt.status, QuizAttempts.STATUS_IN_PROGRESS)

        take_response = self.client.get(
            reverse('submissions:quiz_take', kwargs={'attempt_pk': attempt.pk})
        )
        self.assertEqual(take_response.status_code, 200)
        self.assertContains(take_response, 'Python dùng keyword')

        autosave_response = self.client.post(
            reverse('submissions:quiz_autosave', kwargs={'attempt_pk': attempt.pk}),
            data=json.dumps({
                'question_id': question.pk,
                'selected_choice_ids': [wrong_choice.pk],
            }),
            content_type='application/json',
        )
        self.assertEqual(autosave_response.status_code, 200)
        answer = QuizAnswers.objects.get(attempt=attempt, question=question)
        self.assertEqual(answer.selected_choice_ids, [wrong_choice.pk])

        submit_response = self.client.post(
            reverse('submissions:quiz_submit', kwargs={'attempt_pk': attempt.pk}),
            {f'question_{question.pk}': str(correct_choice.pk)},
        )
        self.assertEqual(submit_response.status_code, 302)
        attempt.refresh_from_db()
        answer.refresh_from_db()
        self.assertEqual(attempt.status, QuizAttempts.STATUS_SUBMITTED)
        self.assertEqual(attempt.score, 5)
        self.assertEqual(attempt.max_score, 5)
        self.assertEqual(answer.selected_choice_ids, [correct_choice.pk])
        self.assertTrue(answer.is_correct)
        self.assertIsNotNone(attempt.submission)
        self.assertEqual(attempt.submission.submission_mode_snapshot, Assignments.SUBMISSION_QUIZ)
        self.assertEqual(attempt.submission.language, 'quiz')

        result_response = self.client.get(
            reverse('submissions:quiz_result', kwargs={'attempt_pk': attempt.pk})
        )
        self.assertEqual(result_response.status_code, 200)
        self.assertContains(result_response, '5.00/5.00')
        self.assertNotContains(result_response, 'Đáp án đúng</p>')

    def test_quiz_assignment_respects_max_attempts(self):
        self.submission.delete()
        self.assignment.submission_mode = Assignments.SUBMISSION_QUIZ
        self.assignment.grading_mode = Assignments.GRADING_AUTO
        self.assignment.max_attempts = 1
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'max_attempts'])
        QuizSettings.objects.create(assignment=self.assignment)
        question = QuizQuestions.objects.create(
            assignment=self.assignment,
            question_text='2 + 2 = ?',
            question_type=QuizQuestions.TYPE_SINGLE_CHOICE,
            points=1,
        )
        QuizChoices.objects.create(question=question, choice_text='4', is_correct=True)
        QuizAttempts.objects.create(
            assignment=self.assignment,
            student=self.student,
            attempt_no=1,
            status=QuizAttempts.STATUS_SUBMITTED,
            started_at=timezone.now(),
            submitted_at=timezone.now(),
        )
        self.client.force_login(self.student)

        response = self.client.post(
            reverse('submissions:start_quiz', kwargs={'assignment_pk': self.assignment.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(QuizAttempts.objects.filter(assignment=self.assignment, student=self.student).count(), 1)

    def test_assignment_file_route_allows_class_members_only(self):
        assignment_file = AssignmentFiles.objects.create(
            assignment=self.assignment,
            file_name='de-bai.pdf',
            file_url='https://example.com/private/de-bai.pdf',
            file_size=456,
            mime_type='application/pdf',
        )

        self.client.force_login(self.student)
        member_response = self.client.get(reverse(
            'assignments:open_file',
            kwargs={'pk': self.assignment.pk, 'file_pk': assignment_file.pk},
        ))
        self.assertEqual(member_response.status_code, 302)
        self.assertEqual(member_response.headers.get('Location'), assignment_file.file_url)

        self.client.force_login(self.other_teacher)
        denied = self.client.get(reverse(
            'assignments:open_file',
            kwargs={'pk': self.assignment.pk, 'file_pk': assignment_file.pk},
        ))
        self.assertEqual(denied.status_code, 302)
        self.assertNotEqual(denied.headers.get('Location'), assignment_file.file_url)

    @patch('apps.submissions.views.cloudinary.uploader.upload')
    def test_file_exam_uses_exam_session_and_submits_once(self, upload_mock):
        upload_mock.return_value = {'secure_url': 'https://example.com/exam.pdf'}
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.is_exam = True
        self.assignment.exam_duration_minutes = 30
        self.assignment.max_attempts = 1
        self.assignment.save(update_fields=[
            'submission_mode', 'grading_mode', 'type',
            'is_exam', 'exam_duration_minutes', 'max_attempts',
        ])
        AssignmentFileRequirements.objects.create(
            assignment=self.assignment,
            allowed_extensions=['.pdf'],
            max_file_size_mb=5,
            max_files=1,
        )
        self.submission.delete()
        self.client.force_login(self.student)

        start_response = self.client.post(
            reverse('submissions:start_exam', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(start_response.status_code, 302)
        session = ExamSessions.objects.get(assignment=self.assignment, student=self.student)
        self.assertEqual(session.status, ExamSessions.STATUS_RUNNING)

        ide_response = self.client.get(
            reverse('submissions:exam_ide', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(ide_response.status_code, 200)
        self.assertContains(ide_response, 'Bài làm trong phòng thi')

        uploaded = SimpleUploadedFile('exam.pdf', b'%PDF exam', content_type='application/pdf')
        submit_response = self.client.post(
            reverse('submissions:submit_file', kwargs={'assignment_pk': self.assignment.pk}),
            {
                'session_id': str(session.pk),
                'submission_text': 'Bai thi file.',
                'files': [uploaded],
            },
        )

        self.assertEqual(submit_response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, ExamSessions.STATUS_SUBMITTED)
        self.assertIsNotNone(session.final_submission_id)
        self.assertEqual(session.final_submission.submission_mode_snapshot, Assignments.SUBMISSION_FILE)
        self.assertEqual(session.final_submission.files.count(), 1)
        self.assertTrue(ExamEvents.objects.filter(session=session, event_type='submitted').exists())

        uploaded_again = SimpleUploadedFile('exam.pdf', b'%PDF again', content_type='application/pdf')
        second_response = self.client.post(
            reverse('submissions:submit_file', kwargs={'assignment_pk': self.assignment.pk}),
            {
                'session_id': str(session.pk),
                'submission_text': 'Nop lai.',
                'files': [uploaded_again],
            },
        )
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(Submissions.objects.filter(assignment=self.assignment, student=self.student).count(), 1)

    def test_teacher_can_manually_grade_file_submission_with_feedback_file(self):
        self.assignment.submission_mode = Assignments.SUBMISSION_FILE
        self.assignment.grading_mode = Assignments.GRADING_MANUAL
        self.assignment.type = 'project'
        self.assignment.max_score = 100
        self.assignment.save(update_fields=['submission_mode', 'grading_mode', 'type', 'max_score'])
        self.submission.submission_mode_snapshot = Assignments.SUBMISSION_FILE
        self.submission.status = 'pending'
        self.submission.save(update_fields=['submission_mode_snapshot', 'status'])
        rubric = Rubrics.objects.create(
            assignment=self.assignment,
            name='Bao cao',
            max_points=100,
            order_index=1,
        )
        SubmissionFiles.objects.create(
            submission=self.submission,
            uploaded_by=self.student,
            file_name='bao-cao.pdf',
            file_url='https://example.com/bao-cao.pdf',
            extension='.pdf',
            scan_status=SubmissionFiles.SCAN_CLEAN,
        )
        self.client.force_login(self.teacher)
        feedback_file = SimpleUploadedFile(
            'nhan-xet.txt',
            b'feedback',
            content_type='text/plain',
        )

        with patch('apps.submissions.views.cloudinary.uploader.upload') as upload_mock:
            upload_mock.return_value = {'secure_url': 'https://example.com/nhan-xet.txt'}
            response = self.client.post(
                reverse('submissions:grade', kwargs={'pk': self.submission.pk}),
                {
                    'use_rubric_score': 'on',
                    'manual_score': '',
                    'teacher_comment': 'File dat yeu cau.',
                    f'rubric_score_{rubric.pk}': '91',
                    f'rubric_comment_{rubric.pk}': 'Tot',
                    'feedback_file_note': 'File nhan xet',
                    'feedback_file': feedback_file,
                },
            )

        self.submission.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.submission.manual_score, 91)
        self.assertEqual(self.submission.status, 'finished')
        self.assertEqual(self.submission.feedback_files.count(), 1)
        self.assertTrue(GradeChangeLogs.objects.filter(submission=self.submission).exists())

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
        self.assertTrue(GradeChangeLogs.objects.filter(submission=self.submission, changed_by=self.teacher).exists())
        self.assertTrue(ActivityLogs.objects.filter(action='SUBMISSION_MANUAL_GRADE', resource_id=self.submission.pk).exists())
        self.assertEqual(stats.avg_score, 90)
        self.assertEqual(leaderboard.total_score, 90)
        self.assertEqual(student_row['cells'][0]['score'], 90)

    def test_gradebook_combines_code_file_and_quiz_scores(self):
        self.submission.manual_score = 90
        self.submission.status = 'finished'
        self.submission.save(update_fields=['manual_score', 'status'])
        file_assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Nop file',
            description='Mo ta',
            instructions='Nop PDF',
            submission_mode=Assignments.SUBMISSION_FILE,
            grading_mode=Assignments.GRADING_MANUAL,
            type='project',
            max_score=100,
            is_published=True,
            created_by=self.teacher,
        )
        quiz_assignment = Assignments.objects.create(
            classroom=self.classroom,
            title='Quiz',
            description='Mo ta',
            instructions='Lam quiz',
            submission_mode=Assignments.SUBMISSION_QUIZ,
            grading_mode=Assignments.GRADING_AUTO,
            type='auto_grade',
            max_score=10,
            is_published=True,
            created_by=self.teacher,
        )
        Submissions.objects.create(
            assignment=file_assignment,
            student=self.student,
            submission_mode_snapshot=Assignments.SUBMISSION_FILE,
            status='finished',
            manual_score=80,
            max_score=100,
        )
        Submissions.objects.create(
            assignment=quiz_assignment,
            student=self.student,
            submission_mode_snapshot=Assignments.SUBMISSION_QUIZ,
            language='quiz',
            status='finished',
            total_score=7,
            max_score=10,
        )

        factory = RequestFactory()
        request = factory.get(reverse('classrooms:gradebook', kwargs={'pk': self.classroom.pk}))
        from apps.classrooms.views import _build_gradebook_data
        gradebook = _build_gradebook_data(self.classroom, request)
        student_row = next(row for row in gradebook['rows'] if row['student'].pk == self.student.pk)
        scores = [cell['score'] for cell in student_row['cells'] if cell['has_score']]

        self.client.force_login(self.teacher)
        export_response = self.client.get(reverse('classrooms:gradebook_export', kwargs={'pk': self.classroom.pk}))
        export_content = export_response.content.decode('utf-8-sig')

        self.assertEqual(student_row['completed_count'], 3)
        self.assertEqual(scores, [90, 80, 7])
        self.assertEqual(student_row['avg_score'], 59)
        self.assertIn('Bai tap 1 [Lập trình]', export_content)
        self.assertIn('Nop file [Nộp file]', export_content)
        self.assertIn('Quiz [Trắc nghiệm]', export_content)

    def test_grades_are_hidden_until_teacher_releases_them(self):
        self.submission.manual_score = 88
        self.submission.teacher_comment = 'Da cham.'
        self.submission.graded_by = self.teacher
        self.submission.graded_at = timezone.now()
        self.submission.status = 'finished'
        self.submission.save(update_fields=[
            'manual_score', 'teacher_comment', 'graded_by', 'graded_at', 'status',
        ])

        self.client.force_login(self.student)
        hidden_response = self.client.get(reverse('submissions:detail', kwargs={'pk': self.submission.pk}))
        self.assertEqual(hidden_response.status_code, 200)
        self.assertContains(hidden_response, 'Chờ công bố')
        self.assertNotContains(hidden_response, '88.0')

        self.client.force_login(self.teacher)
        release_response = self.client.post(
            reverse('assignments:release_grades', kwargs={'pk': self.assignment.pk}),
            {'show_feedback_after_release': '1'},
        )
        self.assertEqual(release_response.status_code, 302)
        self.assignment.refresh_from_db()
        self.assertIsNotNone(self.assignment.grades_released_at)

        self.client.force_login(self.student)
        visible_response = self.client.get(reverse('submissions:detail', kwargs={'pk': self.submission.pk}))
        self.assertEqual(visible_response.status_code, 200)
        self.assertContains(visible_response, '88.0')

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

    def test_quiz_exam_uses_exam_session_single_attempt_autosave_and_force_submit(self):
        self.submission.delete()
        self.assignment.submission_mode = Assignments.SUBMISSION_QUIZ
        self.assignment.grading_mode = Assignments.GRADING_AUTO
        self.assignment.is_exam = True
        self.assignment.exam_duration_minutes = 30
        self.assignment.max_attempts = 1
        self.assignment.max_score = 2
        self.assignment.save(update_fields=[
            'submission_mode', 'grading_mode', 'is_exam',
            'exam_duration_minutes', 'max_attempts', 'max_score',
        ])
        QuizSettings.objects.create(
            assignment=self.assignment,
            show_score_after_submit=False,
            show_correct_answers=False,
            allow_review=False,
        )
        question = QuizQuestions.objects.create(
            assignment=self.assignment,
            question_text='Django là framework Python?',
            question_type=QuizQuestions.TYPE_TRUE_FALSE,
            points=2,
        )
        correct_choice = QuizChoices.objects.create(
            question=question,
            choice_text='Đúng',
            is_correct=True,
            order_index=1,
        )
        QuizChoices.objects.create(
            question=question,
            choice_text='Sai',
            is_correct=False,
            order_index=2,
        )

        self.client.force_login(self.student)
        start_response = self.client.post(
            reverse('submissions:start_exam', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(start_response.status_code, 302)
        session = ExamSessions.objects.get(assignment=self.assignment, student=self.student)
        attempt = QuizAttempts.objects.get(assignment=self.assignment, student=self.student)
        self.assertEqual(session.status, ExamSessions.STATUS_RUNNING)
        self.assertEqual(attempt.exam_session, session)
        self.assertEqual(attempt.attempt_no, 1)

        start_again = self.client.post(
            reverse('submissions:start_exam', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(start_again.status_code, 302)
        self.assertEqual(QuizAttempts.objects.filter(assignment=self.assignment, student=self.student).count(), 1)

        ide_response = self.client.get(
            reverse('submissions:exam_ide', kwargs={'assignment_pk': self.assignment.pk})
        )
        self.assertEqual(ide_response.status_code, 302)
        self.assertIn(reverse('submissions:quiz_take', kwargs={'attempt_pk': attempt.pk}), ide_response.headers['Location'])

        take_response = self.client.get(reverse('submissions:quiz_take', kwargs={'attempt_pk': attempt.pk}))
        self.assertEqual(take_response.status_code, 200)
        self.assertContains(take_response, 'Phòng thi trắc nghiệm')

        autosave_response = self.client.post(
            reverse('submissions:quiz_autosave', kwargs={'attempt_pk': attempt.pk}),
            data=json.dumps({
                'question_id': question.pk,
                'selected_choice_ids': [correct_choice.pk],
            }),
            content_type='application/json',
        )
        event_response = self.client.post(
            reverse('submissions:exam_event', kwargs={'assignment_pk': self.assignment.pk}),
            data=json.dumps({'event_type': 'tab_hidden', 'metadata': {'attempt_id': attempt.pk}}),
            content_type='application/json',
        )
        self.assertEqual(autosave_response.status_code, 200)
        self.assertEqual(event_response.status_code, 200)
        self.assertTrue(ExamEvents.objects.filter(session=session, event_type='answer_saved').exists())
        self.assertTrue(ExamEvents.objects.filter(session=session, event_type='tab_hidden').exists())

        submit_response = self.client.post(
            reverse('submissions:quiz_submit', kwargs={'attempt_pk': attempt.pk}),
            {f'question_{question.pk}': str(correct_choice.pk)},
        )
        self.assertEqual(submit_response.status_code, 302)
        session.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(session.status, ExamSessions.STATUS_SUBMITTED)
        self.assertIsNotNone(session.final_submission)
        self.assertEqual(attempt.status, QuizAttempts.STATUS_SUBMITTED)
        self.assertEqual(attempt.score, 2)
        self.assertEqual(session.final_submission.submission_mode_snapshot, Assignments.SUBMISSION_QUIZ)

        result_response = self.client.get(reverse('submissions:quiz_result', kwargs={'attempt_pk': attempt.pk}))
        self.assertEqual(result_response.status_code, 200)
        self.assertContains(result_response, 'Chờ công bố')

        self.client.force_login(self.other_student)
        self.client.post(reverse('submissions:start_exam', kwargs={'assignment_pk': self.assignment.pk}))
        other_session = ExamSessions.objects.get(assignment=self.assignment, student=self.other_student)
        other_attempt = QuizAttempts.objects.get(assignment=self.assignment, student=self.other_student)

        self.client.force_login(self.teacher)
        force_response = self.client.post(
            reverse('submissions:force_submit_exam_session', kwargs={'session_pk': other_session.pk})
        )
        self.assertEqual(force_response.status_code, 302)
        other_session.refresh_from_db()
        other_attempt.refresh_from_db()
        self.assertEqual(other_session.status, ExamSessions.STATUS_AUTO_SUBMITTED)
        self.assertIsNotNone(other_session.final_submission)
        self.assertEqual(other_attempt.status, QuizAttempts.STATUS_AUTO_SUBMITTED)
        self.assertTrue(ExamEvents.objects.filter(session=other_session, event_type='teacher_force_submit').exists())
        self.assertTrue(Notifications.objects.filter(
            recipient=self.teacher,
            notification_type='exam_auto_submitted',
            metadata__attempt_id=other_attempt.pk,
        ).exists())

        monitor_response = self.client.get(reverse('submissions:exam_monitor', kwargs={'assignment_pk': self.assignment.pk}))
        self.assertEqual(monitor_response.status_code, 200)
        self.assertContains(monitor_response, 'Trắc nghiệm')
        self.assertContains(monitor_response, 'Đã trả lời')

    def test_quiz_exam_expired_session_auto_submits_attempt(self):
        self.submission.delete()
        self.assignment.submission_mode = Assignments.SUBMISSION_QUIZ
        self.assignment.grading_mode = Assignments.GRADING_AUTO
        self.assignment.is_exam = True
        self.assignment.exam_duration_minutes = 30
        self.assignment.exam_grace_seconds = 0
        self.assignment.max_attempts = 1
        self.assignment.max_score = 2
        self.assignment.save(update_fields=[
            'submission_mode', 'grading_mode', 'is_exam',
            'exam_duration_minutes', 'exam_grace_seconds', 'max_attempts', 'max_score',
        ])
        QuizSettings.objects.create(
            assignment=self.assignment,
            show_score_after_submit=False,
            show_correct_answers=False,
            allow_review=False,
        )
        question = QuizQuestions.objects.create(
            assignment=self.assignment,
            question_text='Python la ngon ngu lap trinh?',
            question_type=QuizQuestions.TYPE_TRUE_FALSE,
            points=2,
        )
        correct_choice = QuizChoices.objects.create(
            question=question,
            choice_text='Dung',
            is_correct=True,
            order_index=1,
        )
        QuizChoices.objects.create(question=question, choice_text='Sai', is_correct=False, order_index=2)
        session = ExamSessions.objects.create(
            assignment=self.assignment,
            student=self.student,
            status=ExamSessions.STATUS_RUNNING,
            started_at=timezone.now() - timedelta(minutes=40),
            ends_at=timezone.now() - timedelta(minutes=1),
        )
        attempt = QuizAttempts.objects.create(
            assignment=self.assignment,
            student=self.student,
            exam_session=session,
            attempt_no=1,
            status=QuizAttempts.STATUS_IN_PROGRESS,
            started_at=timezone.now() - timedelta(minutes=40),
        )
        answer = QuizAnswers.objects.create(
            attempt=attempt,
            question=question,
            selected_choice_ids=[correct_choice.pk],
            answered_at=timezone.now() - timedelta(minutes=2),
        )
        answer.selected_choices.add(correct_choice)
        self.client.force_login(self.student)

        response = self.client.get(reverse('submissions:quiz_take', kwargs={'attempt_pk': attempt.pk}))

        session.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(session.status, ExamSessions.STATUS_AUTO_SUBMITTED)
        self.assertEqual(attempt.status, QuizAttempts.STATUS_AUTO_SUBMITTED)
        self.assertEqual(attempt.score, 2)
        self.assertIsNotNone(session.final_submission_id)
        self.assertTrue(ExamEvents.objects.filter(session=session, event_type='auto_submit').exists())

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
