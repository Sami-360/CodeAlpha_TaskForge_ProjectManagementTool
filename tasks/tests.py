from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from projects.models import Project, ProjectMember
from tasks.models import Task

User = get_user_model()


class TaskAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner', email='owner@example.com', password='StrongPass123!'
        )
        self.manager = User.objects.create_user(
            username='manager', email='manager@example.com', password='StrongPass123!'
        )
        self.member = User.objects.create_user(
            username='member', email='member@example.com', password='StrongPass123!'
        )
        self.other_member = User.objects.create_user(
            username='othermember',
            email='othermember@example.com',
            password='StrongPass123!',
        )
        self.outsider = User.objects.create_user(
            username='outsider', email='outsider@example.com', password='StrongPass123!'
        )
        self.project = Project.objects.create(name='TaskForge', owner=self.owner)
        ProjectMember.objects.create(
            project=self.project,
            user=self.manager,
            role=ProjectMember.Role.MANAGER,
            added_by=self.owner,
        )
        ProjectMember.objects.create(
            project=self.project,
            user=self.member,
            role=ProjectMember.Role.MEMBER,
            added_by=self.owner,
        )
        ProjectMember.objects.create(
            project=self.project,
            user=self.other_member,
            role=ProjectMember.Role.MEMBER,
            added_by=self.owner,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def task_data(self, **overrides):
        data = {
            'title': 'Create dashboard UI',
            'description': 'Build responsive dashboard cards',
            'assigned_to_id': self.member.id,
            'status': Task.Status.TODO,
            'priority': Task.Priority.HIGH,
            'due_date': (timezone.localdate() + timedelta(days=7)).isoformat(),
        }
        data.update(overrides)
        return data

    def create_task(self, **overrides):
        data = {
            'project': self.project,
            'title': 'Task card',
            'created_by': self.owner,
            'assigned_to': self.member,
        }
        data.update(overrides)
        return Task.objects.create(**data)

    def test_owner_can_create_task(self):
        self.authenticate(self.owner)

        response = self.client.post(
            reverse('task-list', args=[self.project.id]),
            self.task_data(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['assigned_to']['username'], 'member')
        self.assertEqual(response.data['created_by']['username'], 'owner')

    def test_manager_can_create_task(self):
        self.authenticate(self.manager)

        response = self.client.post(
            reverse('task-list', args=[self.project.id]),
            self.task_data(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.get(pk=response.data['id']).created_by, self.manager)

    def test_member_cannot_create_task(self):
        self.authenticate(self.member)

        response = self.client.post(
            reverse('task-list', args=[self.project.id]),
            self.task_data(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assigned_user_must_be_project_member(self):
        self.authenticate(self.owner)

        response = self.client.post(
            reverse('task-list', args=[self.project.id]),
            self.task_data(assigned_to_id=self.outsider.id),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('assigned_to_id', response.data)

    def test_project_outsider_cannot_view_tasks(self):
        task = self.create_task()
        self.authenticate(self.outsider)

        list_response = self.client.get(reverse('task-list', args=[self.project.id]))
        detail_response = self.client.get(reverse('task-detail', args=[task.id]))

        self.assertEqual(list_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_edit_task(self):
        task = self.create_task()
        self.authenticate(self.manager)

        response = self.client.patch(
            reverse('task-detail', args=[task.id]),
            {'title': 'Updated task'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, 'Updated task')

    def test_member_cannot_edit_task_details(self):
        task = self.create_task()
        self.authenticate(self.member)

        response = self.client.patch(
            reverse('task-detail', args=[task.id]),
            {'priority': Task.Priority.LOW},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assigned_member_can_update_task_status(self):
        task = self.create_task()
        self.authenticate(self.member)

        response = self.client.patch(
            reverse('task-status', args=[task.id]),
            {'status': Task.Status.IN_PROGRESS},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.IN_PROGRESS)

    def test_unassigned_member_cannot_update_task_status(self):
        task = self.create_task()
        self.authenticate(self.other_member)

        response = self.client.patch(
            reverse('task-status', args=[task.id]),
            {'status': Task.Status.DONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_assign_task_to_project_member(self):
        task = self.create_task(assigned_to=None)
        self.authenticate(self.manager)

        response = self.client.patch(
            reverse('task-assign', args=[task.id]),
            {'assigned_to_id': self.other_member.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.assigned_to, self.other_member)

    def test_task_cannot_be_assigned_to_outsider(self):
        task = self.create_task(assigned_to=None)
        self.authenticate(self.owner)

        response = self.client.patch(
            reverse('task-assign', args=[task.id]),
            {'assigned_to_id': self.outsider.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        task.refresh_from_db()
        self.assertIsNone(task.assigned_to)

    def test_task_delete_permissions(self):
        task = self.create_task()
        self.authenticate(self.member)
        forbidden = self.client.delete(reverse('task-detail', args=[task.id]))
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.manager)
        allowed = self.client.delete(reverse('task-detail', args=[task.id]))
        self.assertEqual(allowed.status_code, status.HTTP_204_NO_CONTENT)

    def test_task_filters(self):
        overdue = self.create_task(
            title='Overdue high task',
            priority=Task.Priority.HIGH,
            due_date=timezone.localdate() - timedelta(days=1),
        )
        self.create_task(
            title='Completed task',
            status=Task.Status.DONE,
            priority=Task.Priority.LOW,
            due_date=timezone.localdate() - timedelta(days=2),
        )
        self.authenticate(self.member)

        response = self.client.get(
            reverse('task-list', args=[self.project.id]),
            {'priority': Task.Priority.HIGH, 'overdue': 'true'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data], [overdue.id])

    def test_manager_can_move_task_position_and_status(self):
        task = self.create_task()
        self.authenticate(self.manager)

        response = self.client.patch(
            reverse('task-position', args=[task.id]),
            {'status': Task.Status.DONE, 'position': 4},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)
        self.assertEqual(task.position, 4)
