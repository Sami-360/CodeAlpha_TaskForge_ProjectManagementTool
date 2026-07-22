from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User


class UserProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.FileField(required=False, allow_null=True)
    full_name = serializers.SerializerMethodField()
    projects_owned_count = serializers.SerializerMethodField()
    projects_joined_count = serializers.SerializerMethodField()
    tasks_assigned_count = serializers.SerializerMethodField()
    completed_tasks_count = serializers.SerializerMethodField()
    pending_tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'avatar',
            'bio',
            'date_joined',
            'updated_at',
            'projects_owned_count',
            'projects_joined_count',
            'tasks_assigned_count',
            'completed_tasks_count',
            'pending_tasks_count',
        ]
        read_only_fields = [
            'id',
            'username',
            'email',
            'full_name',
            'date_joined',
            'updated_at',
            'projects_owned_count',
            'projects_joined_count',
            'tasks_assigned_count',
            'completed_tasks_count',
            'pending_tasks_count',
        ]

    def get_full_name(self, user):
        return user.get_full_name()

    def get_projects_owned_count(self, user):
        return user.owned_projects.count()

    def get_projects_joined_count(self, user):
        return user.project_memberships.exclude(project__owner=user).count()

    def get_tasks_assigned_count(self, user):
        return user.assigned_tasks.count()

    def get_completed_tasks_count(self, user):
        return user.assigned_tasks.filter(status='done').count()

    def get_pending_tasks_count(self, user):
        return user.assigned_tasks.exclude(status='done').count()

    def validate_avatar(self, upload):
        from accounts.validators import validate_avatar

        validate_avatar(upload)
        return upload


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'password_confirm',
        ]

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_email(self, value):
        normalized_email = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return normalized_email

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {'password_confirm': 'Password confirmation does not match.'}
            )

        candidate_user = User(
            username=attrs['username'],
            email=attrs['email'],
            first_name=attrs.get('first_name', ''),
            last_name=attrs.get('last_name', ''),
        )
        validate_password(attrs['password'], user=candidate_user)
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserProfileSerializer(
            self.user,
            context=self.context,
        ).data
        return data
