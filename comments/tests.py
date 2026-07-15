from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from comments.models import Comment
from projects.models import Project, ProjectMember
from tasks.models import Task

User = get_user_model()


class CommentAPITests(APITestCase):
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
        self.outsider = User.objects.create_user(
            username='outsider', email='outsider@example.com', password='StrongPass123!'
        )
        self.project = Project.objects.create(name='TaskForge', owner=self.owner)
        ProjectMember.objects.create(
            project=self.project,
            user=self.manager,
            role=ProjectMember.Role.MANAGER,
        )
        ProjectMember.objects.create(project=self.project, user=self.member)
        self.task = Task.objects.create(
            project=self.project,
            title='Comment task',
            created_by=self.owner,
            assigned_to=self.member,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_project_member_can_comment(self):
        self.authenticate(self.member)

        response = self.client.post(
            reverse('comment-list', args=[self.task.id]),
            {'message': 'I started this task.'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'member')

    def test_outsider_cannot_comment_or_list(self):
        self.authenticate(self.outsider)

        list_response = self.client.get(reverse('comment-list', args=[self.task.id]))
        create_response = self.client.post(
            reverse('comment-list', args=[self.task.id]),
            {'message': 'Unauthorized'},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(create_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_comment_is_rejected(self):
        self.authenticate(self.member)

        response = self.client.post(
            reverse('comment-list', args=[self.task.id]),
            {'message': '   '},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_edit_own_comment(self):
        comment = Comment.objects.create(
            task=self.task, user=self.member, message='Original'
        )
        self.authenticate(self.member)

        response = self.client.patch(
            reverse('comment-detail', args=[comment.id]),
            {'message': 'Updated'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.message, 'Updated')

    def test_user_cannot_edit_another_users_comment(self):
        comment = Comment.objects.create(
            task=self.task, user=self.owner, message='Owner comment'
        )
        self.authenticate(self.member)

        response = self.client.patch(
            reverse('comment-detail', args=[comment.id]),
            {'message': 'Changed'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_and_manager_can_delete_comment(self):
        own_comment = Comment.objects.create(
            task=self.task, user=self.member, message='Own comment'
        )
        moderated_comment = Comment.objects.create(
            task=self.task, user=self.member, message='Moderated comment'
        )
        self.authenticate(self.member)
        own_response = self.client.delete(
            reverse('comment-detail', args=[own_comment.id])
        )
        self.assertEqual(own_response.status_code, status.HTTP_204_NO_CONTENT)

        self.authenticate(self.manager)
        manager_response = self.client.delete(
            reverse('comment-detail', args=[moderated_comment.id])
        )
        self.assertEqual(manager_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_comments_are_returned_oldest_first(self):
        first = Comment.objects.create(task=self.task, user=self.owner, message='First')
        second = Comment.objects.create(task=self.task, user=self.member, message='Second')
        self.authenticate(self.member)

        response = self.client.get(reverse('comment-list', args=[self.task.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data], [first.id, second.id])
