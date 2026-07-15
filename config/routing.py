from django.urls import re_path

from notifications.consumers import NotificationConsumer
from projects.consumers import ProjectBoardConsumer

websocket_urlpatterns = [
    re_path(r'^ws/projects/(?P<project_id>\d+)/board/$', ProjectBoardConsumer.as_asgi()),
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
]
