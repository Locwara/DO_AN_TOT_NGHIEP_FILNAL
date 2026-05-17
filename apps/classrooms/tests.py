from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profiles
from apps.notifications.models import Notifications
from .models import ClassroomApprovalStatus, ClassroomMembers, Classrooms


class ClassroomJoinAndRoleTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='pass12345')
        Profiles.objects.create(id=self.teacher, role='teacher', status='approved')

        self.student = User.objects.create_user(username='student', password='pass12345')
        Profiles.objects.create(id=self.student, role='student', status='approved')

        self.other_student = User.objects.create_user(username='otherstudent', password='pass12345')
        Profiles.objects.create(id=self.other_student, role='student', status='approved')

        self.admin = User.objects.create_user(username='admin', password='pass12345', is_staff=True)
        Profiles.objects.create(id=self.admin, role='admin', status='approved')

        self.classroom = Classrooms.objects.create(
            name='Python co ban',
            invite_code='PYT001',
            teacher=self.teacher,
            status=ClassroomApprovalStatus.APPROVED,
            is_active=True,
        )

    def test_auth_role_matrix_for_core_classroom_routes(self):
        list_url = reverse('classrooms:classroom_list')
        detail_url = reverse('classrooms:classroom_detail', kwargs={'pk': self.classroom.pk})
        create_url = reverse('classrooms:create')

        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.headers['Location'])

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(list_url).status_code, 200)
        self.assertEqual(self.client.get(detail_url).status_code, 302)
        self.assertEqual(self.client.get(create_url).status_code, 302)

        ClassroomMembers.objects.create(
            classroom=self.classroom,
            student=self.student,
            status='approved',
        )
        self.assertEqual(self.client.get(detail_url).status_code, 200)

        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(create_url).status_code, 200)
        self.assertEqual(self.client.get(detail_url).status_code, 200)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('administation:dashboard')).status_code, 200)
        self.assertEqual(self.client.get(detail_url).status_code, 200)

    def test_join_classroom_auto_approve(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse('classrooms:join'),
            {'invite_code': self.classroom.invite_code},
        )

        member = ClassroomMembers.objects.get(classroom=self.classroom, student=self.student)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(member.status, 'approved')
        self.assertTrue(Notifications.objects.filter(
            recipient=self.teacher,
            notification_type='class_join_approved',
        ).exists())

    def test_join_classroom_pending_approval(self):
        self.classroom.settings = {'join_requires_approval': True}
        self.classroom.save(update_fields=['settings'])
        self.client.force_login(self.other_student)

        response = self.client.post(
            reverse('classrooms:join'),
            {'invite_code': self.classroom.invite_code},
        )

        member = ClassroomMembers.objects.get(classroom=self.classroom, student=self.other_student)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(member.status, 'pending')
        self.assertTrue(Notifications.objects.filter(
            recipient=self.teacher,
            notification_type='class_join_requested',
        ).exists())
