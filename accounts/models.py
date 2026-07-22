from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.db.models.functions import Lower

from accounts.validators import avatar_upload_path, validate_avatar


class UserManager(DjangoUserManager):
    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).strip().lower()

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError('The username must be set.')
        if not email:
            raise ValueError('The email must be set.')

        user = self.model(
            username=self.model.normalize_username(username),
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        validators=[validate_avatar],
        blank=True,
        null=True,
    )
    bio = models.CharField(max_length=300, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    class Meta:
        ordering = ['username']
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='accounts_user_email_ci_unique',
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = type(self).objects.normalize_email(self.email)
        previous_avatar = None
        if self.pk:
            previous_avatar = type(self).objects.filter(pk=self.pk).values_list(
                'avatar', flat=True
            ).first()
        super().save(*args, **kwargs)
        if previous_avatar and previous_avatar != self.avatar.name:
            self.avatar.storage.delete(previous_avatar)

    def remove_avatar(self):
        if not self.avatar:
            return
        storage = self.avatar.storage
        name = self.avatar.name
        self.avatar = None
        self.save(update_fields=['avatar', 'updated_at'])
        storage.delete(name)

    def __str__(self):
        return self.get_full_name() or self.username
