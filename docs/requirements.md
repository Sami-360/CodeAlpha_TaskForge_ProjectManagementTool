# TaskForge Requirements

## Product Goal

TaskForge is a collaborative project-management application for CodeAlpha Full Stack Development Task 3. It provides authenticated group projects, role-based membership, task assignment, a Kanban workflow, comments, and a responsive vanilla JavaScript client.

## Functional Requirements

1. Users register, log in with username/password, refresh JWTs, and manage their own profile.
2. Authenticated users create projects and automatically become project owners.
3. Owners add/remove members and assign manager or member roles.
4. Project members see only projects to which they belong.
5. Owners and managers create, assign, update, move, and delete tasks.
6. Assigned members update the status of their own assigned tasks.
7. Project members read and create task comments.
8. Comment authors edit/delete their own comments; owners/managers may moderate deletion.
9. Notifications are created for membership, assignment, status, and comment events.
10. The frontend supports authentication, projects, a Kanban board, task detail, comments, profile, and notifications.
11. Profile avatars use unique paths, image validation, a 5 MB limit, preview, replacement, and deletion.
12. Authenticated pages share persistent desktop sidebar and accessible mobile drawer behavior.
13. Tasks support protected attachments, checklists, and project-scoped labels.
14. Project members can review a limited newest-first activity history.
15. Project/task search and filters cover roles, labels, due windows, and unassigned tasks.
16. Due-state responses distinguish today, tomorrow, soon, overdue, completed, and no date.
17. Dashboard insights summarize workload, priority, deadlines, activity, and completion.
18. A repeat-safe command creates due-soon and overdue notifications for scheduling.

## Role Rules

| Action | Owner | Manager | Member |
|---|---:|---:|---:|
| View project and members | Yes | Yes | Yes |
| Edit/delete project | Yes | No | No |
| Manage membership and roles | Yes | No | No |
| Create/assign/edit/delete task | Yes | Yes | No |
| Change any task status | Yes | Yes | No |
| Change assigned task status | Yes | Yes | Yes |
| Add comments | Yes | Yes | Yes |
| Edit own comment | Yes | Yes | Yes |
| Delete own comment | Yes | Yes | Yes |
| Moderate comment deletion | Yes | Yes | No |

The owner membership cannot be removed or downgraded through normal membership endpoints.

## Non-Functional Requirements

- PostgreSQL is the source of truth.
- Protected APIs require valid JWT authentication.
- Authorization is enforced in backend querysets and permission checks.
- Multi-record writes use database transactions.
- Passwords and secrets are never returned or committed.
- Validation errors use clear JSON and appropriate HTTP status codes.
- Database relationships use foreign keys, constraints, and safe cascade behavior.
- The frontend is responsive and keyboard-usable without a UI framework.
- User-provided text is rendered with safe DOM APIs, not unsafe HTML insertion.
- Automated tests cover permissions, validation, and the primary integration flow.
- Avatar and attachment paths use UUID filenames and never trust client paths.
- Avatar files are limited to 5 MB; task attachments are limited to 10 MB.
- Attachment downloads require JWT project membership rather than public media URLs.
- The local sidebar state is stored under `taskforgeSidebarCollapsed`.

## Development Phases

1. Foundation and authentication
2. Projects, membership, and roles
3. Tasks and board workflow
4. Comments and notifications
5. Vanilla JavaScript frontend
6. Required-feature integration testing
7. WebSocket bonus
8. Documentation and final audit
