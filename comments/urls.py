from django.urls import path

from comments.views import CommentDetailView, CommentListCreateView


urlpatterns = [
    path(
        'tasks/<int:task_id>/comments/',
        CommentListCreateView.as_view(),
        name='comment-list',
    ),
    path(
        'comments/<int:pk>/',
        CommentDetailView.as_view(),
        name='comment-detail',
    ),
]
