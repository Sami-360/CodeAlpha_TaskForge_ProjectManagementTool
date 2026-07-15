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

Task list filters: `status`, `priority`, `assigned_to`, and `overdue=true|false`.

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

`GET /api/dashboard/` returns project/task counts, recent projects, recent assigned tasks, and an unread notification count for the current user.

## WebSockets

| Route | Permission | Server events |
|---|---|---|
| `/ws/projects/{project_id}/board/` | Project member | `task_created`, `task_updated`, `task_deleted`, `task_status_changed`, `comment_created`, `member_added` |
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
