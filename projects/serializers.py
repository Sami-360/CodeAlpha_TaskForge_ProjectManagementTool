from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from projects.models import Project, ProjectMember
from projects.permissions import get_project_role

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'avatar']


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    added_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'role', 'added_by', 'joined_at']
        read_only_fields = ['id', 'user', 'added_by', 'joined_at']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSummarySerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'name',
            'description',
            'owner',
            'member_count',
            'current_user_role',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Project name cannot be blank.')
        return value

    def get_current_user_role(self, project):
        request = self.context.get('request')
        return get_project_role(project, request.user) if request else None

    def get_member_count(self, project):
        annotated_count = getattr(project, 'member_count', None)
        return annotated_count if annotated_count is not None else project.memberships.count()

    @transaction.atomic
    def create(self, validated_data):
        project = Project.objects.create(
            owner=self.context['request'].user,
            **validated_data,
        )
        return project


class ProjectMemberCreateSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    role = serializers.ChoiceField(
        choices=[ProjectMember.Role.MANAGER, ProjectMember.Role.MEMBER]
    )

    def validate_identifier(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Username or email is required.')
        return value

    def validate(self, attrs):
        identifier = attrs['identifier']
        user = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        if not user:
            raise serializers.ValidationError({'identifier': 'User was not found.'})

        project = self.context['project']
        if ProjectMember.objects.filter(project=project, user=user).exists():
            raise serializers.ValidationError({'identifier': 'User is already a member.'})

        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        validated_data.pop('identifier')
        return ProjectMember.objects.create(
            project=self.context['project'],
            added_by=self.context['request'].user,
            **validated_data,
        )


class ProjectMemberRoleSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=[ProjectMember.Role.MANAGER, ProjectMember.Role.MEMBER]
    )

    class Meta:
        model = ProjectMember
        fields = ['role']

    def validate(self, attrs):
        if self.instance.role == ProjectMember.Role.OWNER:
            raise serializers.ValidationError('The owner role cannot be changed.')
        return attrs
