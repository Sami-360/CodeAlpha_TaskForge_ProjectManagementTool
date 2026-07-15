from functools import partial

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction


def _send(group_name, payload):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {'type': 'realtime.event', 'payload': payload},
        )


def broadcast_project_event(project_id, event_type, data):
    payload = {'type': event_type, 'project_id': project_id, 'data': data}
    transaction.on_commit(partial(_send, f'project.{project_id}', payload))


def broadcast_notification_event(notification):
    payload = {
        'type': 'notification_created',
        'data': {
            'id': notification.pk,
            'notification_type': notification.notification_type,
            'message': notification.message,
            'project_id': notification.project_id,
            'task_id': notification.task_id,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
        },
    }
    transaction.on_commit(partial(_send, f'user.{notification.recipient_id}', payload))
