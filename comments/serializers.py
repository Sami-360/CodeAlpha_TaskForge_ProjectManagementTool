from rest_framework import serializers

from comments.models import Comment
from projects.serializers import UserSummarySerializer


class CommentSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'task', 'user', 'message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'task', 'user', 'created_at', 'updated_at']

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Comment message cannot be empty.')
        return value
