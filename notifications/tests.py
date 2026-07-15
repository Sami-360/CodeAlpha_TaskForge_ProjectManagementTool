from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from notifications.models import Notification
from projects.models import Project, ProjectMember
from tasks.models import Task

User = get_user_model()


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner', email='owner@example.com', password='StrongPass123!'
        )
        self.member = User.objects.create_user(
            username='member', email='member@example.com', password='StrongPass123!'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='StrongPass123!'
        )
        self.project = Project.objects.create(name='TaskForge', owner=self.owner)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def add_member(self):
        self.authenticate(self.owner)
        return self.client.post(
            reverse('project-member-list', args=[self.project.id]),
            {'identifier': self.member.username, 'role': ProjectMember.Role.MEMBER},
            format='json',
        )

    def test_member_addition_creates_notification(self):
        response = self.add_member()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get(recipient=self.member)
        self.assertEqual(notification.notification_type, Notification.Type.MEMBER_ADDED)

    def test_task_assignment_creates_notification(self):
        self.add_member()
        Notification.objects.all().delete()
        self.authenticate(self.owner)

        response = self.client.post(
            reverse('task-list', args=[self.project.id]),
            {'title': 'Assigned task', 'assigned_to_id': self.member.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.member,
                notification_type=Notification.Type.TASK_ASSIGNED,
            ).exists()
        )

    def test_comment_creates_notification(self):
        self.add_member()
        task = Task.objects.create(
            project=self.project,
            title='Discuss task',
            created_by=self.owner,
            assigned_to=self.member,
        )
        Notification.objects.all().delete()
        self.authenticate(self.member)

        response = self.client.post(
            reverse('comment-list', args=[task.id]),
            {'message': 'Progress update'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner,
                notification_type=Notification.Type.NEW_COMMENT,
            ).exists()
        )

    def test_user_sees_only_own_notifications(self):
        Notification.objects.create(
            recipient=self.member,
            notification_type=Notification.Type.MEMBER_ADDED,
            message='Member notification',
        )
        Notification.objects.create(
            recipient=self.other,
            notification_type=Notification.Type.MEMBER_ADDED,
            message='Other notification',
        )
        self.authenticate(self.member)

        response = self.client.get(reverse('notification-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['message'], 'Member notification')

    def test_mark_read_only_updates_current_users_notification(self):
        own = Notification.objects.create(
            recipient=self.member,
            notification_type=Notification.Type.TASK_UPDATED,
            message='Own',
        )
        other = Notification.objects.create(
            recipient=self.other,
            notification_type=Notification.Type.TASK_UPDATED,
            message='Other',
        )
        self.authenticate(self.member)

        own_response = self.client.patch(reverse('notification-read', args=[own.id]))
        other_response = self.client.patch(reverse('notification-read', args=[other.id]))

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)
        own.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(own.is_read)
        self.assertFalse(other.is_read)

    def test_mark_all_read_updates_only_current_user(self):
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient=self.member,
                    notification_type=Notification.Type.TASK_UPDATED,
                    message='One',
                ),
                Notification(
                    recipient=self.member,
                    notification_type=Notification.Type.NEW_COMMENT,
                    message='Two',
                ),
                Notification(
                    recipient=self.other,
                    notification_type=Notification.Type.TASK_UPDATED,
                    message='Other',
                ),
            ]
        )
        self.authenticate(self.member)

        response = self.client.patch(reverse('notification-read-all'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated'], 2)
        self.assertFalse(
            Notification.objects.filter(recipient=self.member, is_read=False).exists()
        )
        self.assertTrue(
            Notification.objects.filter(recipient=self.other, is_read=False).exists()
        )
