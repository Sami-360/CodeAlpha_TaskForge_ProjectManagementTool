from channels.db import database_sync_to_async

from config.websocket import TokenAuthenticatedConsumer
from projects.models import ProjectMember


class ProjectBoardConsumer(TokenAuthenticatedConsumer):
    @database_sync_to_async
    def authorized_group(self, user):
        project_id = self.scope['url_route']['kwargs']['project_id']
        if not ProjectMember.objects.filter(project_id=project_id, user=user).exists():
            return None
        return f'project.{project_id}'
