from config.websocket import TokenAuthenticatedConsumer


class NotificationConsumer(TokenAuthenticatedConsumer):
    async def authorized_group(self, user):
        return f'user.{user.pk}'
