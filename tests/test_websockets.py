from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application
from notifications.models import Notification
from notifications.services import notify_user
from projects.models import Project, ProjectMember


@override_settings(ALLOWED_HOSTS=['testserver'])
class WebSocketTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='socket-owner',
            email='socket-owner@example.com',
            password='StrongPass123!',
        )
        self.member = user_model.objects.create_user(
            username='socket-member',
            email='socket-member@example.com',
            password='StrongPass123!',
        )
        self.outsider = user_model.objects.create_user(
            username='socket-outsider',
            email='socket-outsider@example.com',
            password='StrongPass123!',
        )
        self.project = Project.objects.create(name='Socket project', owner=self.owner)
        ProjectMember.objects.create(
            project=self.project,
            user=self.member,
            role=ProjectMember.Role.MEMBER,
            added_by=self.owner,
        )

    def communicator(self, path):
        return WebsocketCommunicator(
            application,
            path,
            headers=[(b'origin', b'http://testserver')],
        )

    async def authenticate(self, communicator, user):
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        self.assertEqual(
            await communicator.receive_json_from(),
            {'type': 'authentication_required'},
        )
        await communicator.send_json_to(
            {'type': 'authenticate', 'token': str(AccessToken.for_user(user))}
        )
        return await communicator.receive_json_from()

    async def test_project_member_receives_board_event(self):
        communicator = self.communicator(f'/ws/projects/{self.project.pk}/board/')
        self.assertEqual(
            await self.authenticate(communicator, self.member),
            {'type': 'authenticated'},
        )
        await get_channel_layer().group_send(
            f'project.{self.project.pk}',
            {
                'type': 'realtime.event',
                'payload': {
                    'type': 'task_updated',
                    'project_id': self.project.pk,
                    'data': {'id': 10},
                },
            },
        )
        event = await communicator.receive_json_from()
        self.assertEqual(event['type'], 'task_updated')
        self.assertEqual(event['data']['id'], 10)
        await communicator.disconnect()

    async def test_project_outsider_is_rejected(self):
        communicator = self.communicator(f'/ws/projects/{self.project.pk}/board/')
        response = await self.authenticate(communicator, self.outsider)
        self.assertEqual(response['type'], 'authorization_error')

    async def test_invalid_access_token_is_rejected(self):
        communicator = self.communicator('/ws/notifications/')
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_json_from()
        await communicator.send_json_to({'type': 'authenticate', 'token': 'invalid'})
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'authentication_error')

    async def test_notification_service_broadcasts_to_recipient(self):
        communicator = self.communicator('/ws/notifications/')
        self.assertEqual(
            await self.authenticate(communicator, self.member),
            {'type': 'authenticated'},
        )
        await sync_to_async(notify_user)(
            recipient=self.member,
            sender=self.owner,
            notification_type=Notification.Type.MEMBER_ADDED,
            message='You were added to a project.',
            project=self.project,
        )
        event = await communicator.receive_json_from()
        self.assertEqual(event['type'], 'notification_created')
        self.assertEqual(event['data']['message'], 'You were added to a project.')
        await communicator.disconnect()
