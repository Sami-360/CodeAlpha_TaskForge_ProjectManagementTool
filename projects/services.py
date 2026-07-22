from projects.models import ProjectActivity


def record_activity(*, project, action, actor=None, task=None, target_user=None, metadata=None):
    safe_metadata = {
        key: value
        for key, value in (metadata or {}).items()
        if key in {'project_name', 'task_title', 'member_name', 'role', 'filename', 'status'}
    }
    return ProjectActivity.objects.create(
        project=project,
        actor=actor,
        action=action,
        task=task,
        target_user=target_user,
        metadata=safe_metadata,
    )
