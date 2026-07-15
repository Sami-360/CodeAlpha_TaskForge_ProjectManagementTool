from rest_framework import permissions

from projects.permissions import can_manage_tasks, get_project_role


class CommentObjectPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, comment):
        if get_project_role(comment.task.project, request.user) is None:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'PATCH':
            return comment.user_id == request.user.id
        if request.method == 'DELETE':
            return comment.user_id == request.user.id or can_manage_tasks(
                comment.task.project, request.user
            )
        return False
