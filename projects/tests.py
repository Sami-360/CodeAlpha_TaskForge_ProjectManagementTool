from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from projects.models import Project, ProjectMember
from tasks.models import Task

User = get_user_model()


class ProjectAPITests(APITestCase):
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

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_project(self, name='TaskForge'):
        return Project.objects.create(name=name, owner=self.owner)

    def test_authenticated_user_can_create_project(self):
        self.authenticate(self.owner)

        response = self.client.post(
            reverse('project-list'),
            {'name': 'CodeAlpha Task 3', 'description': 'Collaborative tool'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner']['username'], 'owner')
        self.assertEqual(response.data['current_user_role'], ProjectMember.Role.OWNER)

    def test_project_creation_adds_owner_membership(self):
        self.authenticate(self.owner)
        response = self.client.post(
            reverse('project-list'), {'name': 'TaskForge'}, format='json'
        )

        membership = ProjectMember.objects.get(project_id=response.data['id'])
        self.assertEqual(membership.user, self.owner)
        self.assertEqual(membership.role, ProjectMember.Role.OWNER)
        self.assertEqual(membership.added_by, self.owner)

    def test_unauthenticated_project_creation_is_rejected(self):
        response = self.client.post(
            reverse('project-list'), {'name': 'TaskForge'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_projects_they_belong_to(self):
        shared = self.create_project('Shared')
        private = Project.objects.create(name='Private', owner=self.other)
        ProjectMember.objects.create(project=shared, user=self.member)
        self.authenticate(self.member)

        response = self.client.get(reverse('project-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {project['id'] for project in response.data}
        self.assertEqual(returned_ids, {shared.id})
        self.assertNotIn(private.id, returned_ids)

    def test_owner_can_update_project(self):
        project = self.create_project()
        self.authenticate(self.owner)

        response = self.client.patch(
            reverse('project-detail', args=[project.id]),
            {'name': 'Updated TaskForge'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        project.refresh_from_db()
        self.assertEqual(project.name, 'Updated TaskForge')

    def test_non_owner_cannot_delete_project(self):
        project = self.create_project()
        ProjectMember.objects.create(project=project, user=self.member)
        self.authenticate(self.member)

        response = self.client.delete(reverse('project-detail', args=[project.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())

    def test_owner_can_delete_project(self):
        project = self.create_project()
        self.authenticate(self.owner)

        response = self.client.delete(reverse('project-detail', args=[project.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())

    def test_owner_can_add_member_by_email(self):
        project = self.create_project()
        self.authenticate(self.owner)

        response = self.client.post(
            reverse('project-member-list', args=[project.id]),
            {'identifier': 'MEMBER@EXAMPLE.COM', 'role': ProjectMember.Role.MEMBER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'member')
        self.assertTrue(
            ProjectMember.objects.filter(project=project, user=self.member).exists()
        )

    def test_duplicate_member_is_rejected(self):
        project = self.create_project()
        ProjectMember.objects.create(project=project, user=self.member)
        self.authenticate(self.owner)

        response = self.client.post(
            reverse('project-member-list', args=[project.id]),
            {'identifier': 'member', 'role': ProjectMember.Role.MANAGER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_owner_cannot_manage_membership(self):
        project = self.create_project()
        member_record = ProjectMember.objects.create(project=project, user=self.member)
        self.authenticate(self.member)

        response = self.client.patch(
            reverse('project-member-detail', args=[project.id, member_record.id]),
            {'role': ProjectMember.Role.MANAGER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        member_record.refresh_from_db()
        self.assertEqual(member_record.role, ProjectMember.Role.MEMBER)

    def test_owner_membership_cannot_be_removed(self):
        project = self.create_project()
        owner_membership = project.memberships.get(user=self.owner)
        self.authenticate(self.owner)

        response = self.client.delete(
            reverse('project-member-detail', args=[project.id, owner_membership.id])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(ProjectMember.objects.filter(pk=owner_membership.pk).exists())

    def test_owner_can_update_non_owner_role(self):
        project = self.create_project()
        member_record = ProjectMember.objects.create(project=project, user=self.member)
        self.authenticate(self.owner)

        response = self.client.patch(
            reverse('project-member-detail', args=[project.id, member_record.id]),
            {'role': ProjectMember.Role.MANAGER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        member_record.refresh_from_db()
        self.assertEqual(member_record.role, ProjectMember.Role.MANAGER)

    def test_global_search_is_membership_scoped(self):
        visible = self.create_project('Visible launch')
        hidden = Project.objects.create(name='Hidden launch', owner=self.other)
        ProjectMember.objects.create(project=visible, user=self.member)
        visible_task = Task.objects.create(
            project=visible, title='Launch checklist', created_by=self.owner
        )
        Task.objects.create(
            project=hidden, title='Launch secret', created_by=self.other
        )
        self.authenticate(self.member)

        response = self.client.get(reverse('global-search'), {'q': 'launch'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data['projects']], [visible.id])
        self.assertEqual([item['id'] for item in response.data['tasks']], [visible_task.id])

    def test_global_search_requires_meaningful_query(self):
        self.authenticate(self.owner)

        response = self.client.get(reverse('global-search'), {'q': 'a'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
