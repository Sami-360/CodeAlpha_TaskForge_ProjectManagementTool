from django.urls import path

from projects.views import (
    ProjectActivityListView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectMemberDetailView,
    ProjectMemberListCreateView,
    ProjectLabelListCreateView,
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
    path('<int:project_id>/labels/', ProjectLabelListCreateView.as_view(), name='project-label-list'),
    path('<int:project_id>/activities/', ProjectActivityListView.as_view(), name='project-activity-list'),
]
