# TaskForge User Stories

## Authentication

- As a visitor, I can register and receive JWT tokens so I can start securely.
- As a user, I can log in, refresh my access token, and view/update my profile.

Acceptance criteria:

- Passwords are validated, hashed, write-only, and absent from responses.
- Invalid or expired credentials return HTTP 401.
- A user cannot modify protected profile fields.

## Projects and Membership

- As a user, I can create a project and become its owner.
- As an owner, I can add existing users by username or email.
- As an owner, I can promote/demote manager and member roles.
- As a member, I see only projects shared with me.

Acceptance criteria:

- Project creation and owner membership are one transaction.
- A user appears once per project and each project has one owner membership.
- Non-owners cannot manage membership or delete a project.
- The owner membership cannot be removed or downgraded.

## Tasks and Board

- As an owner or manager, I can create and assign project tasks.
- As a project member, I can view task cards and details.
- As an assigned member, I can update my task status.
- As an owner or manager, I can move task cards and reorder them.

Acceptance criteria:

- Creator and assignee must belong to the task project.
- Outsiders receive HTTP 404 or 403 without project data leakage.
- Status, priority, due date, assignment, and position are validated.
- Task lists support status, priority, assignee, and overdue filters.

## Comments

- As a project member, I can discuss work on a task.
- As an author, I can edit or delete my own comment.
- As an owner or manager, I can delete inappropriate comments.

Acceptance criteria:

- Empty messages and messages over 2000 characters are rejected.
- Outsiders cannot list or create comments.
- Comments are returned oldest first.

## Notifications

- As a user, I receive notifications for relevant collaboration events.
- As a user, I can mark one or all of my notifications read.

Acceptance criteria:

- Users receive only their own notifications.
- Self-notifications are avoided when they add no value.
- Unread count is returned with the notification list.

## Frontend

- As a user, I can complete the primary workflow without manually calling the API.
- As a keyboard user, I can use status controls without relying on drag-and-drop.

Acceptance criteria:

- The client handles loading, empty, error, unauthorized, and confirmation states.
- Access tokens are attached automatically and refreshed once after HTTP 401.
- Protected pages redirect to login when refresh fails.
