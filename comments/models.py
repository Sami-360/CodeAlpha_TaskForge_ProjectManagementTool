from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from tasks.models import Task


class Comment(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_comments',
    )
    message = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def clean(self):
        super().clean()
        self.message = self.message.strip()
        if not self.message:
            raise ValidationError({'message': 'Comment message cannot be empty.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} on {self.task.title}'
