# TaskForge

TaskForge is a collaborative full-stack project management platform being built for CodeAlpha Full Stack Development Task 3. The repository currently contains a tested Django REST API foundation and JWT authentication system. Group projects, task boards, comments, notifications, WebSockets, and the frontend are planned phases and are not represented as complete in this document.

## 1. Project Overview

The final product is intended to provide a Trello- or Asana-style workspace where users can create group projects, manage project members, assign tasks, communicate through task comments, and track work on a Kanban board.

Current implementation status:

- Django 6 project foundation
- PostgreSQL database connection
- Environment-based configuration
- Django REST Framework and CORS
- API health check
- Custom `accounts.User` model
- JWT registration, username login, token refresh, and profile API
- Django admin support for the custom user
- Authentication test suite

## 2. CodeAlpha Requirements

| Requirement | Status |
|---|---|
| Full-stack authentication | Backend complete and tested; frontend planned |
| Group projects | Planned |
| Task assignment | Planned |
| Task comments and communication | Planned |
| Project boards | Planned |
| Task cards | Planned |
| Backend management for users | Complete |
| Backend management for projects, tasks, and comments | Planned |
| Notifications | Bonus, planned after required features |
| Real-time WebSocket updates | Bonus, planned after required features |

## 3. SDLC Methodology

TaskForge follows an incremental Agile-style workflow:

1. Analyze one feature and its permission rules.
2. Design database relationships and API contracts.
3. Implement the backend on a dedicated Git branch.
4. Generate and review migrations.
5. Add automated tests for success, validation, and authorization paths.
6. Integrate the frontend only after the API is stable.
7. Run regression checks before merging.
8. Update documentation to match behavior that actually exists.

Completed phases are foundation and authentication. Projects, tasks, comments, frontend, notifications, and final audit remain separate phases.

## 4. User Stories

Implemented:

- As a visitor, I can register with a unique username and email.
- As a user, I can log in with my username and password.
- As a client, I can refresh an access token with a valid refresh token.
- As an authenticated user, I can view my safe profile data.
- As an authenticated user, I can update my name, bio, and avatar.

Planned:

- As an owner, I can create a project and manage its members.
- As a manager, I can create, assign, update, and delete project tasks.
- As a member, I can view shared work and update tasks assigned to me.
- As a project member, I can communicate through task comments.
- As a user, I can see relevant notifications and board changes.

## 5. Features

### Implemented

- Password hashing through Django authentication
- Case-insensitive unique email validation
- Optional avatar and 300-character bio
- JWT access tokens with a 15-minute lifetime
- JWT refresh tokens with a 7-day lifetime
- Protected current-user endpoint
- Development media configuration
- PostgreSQL-backed migrations

### Planned

- Owner, manager, and member project roles
- Project membership management
- Task assignment, priority, due date, status, and position
- To Do, In Progress, and Done Kanban columns
- Task comments
- Vanilla HTML, CSS, and JavaScript frontend
- Notifications and optional Django Channels integration

## 6. User Roles and Permissions

Project-level roles are part of the planned project phase and are not yet enforced by the current API.

| Role | Planned permissions |
|---|---|
| Owner | Manage the project, membership, roles, tasks, and comments |
| Manager | View members and manage tasks and comments; cannot delete the project |
| Member | View shared work, update assigned task status, and manage own comments |

All permission rules will be enforced by the backend. Frontend button visibility will not be treated as security.

## 7. Technology Stack

- Python 3.12
- Django 6.0.6
- Django REST Framework 3.17.1
- PostgreSQL 17
- Psycopg 3
- Simple JWT 5.5.1
- django-cors-headers
- python-dotenv
- Pillow
- Planned frontend: HTML5, CSS3, and vanilla JavaScript

No React, Vue, Angular, TypeScript, Bootstrap, Tailwind, Firebase, or Node.js backend is used.

## 8. Database Design

Current relationship:

```text
accounts.User
  id, username, email, first_name, last_name,
  avatar, bio, is_active, date_joined, updated_at
```

Planned relationship overview:

```text
User 1---* Project (owner)
User *---* Project (through ProjectMember with a role)
Project 1---* Task
User 1---* Task (creator)
User 1---* Task (optional assignee)
Task 1---* Comment
User 1---* Comment
User 1---* Notification (recipient)
```

The custom user model is configured through `AUTH_USER_MODEL = "accounts.User"` and was created in `accounts/0001_initial.py` before the clean migration history was applied.

## 9. Project Structure

```text
CodeAlpha_ProjectManagementTool/
|-- accounts/                 Custom user and authentication API
|   |-- migrations/
|   |-- admin.py
|   |-- models.py
|   |-- serializers.py
|   |-- tests.py
|   |-- urls.py
|   `-- views.py
|-- comments/                 Reserved app shell for comments phase
|-- config/                   Settings, root URLs, ASGI, and WSGI
|-- projects/                 Reserved app shell for projects phase
|-- tasks/                    Reserved app shell for tasks phase
|-- .env.example              Safe environment-variable template
|-- .gitignore
|-- manage.py
|-- README.md
`-- requirements.txt
```

## 10. Installation

### Prerequisites

Install Python 3, PostgreSQL with pgAdmin, Git, VS Code, and the VS Code Python extension.

### Windows PowerShell setup

1. Open the project directory:

```powershell
cd "D:\Vs Studio\CodeAlpha_ProjectManagementTool"
```

2. Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow scripts for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

4. Create the local environment file:

```powershell
Copy-Item .env.example .env
```

5. Replace the placeholders in `.env` with local values. Never commit `.env`.

## 11. PostgreSQL Setup

PostgreSQL must be running on the host and port configured in `.env`.

### pgAdmin method

