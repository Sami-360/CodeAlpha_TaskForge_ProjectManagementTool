from notifications.models import Notification


def notify_user(
    *,
    recipient,
    notification_type,
    message,
    sender=None,
    project=None,
    task=None,
):
    if recipient is None or (sender and recipient.pk == sender.pk):
        return None
    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        message=message,
        project=project,
        task=task,
    )


def notify_users(*, recipients, **notification_data):
    created = []
    seen_ids = set()
    for recipient in recipients:
        if recipient is None or recipient.pk in seen_ids:
            continue
        seen_ids.add(recipient.pk)
        notification = notify_user(recipient=recipient, **notification_data)
        if notification:
            created.append(notification)
    return created
