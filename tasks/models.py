from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from tasks.validators import attachment_upload_path, validate_attachment

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
    previous_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        blank=True,
    )
    position = models.PositiveIntegerField(default=0)
    labels = models.ManyToManyField(
        'projects.ProjectLabel',
        blank=True,
        related_name='tasks',
    )
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


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='task_attachments',
    )
    file = models.FileField(upload_to=attachment_upload_path, validators=[validate_attachment])
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def save(self, *args, **kwargs):
        """Keep upload metadata valid for admin and programmatic uploads."""
        if self.file:
            if not self.file_size:
                self.file_size = self.file.size
            if not self.original_name:
                from pathlib import Path

                self.original_name = Path(self.file.name).name[:255]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name


class TaskChecklist(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='checklists')
    title = models.CharField(max_length=150)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_task_checklists',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.task.title}: {self.title}'


class ChecklistItem(models.Model):
    checklist = models.ForeignKey(
        TaskChecklist,
        on_delete=models.CASCADE,
        related_name='items',
    )
    text = models.CharField(max_length=300)
    is_completed = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_checklist_items',
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'created_at']

    def __str__(self):
        return self.text


@receiver(post_delete, sender=TaskAttachment)
def delete_attachment_file(sender, instance, **kwargs):
    if instance.file and instance.file.name:
        try:
            instance.file.storage.delete(instance.file.name)
        except OSError:
            pass
