# TaskForge Testing Checklist

## Automated Backend

- [x] Custom user password hashing and normalization
- [x] Registration, login, refresh, profile access, and profile protection
- [ ] Project creation and automatic owner membership
- [ ] Project queryset isolation
- [ ] Project update/delete role enforcement
- [ ] Member creation, duplicate rejection, role update, and owner protection
- [ ] Task create/edit/delete permissions
- [ ] Task member validation, filtering, assignment, status, and position
- [ ] Comment membership, validation, ownership, moderation, and ordering
- [ ] Notification creation, isolation, single read, and read all
- [ ] Full two-user collaboration flow plus outsider rejection
- [ ] WebSocket authentication, project membership, and notification isolation

Required verification command:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
```

## Frontend Manual Checks

- [ ] Register, login, logout, and failed-login message
- [ ] Expired access-token refresh and invalid-refresh redirect
- [ ] Project create/edit/delete and empty state
- [ ] Member add/remove/role controls and forbidden controls
- [ ] Task create/assign/edit/delete
- [ ] Kanban status move through drag and accessible controls
- [ ] Task filters and overdue display
- [ ] Comment create/edit/delete and validation
- [ ] Notification list, unread count, and read actions
- [ ] Profile display, update, and avatar upload
- [ ] Loading states, confirmations, toasts, and network errors
- [ ] Keyboard focus and narrow mobile layout
- [ ] No browser console errors

## Security Audit

- [ ] `.env` remains ignored and `.env.example` contains placeholders only
- [ ] Protected APIs reject missing/invalid JWTs
- [ ] Outsiders cannot enumerate project resources
- [ ] Members cannot elevate roles or assign non-members
- [ ] Users cannot edit another profile or comment
- [ ] API responses never contain passwords or secrets
- [ ] User content is rendered through safe DOM APIs
- [ ] WebSockets reject anonymous/unauthorized access when implemented
