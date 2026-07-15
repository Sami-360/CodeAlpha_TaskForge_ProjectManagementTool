from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from projects.models import Project, ProjectMember


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'todo', 'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_tasks',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    due_date = models.DateField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', 'position', '-created_at']
        indexes = [
            models.Index(fields=['project', 'status', 'position']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date']),
        ]

    def clean(self):
        super().clean()
        if self.project_id and self.created_by_id:
            if not ProjectMember.objects.filter(
                project_id=self.project_id,
                user_id=self.created_by_id,
            ).exists():
                raise ValidationError(
                    {'created_by': 'Task creator must be a project member.'}
                )
        if self.project_id and self.assigned_to_id:
            if not ProjectMember.objects.filter(
                project_id=self.project_id,
                user_id=self.assigned_to_id,
            ).exists():
                raise ValidationError(
                    {'assigned_to': 'Assigned user must be a project member.'}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.project.name}: {self.title}'
