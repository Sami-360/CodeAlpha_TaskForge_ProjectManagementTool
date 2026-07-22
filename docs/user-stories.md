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

## Professional Enhancements

- As a user, I can preview, upload, replace, or remove a validated profile picture and see my work statistics.
- As a desktop user, I can collapse navigation and keep that preference; as a mobile user, I can use an accessible off-canvas drawer.
- As a project member, I can download protected task attachments and review checklists, labels, and activity.
- As an owner or manager, I can manage project labels and checklist structure.
- As a task assignee, I can add and complete checklist items and complete or reopen my task.
- As a user, I can search/sort projects, filter board work, and review deadline/workload insights.

Acceptance criteria:

- Avatar images accept JPG/JPEG/PNG/WebP up to 5 MB and old files are removed safely.
- Attachments accept the documented formats up to 10 MB; outsiders cannot download them.
- Labels are project-scoped, case-insensitively unique, and use validated six-digit colors.
- Activity entries contain safe metadata, a human-readable message, and newest-first ordering.
- Due reminders are idempotent when the command runs repeatedly.
