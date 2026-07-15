from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from tasks.models import Task


class CollaborationFlowTests(APITestCase):
    password = 'StrongPass123!'

    def register(self, username):
        response = self.client.post(
            reverse('auth-register'),
            {
                'username': username,
                'email': f'{username}@example.com',
                'first_name': username.title(),
                'last_name': 'User',
                'password': self.password,
                'password_confirm': self.password,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def use_access_token(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_complete_two_user_collaboration_flow(self):
        user_a = self.register('usera')
        user_b = self.register('userb')
        outsider = self.register('outsider')

        self.use_access_token(user_a['access'])
        project_response = self.client.post(
            reverse('project-list'),
            {'name': 'CodeAlpha Task 3', 'description': 'Integration project'},
            format='json',
        )
        self.assertEqual(project_response.status_code, status.HTTP_201_CREATED)
        project_id = project_response.data['id']

        member_response = self.client.post(
            reverse('project-member-list', args=[project_id]),
            {'identifier': 'userb@example.com', 'role': 'member'},
            format='json',
        )
        self.assertEqual(member_response.status_code, status.HTTP_201_CREATED)

        task_response = self.client.post(
            reverse('task-list', args=[project_id]),
            {
                'title': 'Build project board',
                'assigned_to_id': user_b['user']['id'],
                'priority': 'high',
            },
            format='json',
        )
        self.assertEqual(task_response.status_code, status.HTTP_201_CREATED)
        task_id = task_response.data['id']

        self.use_access_token(user_b['access'])
        member_project = self.client.get(reverse('project-detail', args=[project_id]))
        self.assertEqual(member_project.status_code, status.HTTP_200_OK)

        status_response = self.client.patch(
            reverse('task-status', args=[task_id]),
            {'status': Task.Status.IN_PROGRESS},
            format='json',
        )
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)

        comment_response = self.client.post(
            reverse('comment-list', args=[task_id]),
            {'message': 'Board implementation has started.'},
            format='json',
        )
        self.assertEqual(comment_response.status_code, status.HTTP_201_CREATED)

        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.data['assigned_tasks'], 1)

        self.use_access_token(user_a['access'])
        comments_response = self.client.get(reverse('comment-list', args=[task_id]))
        self.assertEqual(comments_response.status_code, status.HTTP_200_OK)
        self.assertEqual(comments_response.data[0]['user']['username'], 'userb')

        notifications_response = self.client.get(reverse('notification-list'))
        self.assertEqual(notifications_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(notifications_response.data['unread_count'], 1)

        self.use_access_token(outsider['access'])
        outsider_project = self.client.get(reverse('project-detail', args=[project_id]))
        outsider_tasks = self.client.get(reverse('task-list', args=[project_id]))
        self.assertEqual(outsider_project.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(outsider_tasks.status_code, status.HTTP_404_NOT_FOUND)
