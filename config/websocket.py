from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def user_from_access_token(raw_token):
    try:
        token = AccessToken(raw_token)
        user_id = token.get('user_id')
    except (TokenError, TypeError):
        return None
    if not user_id:
        return None
    return get_user_model().objects.filter(pk=user_id, is_active=True).first()


class TokenAuthenticatedConsumer(AsyncJsonWebsocketConsumer):
    group_name = None
    user = None

    async def connect(self):
        await self.accept()
        await self.send_json({'type': 'authentication_required'})

    async def receive_json(self, content, **kwargs):
        if self.user is None:
            if content.get('type') != 'authenticate' or not content.get('token'):
                await self.send_json({'type': 'authentication_error', 'message': 'Access token required.'})
                await self.close(code=4401)
                return
            user = await user_from_access_token(content['token'])
            if user is None:
                await self.send_json({'type': 'authentication_error', 'message': 'Invalid access token.'})
                await self.close(code=4401)
                return
            self.user = user
            self.group_name = await self.authorized_group(user)
            if self.group_name is None:
                await self.send_json({'type': 'authorization_error', 'message': 'WebSocket access denied.'})
                await self.close(code=4403)
                return
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.send_json({'type': 'authenticated'})
            return

        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def realtime_event(self, event):
        await self.send_json(event['payload'])

    async def authorized_group(self, user):
        raise NotImplementedError
