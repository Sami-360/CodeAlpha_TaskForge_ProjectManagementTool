from django.urls import path

from projects.views import (
    ProjectDetailView,
    ProjectListCreateView,
    ProjectMemberDetailView,
    ProjectMemberListCreateView,
)


urlpatterns = [
    path('', ProjectListCreateView.as_view(), name='project-list'),
    path('<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path(
        '<int:project_id>/members/',
        ProjectMemberListCreateView.as_view(),
        name='project-member-list',
    ),
    path(
        '<int:project_id>/members/<int:member_id>/',
        ProjectMemberDetailView.as_view(),
        name='project-member-detail',
    ),
]
