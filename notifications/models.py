from django.conf import settings
from django.db import models

from projects.models import Project
from tasks.models import Task


class Notification(models.Model):
    class Type(models.TextChoices):
        PROJECT_INVITATION = 'project_invitation', 'Project invitation'
        MEMBER_ADDED = 'member_added', 'Member added'
        TASK_ASSIGNED = 'task_assigned', 'Task assigned'
        TASK_UPDATED = 'task_updated', 'Task updated'
        TASK_STATUS_CHANGED = 'task_status_changed', 'Task status changed'
        NEW_COMMENT = 'new_comment', 'New comment'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
    )
    notification_type = models.CharField(max_length=40, choices=Type.choices)
    message = models.CharField(max_length=500)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read', '-created_at'])]

    def __str__(self):
        return f'{self.recipient.username}: {self.message}'
