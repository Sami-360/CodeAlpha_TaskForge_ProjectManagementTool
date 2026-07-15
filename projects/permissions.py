from rest_framework import permissions

from projects.models import ProjectMember


def get_project_role(project, user):
    if not user or not user.is_authenticated:
        return None
    return project.memberships.filter(user=user).values_list('role', flat=True).first()


def can_manage_tasks(project, user):
    return get_project_role(project, user) in {
        ProjectMember.Role.OWNER,
        ProjectMember.Role.MANAGER,
    }


class ProjectObjectPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        role = get_project_role(project, request.user)
        if request.method in permissions.SAFE_METHODS:
            return role is not None
        return role == ProjectMember.Role.OWNER
