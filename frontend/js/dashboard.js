document.addEventListener('DOMContentLoaded', async () => {
  const user = await TaskForgeUI.initShell('dashboard');
  if (!user) return;
  const { el, formatDate, toast } = TaskForgeUI;
  try {
    const data = await TaskForgeAPI.request('/dashboard/');
    const stats = [
      ['Projects', data.total_projects],
      ['Owned', data.owned_projects],
      ['Joined', data.joined_projects],
      ['Assigned', data.assigned_tasks],
      ['Overdue', data.overdue_tasks],
      ['To do', data.todo_tasks],
      ['In progress', data.in_progress_tasks],
      ['Completed', data.completed_tasks],
      ['Unread', data.unread_notifications],
      ['Due this week', data.tasks_due_this_week],
      ['Completion', `${data.completion_percentage}%`],
    ];
    document.getElementById('stats').replaceChildren(...stats.map(([label, value]) =>
      el('article', { className: 'panel stat' }, [
        el('span', { className: 'stat-label', text: label }),
        el('strong', { className: 'stat-value', text: String(value) }),
      ]),
    ));

    const projects = document.getElementById('recent-projects');
    projects.replaceChildren();
    if (!data.recent_projects.length) projects.append(el('div', { className: 'empty-state', text: 'No projects yet.' }));
    data.recent_projects.forEach((project) => {
      const link = el('a', { href: `project-board.html?id=${project.id}`, text: project.name });
      const row = el('div', { className: 'project-meta' }, [
        el('div', {}, [link, el('div', { className: 'muted', text: `${project.member_count} members` })]),
        el('span', { className: `badge badge-${project.current_user_role}`, text: project.current_user_role }),
      ]);
      projects.append(row);
    });

    const tasks = document.getElementById('recent-tasks');
    tasks.replaceChildren();
    if (!data.recent_assigned_tasks.length) tasks.append(el('div', { className: 'empty-state', text: 'No tasks assigned.' }));
    data.recent_assigned_tasks.forEach((task) => {
      tasks.append(el('article', { className: 'task-card' }, [
        el('a', { href: `task-details.html?id=${task.id}`, text: task.title }),
        el('div', { className: 'task-card-meta' }, [
          el('span', { text: task.project.name }),
          el('span', { text: task.due_date ? formatDate(task.due_date) : 'No due date' }),
        ]),
      ]));
    });

    const workload = document.getElementById('workload');
    workload.replaceChildren(...data.workload_by_project.map((item) => {
      const percent = item.total ? Math.round(item.completed * 100 / item.total) : 0;
      return el('div', { className: 'insight-row' }, [el('div', { className: 'insight-head' }, [el('span', { text: item.project__name }), el('strong', { text: `${item.completed}/${item.total}` })]), el('div', { className: 'progress-track' }, [el('div', { className: 'progress-fill', style: `width:${percent}%` })])]);
    }));
    if (!data.workload_by_project.length) workload.append(el('div', { className: 'empty-state', text: 'No assigned workload.' }));

    const priority = document.getElementById('priority-insight');
    const priorityTotal = Object.values(data.priority_distribution).reduce((sum, value) => sum + value, 0);
    priority.replaceChildren(...['high', 'medium', 'low'].map((name) => {
      const count = data.priority_distribution[name] || 0;
      return el('div', { className: 'insight-row' }, [el('div', { className: 'insight-head' }, [el('span', { text: name }), el('strong', { text: String(count) })]), el('div', { className: 'progress-track' }, [el('div', { className: `progress-fill priority-${name}`, style: `width:${priorityTotal ? Math.round(count * 100 / priorityTotal) : 0}%` })])]);
    }));

    const deadlines = document.getElementById('upcoming-deadlines');
    deadlines.replaceChildren(...data.upcoming_deadlines.map((task) => el('a', { className: 'insight-link', href: `task-details.html?id=${task.id}` }, [el('strong', { text: task.title }), el('span', { text: `${task.project.name} - ${formatDate(task.due_date)}` })])));
    if (!data.upcoming_deadlines.length) deadlines.append(el('div', { className: 'empty-state', text: 'No upcoming deadlines.' }));

    const activity = document.getElementById('dashboard-activity');
    activity.replaceChildren(...data.recent_activity.map((item) => el('div', { className: 'insight-link' }, [el('strong', { text: item.message }), el('span', { text: formatDate(item.created_at, true) })])));
    if (!data.recent_activity.length) activity.append(el('div', { className: 'empty-state', text: 'No recent activity.' }));
  } catch (error) {
    toast(error.message, 'error');
  }
});
