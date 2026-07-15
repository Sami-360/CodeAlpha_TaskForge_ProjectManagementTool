# TaskForge Database Design

## Relationships

```text
accounts.User 1---* projects.Project                 (owner)
accounts.User *---* projects.ProjectMember           (membership)
projects.Project 1---* projects.ProjectMember
projects.Project 1---* tasks.Task
accounts.User 1---* tasks.Task                       (creator)
accounts.User 1---* tasks.Task                       (optional assignee)
tasks.Task 1---* comments.Comment
accounts.User 1---* comments.Comment
accounts.User 1---* notifications.Notification       (recipient/sender)
projects.Project 1---* notifications.Notification    (optional context)
tasks.Task 1---* notifications.Notification          (optional context)
```

## Models

### User

Existing `accounts.User` extends `AbstractUser` with unique normalized email, optional avatar, bio, and update timestamp.

### Project

Fields: `name`, `description`, `owner`, `created_at`, `updated_at`.

- `owner` uses `PROTECT` so ownership cannot disappear independently.
- Projects are ordered newest first.

### ProjectMember

Fields: `project`, `user`, `role`, `added_by`, `joined_at`.

- Unique constraint on `(project, user)`.
- Partial unique constraint permits one `owner` membership per project.
- Application validation keeps `Project.owner` aligned with its owner membership.

### Task

Fields: `project`, `title`, `description`, `created_by`, `assigned_to`, `status`, `priority`, `due_date`, `position`, timestamps.

- Status choices: `todo`, `in_progress`, `done`.
- Priority choices: `low`, `medium`, `high`.
- Task assignment and creation validate project membership.
- Ordering is status, position, then creation time.

### Comment

Fields: `task`, `user`, `message`, `created_at`, `updated_at`.

- Message length is limited to 2000.
- Ordering is oldest first.

### Notification

Fields: `recipient`, optional `sender`, type, message, optional project/task, `is_read`, `created_at`.

- Notifications cascade with recipient/project/task context.
- Ordering is newest first.

## Deletion Behavior

- Deleting a project cascades its memberships, tasks, comments, and contextual notifications.
- Deleting a task cascades comments and task notifications.
- Project owners are protected while they own a project.
- Assigned user deletion sets task assignment to null; task creator deletion is protected.
