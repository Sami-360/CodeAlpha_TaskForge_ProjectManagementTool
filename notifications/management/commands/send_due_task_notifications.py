from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Notification
from notifications.services import notify_user
from tasks.models import Task


class Command(BaseCommand):
    help = 'Create one due-soon or overdue notification per task and recipient.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        due_soon_end = today + timedelta(days=2)
        tasks = Task.objects.exclude(status=Task.Status.DONE).filter(
            due_date__isnull=False
        ).select_related('project__owner', 'assigned_to')
        created = 0

        for task in tasks:
            if task.due_date < today:
                notification_type = Notification.Type.TASK_OVERDUE
                message = f'Task "{task.title}" is overdue.'
            elif task.due_date <= due_soon_end:
                notification_type = Notification.Type.DUE_SOON
                message = f'Task "{task.title}" is due on {task.due_date.isoformat()}.'
            else:
                continue

            recipients = {task.project.owner_id: task.project.owner}
            if task.assigned_to_id:
                recipients[task.assigned_to_id] = task.assigned_to
            for recipient in recipients.values():
                already_sent = Notification.objects.filter(
                    recipient=recipient,
                    task=task,
                    notification_type=notification_type,
                ).exists()
                if not already_sent:
                    notify_user(
                        recipient=recipient,
                        notification_type=notification_type,
                        message=message,
                        project=task.project,
                        task=task,
                    )
                    created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} due-task notification(s).'))
