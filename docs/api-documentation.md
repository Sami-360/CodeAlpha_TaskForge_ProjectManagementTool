# TaskForge API Design

Base URL for local development: `http://127.0.0.1:8000`

Protected endpoints use:

```http
Authorization: Bearer <access-token>
```

## Foundation and Authentication

| Method | Path | Permission |
|---|---|---|
| GET | `/api/health/` | Public |
| POST | `/api/auth/register/` | Public |
| POST | `/api/auth/login/` | Public; username/password |
| POST | `/api/auth/token/refresh/` | Public; refresh token |
| GET | `/api/auth/me/` | Authenticated |
| PATCH | `/api/auth/me/` | Authenticated owner of profile |
| DELETE | `/api/auth/me/avatar/` | Authenticated owner of profile |

Profile PATCH accepts `multipart/form-data`. Avatars support JPG, JPEG, PNG, and WebP up to 5 MB.

## Projects and Members

| Method | Path | Permission |
|---|---|---|
| GET, POST | `/api/projects/` | Authenticated |
| GET | `/api/projects/{project_id}/` | Project member |
| PATCH, DELETE | `/api/projects/{project_id}/` | Owner |
| GET | `/api/projects/{project_id}/members/` | Project member |
| POST | `/api/projects/{project_id}/members/` | Owner |
| PATCH, DELETE | `/api/projects/{project_id}/members/{member_id}/` | Owner; owner membership protected |

Member creation accepts `identifier` containing a username or email plus `role` containing `manager` or `member`.

Project list parameters: `search`, `role=owner|manager|member`, and `sort=updated|created|alphabetical`.

## Labels and Activity

| Method | Path | Permission |
|---|---|---|
| GET | `/api/projects/{project_id}/labels/` | Project member |
| POST | `/api/projects/{project_id}/labels/` | Owner or manager |
| PATCH, DELETE | `/api/project-labels/{label_id}/` | Owner or manager |
| GET | `/api/projects/{project_id}/activities/` | Project member |
| PATCH | `/api/tasks/{task_id}/labels/` | Owner or manager |

## Tasks

| Method | Path | Permission |
|---|---|---|
| GET | `/api/projects/{project_id}/tasks/` | Project member |
| POST | `/api/projects/{project_id}/tasks/` | Owner or manager |
| GET | `/api/tasks/{task_id}/` | Project member |
| PATCH, DELETE | `/api/tasks/{task_id}/` | Owner or manager |
| PATCH | `/api/tasks/{task_id}/status/` | Owner, manager, or assigned member |
| PATCH | `/api/tasks/{task_id}/assign/` | Owner or manager |
| PATCH | `/api/tasks/{task_id}/position/` | Owner or manager |
| PATCH | `/api/tasks/{task_id}/complete/` | Owner, manager, or assigned member |
| PATCH | `/api/tasks/{task_id}/reopen/` | Owner, manager, or assigned member |

Task list filters: `search`, `status`, `priority`, `assigned_to`, `label`, `overdue=true|false`, `due_this_week=true`, and `unassigned=true`.

## Attachments and Checklists

| Method | Path | Permission |
|---|---|---|
| GET, POST | `/api/tasks/{task_id}/attachments/` | Project member |
| GET | `/api/task-attachments/{id}/download/` | Project member |
| DELETE | `/api/task-attachments/{id}/` | Uploader, owner, or manager |
| GET | `/api/tasks/{task_id}/checklists/` | Project member |
| POST | `/api/tasks/{task_id}/checklists/` | Owner or manager |
| DELETE | `/api/checklists/{id}/` | Owner or manager |
| POST | `/api/checklists/{id}/items/` | Owner, manager, or task assignee |
| PATCH, DELETE | `/api/checklist-items/{id}/` | Owner, manager, or task assignee |
| PATCH | `/api/checklist-items/{id}/toggle/` | Owner, manager, or task assignee |

Attachments support PNG, JPG, JPEG, WebP, PDF, TXT, DOC, DOCX, XLS, XLSX, and ZIP up to 10 MB. Downloads use JWT and are not public media links.

## Comments

| Method | Path | Permission |
|---|---|---|
| GET, POST | `/api/tasks/{task_id}/comments/` | Project member |
| PATCH | `/api/comments/{comment_id}/` | Comment author |
| DELETE | `/api/comments/{comment_id}/` | Author, owner, or manager |

## Notifications

| Method | Path | Permission |
|---|---|---|
| GET | `/api/notifications/` | Authenticated recipient |
| PATCH | `/api/notifications/{id}/read/` | Authenticated recipient |
| PATCH | `/api/notifications/read-all/` | Authenticated recipient |

## Dashboard

`GET /api/dashboard/` returns project/task counts, completion percentage, due-this-week count, recent projects/tasks/activity, upcoming deadlines, workload per project, priority distribution, and unread notifications.

## Due Notification Command

```powershell
python manage.py send_due_task_notifications
```

The command creates at most one due-soon and one overdue notification per task/recipient reminder state. Schedule it with cron or Windows Task Scheduler in production.

## WebSockets

| Route | Permission | Server events |
|---|---|---|
| `/ws/projects/{project_id}/board/` | Project member | `task_created`, `task_updated`, `task_deleted`, `task_status_changed`, `comment_created`, `member_added`, `attachment_added`, `checklist_updated` |
| `/ws/notifications/` | Authenticated user | `notification_created` for that user only |

WebSockets use message-based JWT authentication. After the server sends `authentication_required`, send:

```json
{"type": "authenticate", "token": "<access-token>"}
```

The access token is deliberately excluded from the WebSocket URL. Invalid authentication closes with `4401`; project authorization failure closes with `4403`.

## JWT and CSRF

The REST client sends JWTs in the `Authorization` header and does not use authentication cookies. CSRF tokens are therefore not required for these API requests. Django admin continues to use sessions and Django's normal CSRF protection.

## Status Codes

- `200`: successful read/update
- `201`: resource created
- `204`: resource deleted
- `400`: validation error
- `401`: missing/invalid authentication
- `403`: authenticated but unauthorized
- `404`: resource absent or intentionally hidden from outsiders
