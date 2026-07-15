from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related(
            'sender'
        )[:100]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'unread_count': Notification.objects.filter(
                    recipient=request.user,
                    is_read=False,
                ).count(),
                'results': serializer.data,
            }
        )


class NotificationReadView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    http_method_names = ['patch', 'head', 'options']

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(self.get_serializer(notification).data)


class NotificationReadAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)
        return Response({'updated': updated}, status=status.HTTP_200_OK)
