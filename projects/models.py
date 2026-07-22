from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.signals import post_save
from django.dispatch import receiver


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_projects',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.pk:
            original_owner_id = type(self).objects.filter(pk=self.pk).values_list(
                'owner_id', flat=True
            ).first()
            if original_owner_id and original_owner_id != self.owner_id:
                raise ValidationError('Project ownership transfer is not supported.')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MANAGER = 'manager', 'Manager'
        MEMBER = 'member', 'Member'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_project_memberships',
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['joined_at']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'user'],
                name='projects_unique_project_user',
            ),
            models.UniqueConstraint(
                fields=['project'],
                condition=Q(role='owner'),
                name='projects_one_owner_membership',
            ),
        ]

    def clean(self):
        super().clean()
        if self.role == self.Role.OWNER and self.user_id != self.project.owner_id:
            raise ValidationError({'role': 'Only the project owner can have the owner role.'})
        if self.user_id == self.project.owner_id and self.role != self.Role.OWNER:
            raise ValidationError({'role': 'The project owner must keep the owner role.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.role == self.Role.OWNER:
            raise ValidationError('The project owner membership cannot be removed.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} in {self.project.name} ({self.role})'


class ProjectLabel(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='labels')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_project_labels',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                'project',
                name='projects_unique_label_name_ci',
            )
        ]

    def __str__(self):
        return f'{self.project.name}: {self.name}'


class ProjectActivity(models.Model):
    class Action(models.TextChoices):
        PROJECT_CREATED = 'project_created', 'Project created'
        PROJECT_UPDATED = 'project_updated', 'Project updated'
        MEMBER_ADDED = 'member_added', 'Member added'
        MEMBER_REMOVED = 'member_removed', 'Member removed'
        MEMBER_ROLE_CHANGED = 'member_role_changed', 'Member role changed'
        TASK_CREATED = 'task_created', 'Task created'
        TASK_ASSIGNED = 'task_assigned', 'Task assigned'
        TASK_STATUS_CHANGED = 'task_status_changed', 'Task status changed'
        TASK_UPDATED = 'task_updated', 'Task updated'
        TASK_DELETED = 'task_deleted', 'Task deleted'
        COMMENT_ADDED = 'comment_added', 'Comment added'
        ATTACHMENT_ADDED = 'attachment_added', 'Attachment added'
        CHECKLIST_UPDATED = 'checklist_updated', 'Checklist updated'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_activities',
    )
    action = models.CharField(max_length=40, choices=Action.choices)
    task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='targeted_project_activities',
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['project', '-created_at'])]

    def __str__(self):
        return f'{self.project.name}: {self.get_action_display()}'


@receiver(post_save, sender=Project)
def ensure_owner_membership(sender, instance, created, **kwargs):
    if created:
        ProjectMember.objects.create(
            project=instance,
            user=instance.owner,
            role=ProjectMember.Role.OWNER,
            added_by=instance.owner,
        )
