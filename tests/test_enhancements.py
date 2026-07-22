import shutil
import tempfile
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from notifications.models import Notification
from projects.models import Project, ProjectActivity, ProjectMember
from tasks.models import Task, TaskAttachment

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='taskforge-test-media-')


def image_upload(name='avatar.png'):
    stream = BytesIO()
    Image.new('RGB', (32, 32), '#087f6b').save(stream, format='PNG')
    return SimpleUploadedFile(name, stream.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class EnhancementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_user('enh-owner', 'owner@enh.test', 'StrongPass123!')
        cls.member = user_model.objects.create_user('enh-member', 'member@enh.test', 'StrongPass123!')
        cls.viewer = user_model.objects.create_user('enh-viewer', 'viewer@enh.test', 'StrongPass123!')
        cls.outsider = user_model.objects.create_user('enh-outsider', 'outsider@enh.test', 'StrongPass123!')
        cls.project = Project.objects.create(name='Enhancement project', owner=cls.owner)
        ProjectMember.objects.create(project=cls.project, user=cls.member, role='member', added_by=cls.owner)
        ProjectMember.objects.create(project=cls.project, user=cls.viewer, role='member', added_by=cls.owner)
        cls.task = Task.objects.create(
            project=cls.project,
            title='Enhanced task',
            created_by=cls.owner,
            assigned_to=cls.member,
            priority=Task.Priority.HIGH,
            due_date=timezone.localdate() + timedelta(days=1),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def test_valid_avatar_upload_statistics_and_protected_fields(self):
        self.authenticate(self.member)
        response = self.client.patch(
            '/api/auth/me/',
            {'avatar': image_upload(), 'first_name': 'Enhanced', 'username': 'changed', 'is_superuser': True},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.member.refresh_from_db()
        self.assertTrue(self.member.avatar.name.startswith(f'avatars/{self.member.pk}/'))
        self.assertEqual(self.member.username, 'enh-member')
        self.assertFalse(self.member.is_superuser)
        self.assertEqual(response.data['projects_joined_count'], 1)
        self.assertEqual(response.data['tasks_assigned_count'], 1)
        self.assertEqual(response.data['pending_tasks_count'], 1)

    def test_invalid_and_oversized_avatars_are_rejected(self):
        self.authenticate(self.member)
        invalid = SimpleUploadedFile('avatar.gif', b'not-an-image', content_type='image/gif')
        self.assertEqual(self.client.patch('/api/auth/me/', {'avatar': invalid}, format='multipart').status_code, 400)
        oversized = SimpleUploadedFile('large.png', b'x' * (5 * 1024 * 1024 + 1), content_type='image/png')
        response = self.client.patch('/api/auth/me/', {'avatar': oversized}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('5 MB', str(response.data))

    def test_avatar_replacement_and_delete_remove_physical_files(self):
        self.authenticate(self.member)
        self.client.patch('/api/auth/me/', {'avatar': image_upload('first.png')}, format='multipart')
        self.member.refresh_from_db()
        old_path = Path(self.member.avatar.path)
        self.assertTrue(old_path.exists())
        self.client.patch('/api/auth/me/', {'avatar': image_upload('second.png')}, format='multipart')
        self.assertFalse(old_path.exists())
        self.member.refresh_from_db()
        current_path = Path(self.member.avatar.path)
        response = self.client.delete('/api/auth/me/avatar/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(current_path.exists())
        self.assertFalse(response.data['avatar'])

    def test_attachment_upload_download_permissions_and_physical_delete(self):
        self.authenticate(self.member)
        upload = SimpleUploadedFile('notes.txt', b'project notes', content_type='text/plain')
        response = self.client.post(f'/api/tasks/{self.task.pk}/attachments/', {'file': upload}, format='multipart')
        self.assertEqual(response.status_code, 201)
        attachment = TaskAttachment.objects.get(pk=response.data['id'])
        file_path = Path(attachment.file.path)
        self.assertTrue(file_path.exists())
        self.authenticate(self.outsider)
        self.assertEqual(self.client.get(f'/api/task-attachments/{attachment.pk}/download/').status_code, 404)
        self.authenticate(self.viewer)
        self.assertEqual(self.client.delete(f'/api/task-attachments/{attachment.pk}/').status_code, 403)
        self.authenticate(self.member)
        self.assertEqual(self.client.delete(f'/api/task-attachments/{attachment.pk}/').status_code, 204)
        self.assertFalse(file_path.exists())
        activity = ProjectActivity.objects.get(
            action=ProjectActivity.Action.ATTACHMENT_DELETED,
            task=self.task,
        )
        self.assertEqual(activity.metadata['filename'], 'notes.txt')
        self.assertFalse(
            ProjectActivity.objects.filter(
                action=ProjectActivity.Action.CHECKLIST_UPDATED,
                task=self.task,
            ).exists()
        )

    def test_attachment_download_is_project_member_only(self):
        attachment = TaskAttachment.objects.create(
            task=self.task,
            uploaded_by=self.member,
            file=SimpleUploadedFile('download.txt', b'download', content_type='text/plain'),
            original_name='download.txt',
            file_size=8,
        )
        self.authenticate(self.outsider)
        self.assertEqual(self.client.get(f'/api/task-attachments/{attachment.pk}/download/').status_code, 404)
        self.authenticate(self.member)
        response = self.client.get(f'/api/task-attachments/{attachment.pk}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="download.txt"')

    def test_attachment_validation_rejects_extension_and_size(self):
        self.authenticate(self.member)
        invalid = SimpleUploadedFile('script.exe', b'data', content_type='application/octet-stream')
        self.assertEqual(self.client.post(f'/api/tasks/{self.task.pk}/attachments/', {'file': invalid}, format='multipart').status_code, 400)
        large = SimpleUploadedFile('large.txt', b'x' * (10 * 1024 * 1024 + 1), content_type='text/plain')
        self.assertEqual(self.client.post(f'/api/tasks/{self.task.pk}/attachments/', {'file': large}, format='multipart').status_code, 400)

    def test_checklist_permissions_toggle_and_progress(self):
        self.authenticate(self.owner)
        response = self.client.post(f'/api/tasks/{self.task.pk}/checklists/', {'title': 'Release'}, format='json')
        self.assertEqual(response.status_code, 201)
        checklist_id = response.data['id']
        self.authenticate(self.member)
        item_response = self.client.post(f'/api/checklists/{checklist_id}/items/', {'text': 'Run tests', 'position': 0}, format='json')
        self.assertEqual(item_response.status_code, 201)
        item_id = item_response.data['id']
        self.assertEqual(self.client.patch(f'/api/checklist-items/{item_id}/toggle/', {}, format='json').status_code, 200)
        result = self.client.get(f'/api/tasks/{self.task.pk}/checklists/').data[0]
        self.assertEqual(result['completed_percentage'], 100)
        self.authenticate(self.viewer)
        self.assertEqual(self.client.patch(f'/api/checklist-items/{item_id}/toggle/', {}, format='json').status_code, 403)

    def test_label_validation_assignment_filter_and_outsider_access(self):
        self.authenticate(self.owner)
        create = self.client.post(f'/api/projects/{self.project.pk}/labels/', {'name': 'Backend', 'color': '#175CD3'}, format='json')
        self.assertEqual(create.status_code, 201)
        label_id = create.data['id']
        self.assertEqual(self.client.post(f'/api/projects/{self.project.pk}/labels/', {'name': 'backend', 'color': '#175CD3'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'/api/projects/{self.project.pk}/labels/', {'name': 'Bad', 'color': 'red'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.pk}/labels/', {'label_ids': [label_id]}, format='json').status_code, 200)
        filtered = self.client.get(f'/api/projects/{self.project.pk}/tasks/?label={label_id}').data
        self.assertEqual([item['id'] for item in filtered], [self.task.pk])
        self.authenticate(self.outsider)
        self.assertEqual(self.client.get(f'/api/projects/{self.project.pk}/labels/').status_code, 404)

    def test_activity_creation_order_and_outsider_rejection(self):
        self.authenticate(self.owner)
        self.client.post(
            f'/api/projects/{self.project.pk}/tasks/',
            {'title': 'Activity task', 'priority': 'medium'},
            format='json',
        )
        response = self.client.get(f'/api/projects/{self.project.pk}/activities/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['action'], ProjectActivity.Action.TASK_CREATED)
        self.authenticate(self.outsider)
        self.assertEqual(self.client.get(f'/api/projects/{self.project.pk}/activities/').status_code, 404)

    def test_project_search_role_sort_and_task_filters(self):
        self.authenticate(self.owner)
        projects = self.client.get('/api/projects/?search=Enhancement&role=owner&sort=alphabetical')
        self.assertEqual([item['id'] for item in projects.data], [self.project.pk])
        tasks = self.client.get(f'/api/projects/{self.project.pk}/tasks/?search=Enhanced&priority=high&due_this_week=true')
        self.assertEqual([item['id'] for item in tasks.data], [self.task.pk])

    def test_complete_and_reopen_preserve_previous_status(self):
        self.authenticate(self.member)
        self.task.status = Task.Status.IN_PROGRESS
        self.task.save()
        complete = self.client.patch(f'/api/tasks/{self.task.pk}/complete/', {}, format='json')
        self.assertEqual(complete.data['status'], Task.Status.DONE)
        self.assertEqual(complete.data['due_state'], 'completed')
        reopen = self.client.patch(f'/api/tasks/{self.task.pk}/reopen/', {}, format='json')
        self.assertEqual(reopen.data['status'], Task.Status.IN_PROGRESS)

    def test_dashboard_insights_are_scoped_and_complete(self):
        self.authenticate(self.member)
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joined_projects'], 1)
        self.assertEqual(response.data['total_assigned_tasks'], 1)
        self.assertEqual(response.data['tasks_due_this_week'], 1)
        self.assertEqual(response.data['priority_distribution']['high'], 1)
        self.assertEqual(response.data['workload_by_project'][0]['project_id'], self.project.pk)

    def test_due_notification_command_is_idempotent(self):
        output = StringIO()
        call_command('send_due_task_notifications', stdout=output)
        first_count = Notification.objects.filter(task=self.task, notification_type=Notification.Type.DUE_SOON).count()
        call_command('send_due_task_notifications', stdout=output)
        self.assertEqual(first_count, 2)
        self.assertEqual(Notification.objects.filter(task=self.task, notification_type=Notification.Type.DUE_SOON).count(), 2)
        self.assertIn('Created 0 due-task notification(s).', output.getvalue())

    def test_taskforge_admin_branding_loads(self):
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TaskForge Administration')
        self.assertContains(response, 'taskforge_admin.css')

    def test_taskforge_admin_has_fixed_model_navigation_without_arrow_toggle(self):
        self.owner.is_staff = True
        self.owner.is_superuser = True
        self.owner.save(update_fields=['is_staff', 'is_superuser'])
        self.client.force_login(self.owner)

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin-nav-groups')
        self.assertContains(response, 'admin-model-link', count=12)
        self.assertNotContains(response, 'toggle-nav-sidebar')

    def test_admin_attachment_upload_populates_required_metadata(self):
        self.owner.is_staff = True
        self.owner.is_superuser = True
        self.owner.save(update_fields=['is_staff', 'is_superuser'])
        self.client.force_login(self.owner)
        upload = SimpleUploadedFile(
            'admin-notes.txt',
            b'Admin attachment content',
            content_type='text/plain',
        )

        response = self.client.post(
            '/admin/tasks/taskattachment/add/',
            {'task': self.task.pk, 'uploaded_by': self.owner.pk, 'file': upload},
        )

        self.assertEqual(response.status_code, 302)
        attachment = TaskAttachment.objects.get(original_name='admin-notes.txt')
        self.assertEqual(attachment.file_size, 24)
