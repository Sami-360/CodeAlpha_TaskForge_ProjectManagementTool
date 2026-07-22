# TaskForge Testing Checklist

## Automated Backend

- [x] Custom user password hashing and normalization
- [x] Registration, login, refresh, profile access, and profile protection
- [x] Project creation and automatic owner membership
- [x] Project queryset isolation
- [x] Project update/delete role enforcement
- [x] Member creation, duplicate rejection, role update, and owner protection
- [x] Task create/edit/delete permissions
- [x] Task member validation, filtering, assignment, status, and position
- [x] Comment membership, validation, ownership, moderation, and ordering
- [x] Notification creation, isolation, single read, and read all
- [x] Full two-user collaboration flow plus outsider rejection
- [x] WebSocket authentication, project membership, and notification isolation
- [x] Avatar type/size validation, replacement, deletion, and profile statistics
- [x] Attachment type/size validation, protected download, deletion permission, and file cleanup
- [x] Checklist creation, item permission, toggle, and progress
- [x] Label validation, uniqueness, assignment, filtering, and outsider isolation
- [x] Activity creation, ordering, and outsider rejection
- [x] Project search/role/sort and enhanced task filters
- [x] Complete/reopen behavior and dashboard insight scoping
- [x] Repeat-safe due notification command
- [x] TaskForge admin branding and local CSS reference

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
- [x] Keyboard focus styles and narrow authentication layout
- [ ] No browser console errors
- [ ] Desktop sidebar menu stays visible and each menu button opens the correct page
- [ ] Mobile sidebar overlay, navigation close, and Escape close
- [ ] Avatar preview/change/remove flow using a real image
- [ ] Attachment upload/download/delete using each supported category
- [ ] Checklist and label controls on task details/board
- [ ] Activity drawer links and real-time refresh
- [ ] Dashboard insight layout at desktop and mobile widths

## Security Audit

- [x] `.env` remains ignored and `.env.example` contains placeholders only
- [x] Protected APIs reject missing/invalid JWTs
- [x] Outsiders cannot enumerate project resources
- [x] Members cannot elevate roles or assign non-members
- [x] Users cannot edit another profile or comment
- [x] API responses never contain passwords or secrets
- [x] User content is rendered through safe DOM APIs
- [x] WebSockets reject anonymous/unauthorized access
