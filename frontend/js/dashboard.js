document.addEventListener('DOMContentLoaded', async () => {
  const user = await TaskForgeUI.initShell('dashboard');
  if (!user) return;
  const { el, formatDate, toast } = TaskForgeUI;
  try {
    const data = await TaskForgeAPI.request('/dashboard/');
    const stats = [
      ['Projects', data.total_projects],
      ['Owned', data.owned_projects],
      ['Assigned', data.assigned_tasks],
      ['Overdue', data.overdue_tasks],
      ['To do', data.todo_tasks],
      ['In progress', data.in_progress_tasks],
      ['Completed', data.completed_tasks],
      ['Unread', data.unread_notifications],
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
  } catch (error) {
    toast(error.message, 'error');
  }
});
