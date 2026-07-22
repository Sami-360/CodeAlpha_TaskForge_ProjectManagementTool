# Enhancement Screenshot Guide

Release screenshots must be captured from the real running application rather than mocked pages.

1. Start Django on `127.0.0.1:8000` and the static frontend on `127.0.0.1:5500`.
2. Sign in with a review account that has representative project, task, notification, and activity data.
3. Capture these real states at 1440x900 unless noted:

| Filename | Real UI state |
|---|---|
| `dashboard-insights.png` | Dashboard metrics, assignments, workload, and priorities |
| `projects-page.png` | Searchable project listing |
| `project-board.png` | Kanban board with real project members, labels, and tasks |
| `task-details.png` | Task details, comments, attachments, and checklist area |
| `profile-page.png` | Profile avatar, statistics, and edit controls |
| `activity-view.png` | Project board with the real activity drawer open |
| `notifications-panel.png` | Dashboard with the notification panel open |
| `collapsed-sidebar.png` | Desktop dashboard with the compact sidebar enabled |
| `mobile-sidebar.png` | 375x812 dashboard with the mobile drawer and overlay open |
| `admin-dashboard.png` | TaskForge administration overview |
| `admin-users.png` | User administration list |
| `admin-sami-profile.png` | Sami user administration form with the password row excluded |
| `admin-projects.png` | Project administration list |
| `admin-tasks.png` | Task administration list |

Use review data only. Do not add screenshots containing passwords, password metadata, JWTs, private production data, or browser developer tools.
