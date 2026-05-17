from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Profiles, TeacherRegistrations
from apps.administation.models import (
    ActivityLogs,
    ProgrammingLanguages,
    SandboxConfigs,
    ServerMetrics,
    SystemSettings,
)
from apps.assignments.models import (
    AssignmentFiles,
    AssignmentStatistics,
    Assignments,
    PlagiarismReports,
    Rubrics,
    Testcases,
)
from apps.classrooms.models import (
    Announcements,
    ClassroomApprovalStatus,
    ClassroomMembers,
    Classrooms,
    ClassroomSubjects,
    Leaderboard,
    Semesters,
    SubjectApprovalStatus,
    Subjects,
)
from apps.discussions.models import Discussions, DiscussionVotes
from apps.notifications.models import Notifications
from apps.submissions.models import (
    CodeComments,
    CodeDrafts,
    ExamEvents,
    ExamSessions,
    FeedbackTemplates,
    RubricScores,
    SubmissionDetails,
    Submissions,
)
from apps.submissions.utils import update_assignment_statistics, update_classroom_leaderboard


class Command(BaseCommand):
    help = 'Reset non-user data and seed a complete LMS demo dataset.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Confirm destructive reset of non-user data.',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            raise CommandError('This command deletes non-user data. Re-run with --yes to confirm.')

        with transaction.atomic():
            people = self._resolve_people()
            self._reset_non_user_data()
            data = self._seed_base(people)
            self._seed_classroom_content(data)
            self._seed_submissions_and_exam(data, people)
            self._seed_discussions_and_notifications(data, people)
            self._seed_admin_operational_data(data, people)

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
        self._print_summary()

    def _resolve_people(self):
        for user in User.objects.all():
            Profiles.objects.get_or_create(
                id=user,
                defaults={'role': 'admin' if user.is_superuser else 'student', 'status': 'approved'},
            )

        admin = (
            User.objects.filter(is_superuser=True).order_by('id').first()
            or User.objects.filter(profiles__role='admin').order_by('id').first()
        )
        if not admin:
            raise CommandError('Need at least one admin/superuser user before seeding demo data.')
        for superuser in User.objects.filter(is_superuser=True):
            superuser.profiles.role = 'admin'
            superuser.profiles.status = 'approved'
            superuser.profiles.save(update_fields=['role', 'status', 'updated_at'])

        teacher = User.objects.filter(profiles__role='teacher').exclude(pk=admin.pk).order_by('id').first()
        if not teacher:
            teacher = User.objects.exclude(pk=admin.pk).order_by('id').first()
            if not teacher:
                raise CommandError('Need at least one non-admin user to act as teacher.')
            teacher.profiles.role = 'teacher'
            teacher.profiles.status = 'approved'
            teacher.profiles.save(update_fields=['role', 'status', 'updated_at'])

        students = list(User.objects.filter(profiles__role='student').exclude(pk__in=[admin.pk, teacher.pk]).order_by('id')[:2])
        if len(students) < 2:
            candidates = list(User.objects.exclude(pk__in=[admin.pk, teacher.pk]).exclude(pk__in=[u.pk for u in students]).order_by('id'))
            for user in candidates:
                user.profiles.role = 'student'
                user.profiles.status = 'approved'
                user.profiles.save(update_fields=['role', 'status', 'updated_at'])
                students.append(user)
                if len(students) == 2:
                    break
        if len(students) < 2:
            raise CommandError('Need at least two student-capable users before seeding demo data.')

        pending_teacher = User.objects.exclude(pk__in=[admin.pk, teacher.pk, students[0].pk]).order_by('id').first() or students[-1]
        pending_teacher.profiles.status = 'approved'
        pending_teacher.profiles.save(update_fields=['status', 'updated_at'])

        return {
            'admin': admin,
            'teacher': teacher,
            'students': students,
            'pending_teacher': pending_teacher,
        }

    def _reset_non_user_data(self):
        # Delete children first. Keep auth.User and accounts.Profiles intact.
        ordered_models = [
            DiscussionVotes,
            Discussions,
            Notifications,
            ExamEvents,
            ExamSessions,
            RubricScores,
            CodeComments,
            SubmissionDetails,
            CodeDrafts,
            FeedbackTemplates,
            Submissions,
            PlagiarismReports,
            AssignmentStatistics,
            AssignmentFiles,
            Testcases,
            Rubrics,
            Assignments,
            Leaderboard,
            Announcements,
            ClassroomMembers,
            ClassroomSubjects,
            Subjects,
            Semesters,
            Classrooms,
            TeacherRegistrations,
            ActivityLogs,
            ServerMetrics,
            SystemSettings,
            SandboxConfigs,
            ProgrammingLanguages,
        ]
        for model in ordered_models:
            model.objects.all().delete()

    def _seed_base(self, people):
        admin = people['admin']
        teacher = people['teacher']
        student_a, student_b = people['students']
        now = timezone.now()
        today = timezone.localdate()

        languages = {
            'python': ProgrammingLanguages.objects.create(
                name='python',
                display_name='Python',
                version='3.11',
                file_extension='.py',
                syntax_highlight_mode='python',
                default_template='print("Hello, LH Programming!")',
            ),
            'javascript': ProgrammingLanguages.objects.create(
                name='javascript',
                display_name='JavaScript',
                version='Node 20',
                file_extension='.js',
                syntax_highlight_mode='javascript',
                default_template='console.log("Hello, LH Programming!");',
            ),
            'cpp': ProgrammingLanguages.objects.create(
                name='cpp',
                display_name='C++',
                version='C++17',
                file_extension='.cpp',
                syntax_highlight_mode='cpp',
                default_template='#include <bits/stdc++.h>\nusing namespace std;\nint main(){ return 0; }',
            ),
        }

        SandboxConfigs.objects.bulk_create([
            SandboxConfigs(language='python', docker_image='python:3.11-alpine', timeout_seconds=5, memory_limit_mb=256, cpu_limit=1.0),
            SandboxConfigs(language='javascript', docker_image='node:20-alpine', timeout_seconds=5, memory_limit_mb=256, cpu_limit=1.0),
            SandboxConfigs(language='cpp', docker_image='gcc:13-bookworm', timeout_seconds=8, memory_limit_mb=512, cpu_limit=1.0),
        ])

        SystemSettings.objects.bulk_create([
            SystemSettings(setting_key='exam.default_grace_seconds', setting_value=30, description='Grace period mac dinh cho bai thi.', updated_by=admin),
            SystemSettings(setting_key='exam.require_fullscreen_default', setting_value=True, description='Mac dinh yeu cau fullscreen khi tao bai thi.', updated_by=admin),
            SystemSettings(setting_key='exam.allow_custom_input_default', setting_value=False, description='Mac dinh custom input trong bai thi.', updated_by=admin),
            SystemSettings(setting_key='notifications.due_soon_hours', setting_value=24, description='So gio nhac han truoc deadline.', updated_by=admin),
            SystemSettings(setting_key='sandbox.zombie_threshold_minutes', setting_value=15, description='Nguong submission running qua lau.', updated_by=admin),
            SystemSettings(setting_key='uploads.assignment_max_mb', setting_value=10, description='Dung luong toi da file bai tap.', updated_by=admin),
        ])

        current_semester = Semesters.objects.create(
            code='HK2_2026',
            name='Hoc ky 2 - 2025-2026',
            start_date=today - timedelta(days=60),
            end_date=today + timedelta(days=60),
            is_current=True,
            is_active=True,
        )
        next_semester = Semesters.objects.create(
            code='HK_HE_2026',
            name='Hoc ky he - 2026',
            start_date=today + timedelta(days=75),
            end_date=today + timedelta(days=135),
            is_current=False,
            is_active=True,
        )

        python_subject = Subjects.objects.create(
            code='PY101',
            name='Lap trinh Python co ban',
            description='Bien, cau truc dieu khien, ham va list.',
            status=SubjectApprovalStatus.APPROVED,
            created_by=teacher,
            approved_by=admin,
            reviewed_at=now,
            is_active=True,
        )
        python_subject.languages.set([languages['python']])

        ds_subject = Subjects.objects.create(
            code='DS201',
            name='Cau truc du lieu va giai thuat',
            description='Mang, stack, queue, sorting va do phuc tap.',
            status=SubjectApprovalStatus.APPROVED,
            created_by=teacher,
            approved_by=admin,
            reviewed_at=now,
            is_active=True,
        )
        ds_subject.languages.set([languages['python'], languages['cpp']])

        web_subject = Subjects.objects.create(
            code='WEB301',
            name='Lap trinh Web voi Django',
            description='View, template, model va authentication.',
            status=SubjectApprovalStatus.APPROVED,
            created_by=teacher,
            approved_by=admin,
            reviewed_at=now,
            is_active=True,
        )
        web_subject.languages.set([languages['python'], languages['javascript']])

        pending_subject = Subjects.objects.create(
            code='AI401',
            name='Nhap mon AI ung dung',
            description='Subject mau dang cho admin duyet.',
            status=SubjectApprovalStatus.PENDING,
            created_by=teacher,
            is_active=True,
        )
        pending_subject.languages.set([languages['python']])

        python_class = Classrooms.objects.create(
            name='Python co ban K18',
            description='Lop demo cho workflow hoc sinh lam bai va giao vien cham diem.',
            invite_code='PYK18DEMO',
            teacher=teacher,
            max_students=40,
            status=ClassroomApprovalStatus.APPROVED,
            approved_by=admin,
            reviewed_at=now,
            is_active=True,
            settings={'join_requires_approval': False},
        )
        web_class = Classrooms.objects.create(
            name='Django Web K18',
            description='Lop demo co yeu cau giao vien duyet hoc sinh vao lop.',
            invite_code='WEB18DMO',
            teacher=teacher,
            max_students=35,
            status=ClassroomApprovalStatus.APPROVED,
            approved_by=admin,
            reviewed_at=now,
            is_active=True,
            settings={'join_requires_approval': True},
        )
        pending_class = Classrooms.objects.create(
            name='Cau truc du lieu K19',
            description='Lop mau dang cho admin duyet.',
            invite_code='DSK19DMO',
            teacher=teacher,
            max_students=45,
            status=ClassroomApprovalStatus.PENDING,
            is_active=False,
            settings={'join_requires_approval': True},
        )

        python_link = ClassroomSubjects.objects.create(
            classroom=python_class,
            subject=python_subject,
            semester=current_semester,
            assigned_by=teacher,
            is_active=True,
        )
        ds_link = ClassroomSubjects.objects.create(
            classroom=python_class,
            subject=ds_subject,
            semester=current_semester,
            assigned_by=teacher,
            is_active=True,
        )
        web_link = ClassroomSubjects.objects.create(
            classroom=web_class,
            subject=web_subject,
            semester=current_semester,
            assigned_by=teacher,
            is_active=True,
        )
        ClassroomSubjects.objects.create(
            classroom=pending_class,
            subject=ds_subject,
            semester=next_semester,
            assigned_by=teacher,
            is_active=True,
        )

        # Supabase projects upgraded from the old schema may still keep
        # classroom_members.status as a PostgreSQL enum. Individual inserts are
        # friendlier to that column than Django's bulk INSERT ... UNNEST.
        for classroom, student, status in [
            (python_class, student_a, 'approved'),
            (python_class, student_b, 'approved'),
            (web_class, student_a, 'approved'),
            (web_class, student_b, 'pending'),
        ]:
            ClassroomMembers.objects.create(classroom=classroom, student=student, status=status)

        Announcements.objects.bulk_create([
            Announcements(classroom=python_class, teacher=teacher, title='Chao mung lop Python K18', content='Tuan nay hoan thanh bai Hello Python va doc rubric cham diem.', is_pinned=True),
            Announcements(classroom=python_class, teacher=teacher, title='Lich hoc buoi 2', content='Buoi sau on list, loop va function.', is_pinned=False),
            Announcements(classroom=web_class, teacher=teacher, title='Chuan bi moi truong Django', content='Cai Python, pip va tao virtualenv truoc buoi hoc.', is_pinned=True),
        ])

        TeacherRegistrations.objects.create(
            user=people['pending_teacher'],
            institution='Demo University',
            reason='Muon mo lop Python nang cao cho hoc sinh.',
            status='pending',
        )

        return {
            'now': now,
            'languages': languages,
            'current_semester': current_semester,
            'python_class': python_class,
            'web_class': web_class,
            'pending_class': pending_class,
            'python_link': python_link,
            'ds_link': ds_link,
            'web_link': web_link,
        }

    def _seed_classroom_content(self, data):
        teacher = data['python_class'].teacher
        now = data['now']

        hello = Assignments.objects.create(
            classroom=data['python_class'],
            classroom_subject=data['python_link'],
            title='Hello Python va phep cong',
            description='Doc input gom hai so nguyen va in tong.',
            instructions='Nhap hai so a b tren mot dong, in ra a + b.',
            type='auto_grade',
            difficulty='easy',
            allowed_languages=['python'],
            start_date=now - timedelta(days=7),
            due_date=now + timedelta(days=5),
            late_submission_allowed=True,
            late_penalty_percent=10,
            max_score=100,
            max_attempts=5,
            show_testcase_result=True,
            enable_leaderboard=True,
            is_published=True,
            created_by=teacher,
        )
        Testcases.objects.bulk_create([
            Testcases(assignment=hello, name='Sample 1', input_data='1 2', expected_output='3', is_sample=True, is_hidden=False, weight=1, order_index=0),
            Testcases(assignment=hello, name='Hidden positive', input_data='10 25', expected_output='35', is_sample=False, is_hidden=True, weight=2, order_index=1),
            Testcases(assignment=hello, name='Hidden negative', input_data='-3 7', expected_output='4', is_sample=False, is_hidden=True, weight=2, order_index=2),
        ])
        Rubrics.objects.bulk_create([
            Rubrics(assignment=hello, name='Doc input dung', description='Xu ly dung dinh dang dau vao.', max_points=20, order_index=1),
            Rubrics(assignment=hello, name='Ket qua dung', description='Tinh va in tong chinh xac.', max_points=70, order_index=2),
            Rubrics(assignment=hello, name='Code gon gang', description='Dat bien ro rang, khong hard-code.', max_points=10, order_index=3),
        ])
        AssignmentFiles.objects.create(
            assignment=hello,
            file_name='hello-python-huong-dan.pdf',
            file_url='https://example.com/demo/hello-python-huong-dan.pdf',
            file_size=256000,
            mime_type='application/pdf',
        )

        project = Assignments.objects.create(
            classroom=data['web_class'],
            classroom_subject=data['web_link'],
            title='Mini project: Blog Django',
            description='Xay dung blog co danh sach bai viet va chi tiet bai viet.',
            instructions='Nop link repository hoac paste code chinh. Giao vien cham theo rubric.',
            type='project',
            difficulty='medium',
            allowed_languages=['python', 'javascript'],
            start_date=now - timedelta(days=3),
            due_date=now + timedelta(days=14),
            late_submission_allowed=True,
            late_penalty_percent=5,
            max_score=100,
            max_attempts=2,
            show_testcase_result=False,
            enable_leaderboard=False,
            is_published=True,
            created_by=teacher,
        )
        Rubrics.objects.bulk_create([
            Rubrics(assignment=project, name='Model va migration', max_points=25, order_index=1),
            Rubrics(assignment=project, name='View/template dung yeu cau', max_points=35, order_index=2),
            Rubrics(assignment=project, name='UX va validation', max_points=25, order_index=3),
            Rubrics(assignment=project, name='Clean code', max_points=15, order_index=4),
        ])

        exam = Assignments.objects.create(
            classroom=data['python_class'],
            classroom_subject=data['ds_link'],
            title='Bai thi giua ky: Sorting co ban',
            description='Viet chuong trinh sap xep day so tang dan.',
            instructions='Input: n va n so nguyen. Output: day so da sap xep tang dan.',
            type='auto_grade',
            difficulty='medium',
            allowed_languages=['python', 'cpp'],
            start_date=now - timedelta(days=1),
            due_date=now + timedelta(days=2),
            max_score=100,
            max_attempts=1,
            show_testcase_result=False,
            enable_leaderboard=True,
            is_published=True,
            is_exam=True,
            exam_duration_minutes=45,
            exam_start_time=now - timedelta(hours=2),
            exam_end_time=now + timedelta(days=2),
            exam_require_fullscreen=True,
            exam_allow_custom_input=False,
            exam_allow_sample_run=True,
            exam_max_run_count=3,
            exam_grace_seconds=30,
            created_by=teacher,
        )
        Testcases.objects.bulk_create([
            Testcases(assignment=exam, name='Sample sort', input_data='5\n3 1 5 2 4', expected_output='1 2 3 4 5', is_sample=True, is_hidden=False, weight=1, order_index=0),
            Testcases(assignment=exam, name='Hidden duplicates', input_data='6\n2 2 1 3 1 4', expected_output='1 1 2 2 3 4', is_sample=False, is_hidden=True, weight=2, order_index=1),
            Testcases(assignment=exam, name='Hidden negative', input_data='5\n0 -1 9 -3 2', expected_output='-3 -1 0 2 9', is_sample=False, is_hidden=True, weight=2, order_index=2),
        ])

        draft = Assignments.objects.create(
            classroom=data['python_class'],
            classroom_subject=data['python_link'],
            title='Draft: Ham va module',
            description='Bai nhap chua cong bo de demo checklist publish.',
            instructions='Viet ham tinh giai thua.',
            type='auto_grade',
            difficulty='easy',
            allowed_languages=['python'],
            max_score=100,
            max_attempts=3,
            is_published=False,
            created_by=teacher,
        )
        Testcases.objects.create(
            assignment=draft,
            name='Sample factorial',
            input_data='5',
            expected_output='120',
            is_sample=True,
            is_hidden=False,
            weight=1,
            order_index=0,
        )

        return {
            'hello': hello,
            'project': project,
            'exam': exam,
            'draft': draft,
        }

    def _seed_submissions_and_exam(self, data, people):
        assignments = {assignment.title: assignment for assignment in Assignments.objects.all()}
        hello = assignments['Hello Python va phep cong']
        project = assignments['Mini project: Blog Django']
        exam = assignments['Bai thi giua ky: Sorting co ban']
        teacher = people['teacher']
        student_a, student_b = people['students']
        now = data['now']

        feedback_template = FeedbackTemplates.objects.create(
            teacher=teacher,
            title='Can xu ly edge case',
            category='logic',
            content='Bai lam dung y tuong, nhung can bo sung edge case va format output.',
        )

        sub_a = Submissions.objects.create(
            assignment=hello,
            student=student_a,
            code_content='a, b = map(int, input().split())\nprint(a + b)',
            language='python',
            status='finished',
            total_score=100,
            max_score=100,
            passed_testcases=3,
            total_testcases=3,
            execution_time=120,
            memory_usage=12,
        )
        sub_b = Submissions.objects.create(
            assignment=hello,
            student=student_b,
            code_content='a, b = map(int, input().split())\nprint(a - b)',
            language='python',
            status='finished',
            total_score=20,
            max_score=100,
            passed_testcases=1,
            total_testcases=3,
            execution_time=110,
            memory_usage=11,
            manual_score=35,
            teacher_comment='Can doc ky de bai: yeu cau tinh tong, khong phai hieu.',
            graded_by=teacher,
            graded_at=now,
        )

        for submission in (sub_a, sub_b):
            for testcase in Testcases.objects.filter(assignment=hello).order_by('order_index'):
                passed = submission == sub_a or testcase.is_sample
                SubmissionDetails.objects.create(
                    submission=submission,
                    testcase=testcase,
                    result_status='passed' if passed else 'failed',
                    actual_output=testcase.expected_output if passed else 'sai ket qua',
                    execution_time=40,
                    memory_usage=10,
                    error_message='' if passed else 'Expected output khong khop.',
                    score_earned=(testcase.weight / 5) * 100 if passed else 0,
                )

        rubrics = list(Rubrics.objects.filter(assignment=hello).order_by('order_index'))
        for rubric, score in zip(rubrics, [10, 15, 10]):
            RubricScores.objects.create(submission=sub_b, rubric=rubric, score=score, comment='Demo rubric score.')

        CodeComments.objects.create(
            submission=sub_b,
            teacher=teacher,
            line_number=2,
            comment_text='Dong nay dang tru hai so, can doi thanh cong.',
            is_resolved=False,
        )

        project_sub = Submissions.objects.create(
            assignment=project,
            student=student_a,
            code_content='https://github.com/demo/blog-django',
            language='python',
            status='finished',
            total_score=0,
            max_score=100,
            manual_score=88,
            teacher_comment='Project co luong CRUD tot, can them test va pagination.',
            graded_by=teacher,
            graded_at=now,
        )
        for rubric, score in zip(Rubrics.objects.filter(assignment=project).order_by('order_index'), [22, 30, 22, 14]):
            RubricScores.objects.create(submission=project_sub, rubric=rubric, score=score)

        CodeDrafts.objects.create(
            assignment=exam,
            student=student_b,
            language='python',
            code_content='n = int(input())\na = list(map(int, input().split()))\nprint(*sorted(a))',
        )

        exam_submission = Submissions.objects.create(
            assignment=exam,
            student=student_a,
            code_content='n = int(input())\na = list(map(int, input().split()))\nprint(*sorted(a))',
            language='python',
            status='finished',
            total_score=100,
            max_score=100,
            passed_testcases=3,
            total_testcases=3,
            execution_time=150,
            memory_usage=15,
        )
        submitted_session = ExamSessions.objects.create(
            assignment=exam,
            student=student_a,
            final_submission=exam_submission,
            status=ExamSessions.STATUS_SUBMITTED,
            started_at=now - timedelta(minutes=35),
            ends_at=now + timedelta(minutes=10),
            submitted_at=now - timedelta(minutes=5),
            last_seen_at=now - timedelta(minutes=5),
            current_language='python',
            latest_draft=exam_submission.code_content,
            ip_address='127.0.0.1',
            user_agent='Demo Browser',
            run_count=2,
            violation_count=1,
        )
        running_session = ExamSessions.objects.create(
            assignment=exam,
            student=student_b,
            status=ExamSessions.STATUS_RUNNING,
            started_at=now - timedelta(minutes=12),
            ends_at=now + timedelta(minutes=33),
            last_seen_at=now,
            current_language='python',
            latest_draft='n = int(input())\na = list(map(int, input().split()))\nprint(*sorted(a))',
            ip_address='127.0.0.1',
            user_agent='Demo Browser',
            run_count=1,
            violation_count=2,
        )
        ExamEvents.objects.bulk_create([
            ExamEvents(session=submitted_session, event_type='started', metadata={'ip': '127.0.0.1'}),
            ExamEvents(session=submitted_session, event_type='focus_lost', metadata={'visible': False}),
            ExamEvents(session=submitted_session, event_type='submitted', metadata={'submission_id': exam_submission.pk, 'score': 100}),
            ExamEvents(session=running_session, event_type='started', metadata={'ip': '127.0.0.1'}),
            ExamEvents(session=running_session, event_type='tab_hidden', metadata={'visible': False}),
            ExamEvents(session=running_session, event_type='paste', metadata={'length': 24}),
        ])

        for assignment in (hello, project, exam):
            update_assignment_statistics(assignment)
        update_classroom_leaderboard(data['python_class'])
        update_classroom_leaderboard(data['web_class'])

        PlagiarismReports.objects.create(
            assignment=hello,
            created_by=teacher,
            status='finished',
            threshold=0.85,
            language='python',
            result=[
                {
                    'submission_a': sub_a.pk,
                    'submission_b': sub_b.pk,
                    'similarity_score': 0.62,
                    'text_score': 0.58,
                    'token_score': 0.66,
                    'structural_score': 0.61,
                    'is_suspicious': False,
                }
            ],
            submissions_count=2,
            pairs_count=1,
            suspicious_count=0,
            finished_at=now,
        )

        return {
            'feedback_template': feedback_template,
            'sub_a': sub_a,
            'sub_b': sub_b,
            'project_sub': project_sub,
            'exam_submission': exam_submission,
        }

    def _seed_discussions_and_notifications(self, data, people):
        teacher = people['teacher']
        student_a, student_b = people['students']
        hello = Assignments.objects.get(title='Hello Python va phep cong')
        exam = Assignments.objects.get(title='Bai thi giua ky: Sorting co ban')

        topic = Discussions.objects.create(
            assignment=hello,
            user=student_a,
            content='# Em bi sai hidden test\n\nEm da pass sample nhung hidden test bi wrong answer, em nen kiem tra gi?',
        )
        answer = Discussions.objects.create(
            assignment=hello,
            user=teacher,
            parent=topic,
            content='Em thu test voi so am va khoang trang cuoi dong. Nho dung phep cong thay vi hard-code sample.',
            is_answer=True,
            upvotes=1,
        )
        reply = Discussions.objects.create(
            assignment=exam,
            user=student_b,
            content='# Format output bai thi sorting\n\nOutput co can xuong dong cuoi khong a?',
        )
        DiscussionVotes.objects.create(discussion=answer, user=student_a, vote_type=1)
        DiscussionVotes.objects.create(discussion=topic, user=student_b, vote_type=1)

        Notifications.objects.bulk_create([
            Notifications(recipient=student_a, actor=teacher, notification_type='assignment_published', title='Bai tap moi: Hello Python va phep cong', message='Lop Python co ban K18 vua cong bo bai moi.', link=f'/assignments/{hello.pk}/', metadata={'assignment_id': hello.pk}),
            Notifications(recipient=student_b, actor=teacher, notification_type='submission_graded', title='Bai nop da duoc cham', message='Diem cua ban da duoc cap nhat.', link=f'/submissions/detail/{Submissions.objects.get(assignment=hello, student=student_b).pk}/', metadata={'assignment_id': hello.pk}),
            Notifications(recipient=teacher, actor=student_a, notification_type='submission_submitted', title='Bai nop moi', message=f'{student_a.username} vua nop bai Hello Python.', link=f'/submissions/teacher-list/{hello.pk}/', metadata={'assignment_id': hello.pk}),
            Notifications(recipient=teacher, actor=student_b, notification_type='discussion_replied', title='Cau hoi moi trong bai thi', message='Hoc sinh co cau hoi ve format output.', link=f'/discussions/{reply.pk}/', metadata={'discussion_id': reply.pk}),
        ])

    def _seed_admin_operational_data(self, data, people):
        admin = people['admin']
        teacher = people['teacher']
        now = data['now']

        for i in range(8):
            ServerMetrics.objects.create(
                cpu_usage=20 + i * 3,
                memory_usage=35 + i * 2,
                active_containers=1 + (i % 3),
                queue_length=i % 4,
                avg_execution_time=120 + i * 15,
            )

        ActivityLogs.objects.bulk_create([
            ActivityLogs(user=admin, action='POST /administration/classrooms/bulk/', resource_type='administation', resource_id=data['python_class'].pk, ip_address='127.0.0.1', user_agent='Demo Browser', metadata={'status_code': 302, 'action': 'approve'}),
            ActivityLogs(user=teacher, action='POST /assignments/demo/publish/', resource_type='assignments', resource_id=Assignments.objects.get(title='Hello Python va phep cong').pk, ip_address='127.0.0.1', user_agent='Demo Browser', metadata={'status_code': 302}),
            ActivityLogs(user=teacher, action='POST /submissions/grade/demo/', resource_type='submissions', resource_id=Submissions.objects.order_by('id').first().pk, ip_address='127.0.0.1', user_agent='Demo Browser', metadata={'status_code': 302}),
        ])

        # Keep an intentionally old-ish metric in the narrative via metadata.
        Notifications.objects.create(
            recipient=admin,
            actor=None,
            notification_type='sandbox_zombie_detected',
            title='Sandbox task co the bi treo',
            message='Submission demo dang running qua nguong can kiem tra.',
            link='/administration/sandbox-monitor/',
            metadata={'seeded_at': now.isoformat()},
        )

    def _print_summary(self):
        counts = {
            'users_kept': User.objects.count(),
            'profiles_kept': Profiles.objects.count(),
            'languages': ProgrammingLanguages.objects.count(),
            'classrooms': Classrooms.objects.count(),
            'members': ClassroomMembers.objects.count(),
            'subjects': Subjects.objects.count(),
            'assignments': Assignments.objects.count(),
            'testcases': Testcases.objects.count(),
            'submissions': Submissions.objects.count(),
            'exam_sessions': ExamSessions.objects.count(),
            'discussions': Discussions.objects.count(),
            'notifications': Notifications.objects.count(),
        }
        for key, value in counts.items():
            self.stdout.write(f'{key}: {value}')