1. Open pgAdmin.
2. Expand `Servers` and connect to PostgreSQL 17.
3. Right-click `Databases`.
4. Select `Create` and then `Database`.
5. Enter `taskforge` as the database name.
6. Select the configured PostgreSQL user as owner.
7. Save the database.

### SQL method

Run this as a PostgreSQL administrator only when the database does not exist:

```sql
CREATE DATABASE taskforge;
```

Do not place the PostgreSQL password in source files or Git commands.

## 12. Environment Variables

The application currently reads these exact variable names:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=taskforge
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-your-postgres-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Generate a Django secret key locally:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the result into `DJANGO_SECRET_KEY` in `.env`. Do not share or commit it. Update CORS origins when the frontend development port is selected.

## 13. Migrations

Run migrations after the environment and database are configured:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
```

Expected output on a current database:

```text
System check identified no issues (0 silenced).
No changes detected
No migrations to apply.
```

Do not delete or recreate migrations casually. The custom user model must remain part of the initial accounts migration.

## 14. Running the Backend

Start the Django development server:

```powershell
python manage.py runserver
```

Useful URLs:

- API health: `http://127.0.0.1:8000/api/health/`
- Django admin: `http://127.0.0.1:8000/admin/`

Create an administrator when needed:

```powershell
python manage.py createsuperuser
```

The development server is not a production server.

## 15. Running the Frontend

The frontend has not been implemented yet. The planned approach is a single organized vanilla HTML/CSS/JavaScript frontend served through one documented development method. No frontend run command is currently valid.

## 16. API Endpoints

| Method | Path | Permission | Status |
|---|---|---|---|
| GET | `/api/health/` | Public | Implemented |
| POST | `/api/auth/register/` | Public | Implemented |
| POST | `/api/auth/login/` | Public | Implemented; username login |
| POST | `/api/auth/token/refresh/` | Public | Implemented |
| GET | `/api/auth/me/` | JWT required | Implemented |
| PATCH | `/api/auth/me/` | JWT required | Implemented |
| `/api/projects/...` | Project member rules | Planned |
| `/api/tasks/...` | Project member rules | Planned |
| `/api/comments/...` | Project member rules | Planned |
| `/api/notifications/...` | JWT required | Bonus, planned |

### Register

```json
{
  "username": "sami",
  "email": "sami@example.com",
  "first_name": "Sami",
  "last_name": "Ullah",
  "password": "StrongPass123!",
  "password_confirm": "StrongPass123!"
}
```

A successful registration returns HTTP 201 with safe user data plus access and refresh tokens. Password fields are never returned.

### Login

```json
{
  "username": "sami",
  "password": "StrongPass123!"
}
```

### Refresh an access token

```json
{
  "refresh": "<refresh-token>"
}
```

### Access a protected endpoint

```http
Authorization: Bearer <access-token>
```

### Update the current profile

```json
{
  "first_name": "Sami",
  "last_name": "Ullah",
  "bio": "Project manager"
}
```

The profile endpoint does not allow changes to username, email, password, staff status, superuser status, ID, or join date.

## 17. WebSocket Events

WebSockets are not implemented. Django Channels, Daphne, consumers, WebSocket routes, and event broadcasts will only be added after required project, task, comment, and frontend features pass their tests. Redis is recommended for a future production channel layer.

## 18. Testing

Run the current checks:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test accounts
```

The current authentication suite contains 13 tests covering:

- Hashed passwords and normalized email
- Duplicate username and case-insensitive duplicate email rejection
- Password confirmation
- Registration response safety
- Valid and invalid login
- Refresh tokens
- JWT-protected profile retrieval
- Allowed profile updates
- Protected-field update prevention

Most recent verified result:

```text
Ran 13 tests
OK
```

## 19. Security

- `.env` is Git ignored.
- Passwords use Django's salted one-way hashing.
- Password fields are write-only and never returned by serializers.
- PostgreSQL credentials are not hard-coded.
- Protected API requests use JWT bearer authentication.
- Email uniqueness is enforced case-insensitively.
- Profile updates expose only explicitly allowed fields.
- Media files are ignored by Git and served by Django only in debug mode.
- Future project permissions must be enforced in backend permission classes.
- JWT APIs do not rely on cookie-based session authentication, while Django admin retains its normal session login.

## 20. Screenshots

No application screenshots are available because the frontend and project-management screens are not implemented yet. Screenshots should be added only after the actual dashboard, projects page, board, task details, and responsive views exist.

## 21. Git Workflow

Current development uses feature branches and focused commits.

```powershell
git checkout main
git checkout -b feature/projects
```

Recommended sequence:

1. `feature/authentication`
2. `feature/projects`
3. `feature/tasks`
4. `feature/comments`
5. `feature/frontend`
6. `feature/notifications`
7. `chore/final-audit`

Before committing:

```powershell
git status
git diff --check
python manage.py test
```

Never push unless the correct remote and credentials are configured and pushing is explicitly intended.

## 22. Author

- **Name:** SAMI ULLAH
- **GitHub:** `Sami-360`
- **Email:** `official.samiullah360@gmail.com`

## 23. License

No open-source license file is currently included. Unless a license is added, the source remains under the author's default copyright rights.

## Troubleshooting

### `password authentication failed for user "postgres"`

Confirm `POSTGRES_USER` and `POSTGRES_PASSWORD` in `.env`, then verify the same credentials in pgAdmin. Do not paste the password into source code.

### `database "taskforge" does not exist`

Create the database through pgAdmin or with the SQL command in the PostgreSQL Setup section.

### `No module named ...`

Activate `.venv` and install the requirements again:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### HTTP 401 from `/api/auth/me/`

Include a current access token in the `Authorization: Bearer <access-token>` header. If the access token expired, use `/api/auth/token/refresh/` with the refresh token.
