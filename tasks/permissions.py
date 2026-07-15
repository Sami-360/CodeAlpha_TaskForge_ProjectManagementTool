from rest_framework import permissions

from projects.permissions import can_manage_tasks, get_project_role


class TaskObjectPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, task):
        if request.method in permissions.SAFE_METHODS:
            return get_project_role(task.project, request.user) is not None
        return can_manage_tasks(task.project, request.user)
