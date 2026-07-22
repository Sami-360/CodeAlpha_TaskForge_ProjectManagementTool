# Enhancement Screenshot Guide

Authenticated interaction automation is not bundled with this repository, so screenshots must be captured from the real running application rather than mocked pages.

1. Start Django on `127.0.0.1:8000` and the static frontend on `127.0.0.1:5500`.
2. Sign in with a review account that owns a project containing labels, a task, an attachment, checklist items, and activity.
3. Capture these real states at 1440x900 unless noted:

| Filename | Real UI state |
|---|---|
| `profile-page.png` | Profile avatar, statistics, preview controls, and bio counter |
| `mobile-sidebar.png` | 390x844 dashboard with mobile drawer and overlay open |
| `taskforge-admin.png` | Django admin login or index with TaskForge branding |
| `task-checklist.png` | Task details showing checklist progress and items |
| `task-attachments.png` | Task details showing uploaded attachment metadata/actions |
| `project-activity.png` | Project board with real activity drawer open |
| `dashboard-insights.png` | Dashboard workload, priorities, deadlines, and activity |

Do not add screenshots containing real passwords, JWTs, private email addresses, or browser developer tools.
