document.addEventListener('DOMContentLoaded', async () => {
  const currentUser = await TaskForgeUI.initShell('projects');
  if (!currentUser) return;
  const { el, avatar, formatDate, modal, toast, setLoading } = TaskForgeUI;
  const projectId = Number(new URLSearchParams(location.search).get('id'));
  if (!projectId) {
    window.location.replace('projects.html');
    return;
  }
  let project;
  let members = [];
  let tasks = [];
  let labels = [];
  let realtimeReload;

  const canManage = () => ['owner', 'manager'].includes(project.current_user_role);
  const canChangeStatus = (task) => canManage() || task.assigned_to?.id === currentUser.id;

  async function loadData() {
    try {
      [project, members, tasks, labels] = await Promise.all([
        TaskForgeAPI.request(`/projects/${projectId}/`),
        TaskForgeAPI.request(`/projects/${projectId}/members/`),
        TaskForgeAPI.request(`/projects/${projectId}/tasks/`),
        TaskForgeAPI.request(`/projects/${projectId}/labels/`),
      ]);
      document.getElementById('project-name').textContent = project.name;
      document.getElementById('project-description').textContent = project.description || 'No project description.';
      const meta = document.getElementById('project-meta');
      TaskForgeSidebar.setContext({ members });
      if (meta) meta.textContent = `${project.current_user_role || 'member'} | Private project | ${members.length} member${members.length === 1 ? '' : 's'}`;
      renderMemberPreview();
      document.getElementById('create-task').classList.toggle('hidden', !canManage());
      document.getElementById('manage-members').classList.toggle('hidden', project.current_user_role !== 'owner');
      document.getElementById('manage-labels').classList.toggle('hidden', !canManage());
      populateAssignees();
      populateLabels();
      renderBoard();
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  function populateLabels() {
    const filter = document.getElementById('label-filter');
    const current = filter.value;
    filter.replaceChildren(el('option', { value: '', text: 'All labels' }));
    labels.forEach((label) => filter.append(el('option', { value: String(label.id), text: label.name })));
    filter.value = current;
  }

  function populateAssignees() {
    const filter = document.getElementById('assignee-filter');
    const current = filter.value;
    filter.replaceChildren(
      el('option', { value: '', text: 'All assignees' }),
      el('option', { value: 'unassigned', text: 'Unassigned' }),
    );
    members.forEach((membership) => {
      filter.append(el('option', {
        value: String(membership.user.id),
        text: membership.user.full_name || membership.user.username,
      }));
    });
    filter.value = current;
  }

  function filteredTasks() {
    const priority = document.getElementById('priority-filter').value;
    const assignee = document.getElementById('assignee-filter').value;
    const due = document.getElementById('due-filter').value;
    const status = document.getElementById('status-filter').value;
    const label = document.getElementById('label-filter').value;
    const search = document.getElementById('task-search').value.trim().toLowerCase();
    return tasks.filter((task) =>
      (!priority || task.priority === priority)
      && (!status || task.status === status)
      && (!search || task.title.toLowerCase().includes(search))
      && (!assignee || (assignee === 'unassigned' ? !task.assigned_to : task.assigned_to?.id === Number(assignee)))
      && (!label || task.labels.some((item) => item.id === Number(label)))
      && (!due || (due === 'overdue' ? task.due_state === 'overdue' : due === 'due_week' ? ['due_today', 'due_tomorrow', 'due_soon'].includes(task.due_state) : task.due_state === 'no_due_date'))
    );
  }

  function dueText(task) {
    const labels = { no_due_date: 'No due date', due_today: 'Due today', due_tomorrow: 'Due tomorrow', due_soon: `Due ${formatDate(task.due_date)}`, overdue: `Overdue ${formatDate(task.due_date)}`, completed: 'Completed', scheduled: formatDate(task.due_date) };
    return labels[task.due_state] || 'No due date';
  }

  function icon(name, label) {
    return el('span', { className: 'material-symbols-outlined', text: name, ariaHidden: 'true', title: label });
  }

  function metric(name, value, label) {
    return el('span', { className: 'task-metric', title: label }, [icon(name, label), el('span', { text: String(value) })]);
  }

  function renderMemberPreview() {
    const holder = document.getElementById('project-members-preview');
    if (!holder) return;
    holder.replaceChildren(...members.slice(0, 4).map((membership) => avatar(membership.user, 'avatar avatar-board')));
    if (members.length > 4) holder.append(el('span', { className: 'avatar avatar-board avatar-more', text: `+${members.length - 4}` }));
  }

  function taskCard(task) {
    const card = el('article', { className: 'task-card', draggable: canManage(), 'data-task-id': String(task.id) });
    const menuButton = el('button', { className: 'task-menu-button', type: 'button', ariaLabel: `Actions for ${task.title}`, ariaExpanded: 'false' }, [icon('more_horiz', 'Task actions')]);
    const menu = el('div', { className: 'task-quick-menu hidden' }, [
      el('a', { href: `task-details.html?id=${task.id}`, text: 'Open details' }),
    ]);
    if (canChangeStatus(task)) {
      const completion = el('button', { type: 'button', text: task.status === 'done' ? 'Reopen task' : 'Mark complete' });
      completion.addEventListener('click', async () => {
        try {
          await TaskForgeAPI.request(`/tasks/${task.id}/${task.status === 'done' ? 'reopen' : 'complete'}/`, { method: 'PATCH' });
          toast(task.status === 'done' ? 'Task reopened.' : 'Task completed.');
          await reloadTasks();
        } catch (error) { toast(error.message, 'error'); }
      });
      menu.append(completion);
    }
    const menuControl = el('div', { className: 'task-menu-control' }, [menuButton, menu]);
    menuButton.addEventListener('click', (event) => {
      event.stopPropagation();
      menu.classList.toggle('hidden');
      menuButton.setAttribute('aria-expanded', String(!menu.classList.contains('hidden')));
    });
    menuControl.addEventListener('focusout', () => setTimeout(() => {
      if (!menuControl.contains(document.activeElement)) {
        menu.classList.add('hidden');
        menuButton.setAttribute('aria-expanded', 'false');
      }
    }, 0));
    const statusSelect = el('select', { className: 'status-select', ariaLabel: `Change status for ${task.title}`, disabled: !canChangeStatus(task) }, [
      el('option', { value: 'todo', text: 'To Do' }),
      el('option', { value: 'in_progress', text: 'In Progress' }),
      el('option', { value: 'done', text: 'Done' }),
    ]);
    statusSelect.value = task.status;
    statusSelect.addEventListener('change', async () => {
      try {
        await TaskForgeAPI.request(`/tasks/${task.id}/status/`, {
          method: 'PATCH',
          body: JSON.stringify({ status: statusSelect.value }),
        });
        toast('Task status updated.');
        await reloadTasks();
      } catch (error) {
        statusSelect.value = task.status;
        toast(error.message, 'error');
      }
    });
    const labelList = el('div', { className: 'label-list' }, task.labels.map((label) => el('span', { className: 'task-label', text: label.name, style: `--label-color:${label.color}` })));
    const description = task.description ? el('p', { className: 'task-card-description', text: task.description }) : null;
    const metrics = el('div', { className: 'task-metrics' }, [
      task.comment_count !== undefined ? metric('chat_bubble', task.comment_count, 'Comments') : null,
      task.attachment_count !== undefined ? metric('attachment', task.attachment_count, 'Attachments') : null,
      task.checklist_total !== undefined ? metric('checklist', `${task.checklist_completed || 0}/${task.checklist_total}`, 'Checklist progress') : null,
    ].filter(Boolean));
    const assignee = task.assigned_to
      ? avatar(task.assigned_to, 'avatar avatar-task')
      : el('span', { className: 'avatar avatar-task avatar-unassigned', text: '?', title: 'Unassigned' });
    card.classList.toggle('task-completed', task.status === 'done');
    card.append(
      el('div', { className: 'task-card-top' }, [labelList, menuControl]),
      el('h4', {}, [el('a', { href: `task-details.html?id=${task.id}`, text: task.title })]),
      description,
      el('div', { className: 'task-due-row' }, [icon(task.is_overdue ? 'warning' : 'event', 'Due date'), el('span', { className: task.is_overdue ? 'overdue' : '', text: dueText(task) }), el('span', { className: `badge badge-${task.priority}`, text: task.priority })]),
      el('div', { className: 'task-card-footer' }, [metrics, assignee]),
      statusSelect,
    );
    card.addEventListener('dragstart', () => card.classList.add('dragging'));
    card.addEventListener('dragend', () => card.classList.remove('dragging'));
    return card;
  }

  function renderBoard() {
    const definitions = [
      ['todo', 'To Do'],
      ['in_progress', 'In Progress'],
      ['done', 'Done'],
    ];
    const visible = filteredTasks();
    const board = document.getElementById('board');
    board.replaceChildren(...definitions.map(([status, label]) => {
      const statusTasks = visible.filter((task) => task.status === status).sort((a, b) => a.position - b.position);
      const list = el('div', { className: 'task-list', 'data-status': status }, statusTasks.map(taskCard));
      if (!statusTasks.length) list.append(el('div', { className: 'board-empty', text: 'No tasks in this section.' }));
      if (canManage()) {
        const addTask = el('button', { className: 'column-add-task', type: 'button' }, [icon('add', 'Add task'), el('span', { text: 'Add task' })]);
        addTask.addEventListener('click', taskForm);
        list.append(addTask);
      }
      if (canManage()) {
        list.addEventListener('dragover', (event) => event.preventDefault());
        list.addEventListener('drop', async (event) => {
          event.preventDefault();
          const dragged = document.querySelector('.task-card.dragging');
          if (!dragged) return;
          try {
            await TaskForgeAPI.request(`/tasks/${dragged.dataset.taskId}/position/`, {
              method: 'PATCH',
              body: JSON.stringify({ status, position: statusTasks.length }),
            });
            await reloadTasks();
          } catch (error) {
            toast(error.message, 'error');
          }
        });
      }
      return el('section', { className: 'board-column' }, [
        el('header', { className: 'board-column-header' }, [
          el('h3', { text: label }),
          el('span', { className: `badge badge-${status}`, text: String(statusTasks.length) }),
        ]),
        list,
      ]);
    }));
  }

  async function reloadTasks() {
    tasks = await TaskForgeAPI.request(`/projects/${projectId}/tasks/`);
    renderBoard();
  }

  function taskForm() {
    const form = el('form', { className: 'form-grid' });
    const title = el('input', { required: true, maxLength: 255 });
    const description = el('textarea');
    const assignee = el('select', {}, [el('option', { value: '', text: 'Unassigned' })]);
    members.forEach((membership) => assignee.append(el('option', {
      value: String(membership.user.id),
      text: membership.user.full_name || membership.user.username,
    })));
    const priority = el('select', {}, [
      el('option', { value: 'low', text: 'Low' }),
      el('option', { value: 'medium', text: 'Medium' }),
      el('option', { value: 'high', text: 'High' }),
    ]);
    priority.value = 'medium';
    const dueDate = el('input', { type: 'date' });
    const taskLabels = el('select', { multiple: true, size: Math.min(Math.max(labels.length, 2), 5), ariaLabel: 'Task labels' });
    labels.forEach((label) => taskLabels.append(el('option', { value: String(label.id), text: label.name })));
    const submit = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Create task' });
    form.append(
      el('div', { className: 'field' }, [el('label', { text: 'Title' }), title]),
      el('div', { className: 'field' }, [el('label', { text: 'Description' }), description]),
      el('div', { className: 'form-row' }, [
        el('div', { className: 'field' }, [el('label', { text: 'Assignee' }), assignee]),
        el('div', { className: 'field' }, [el('label', { text: 'Priority' }), priority]),
      ]),
      el('div', { className: 'field' }, [el('label', { text: 'Due date' }), dueDate]),
      el('div', { className: 'field' }, [el('label', { text: 'Labels' }), taskLabels]),
      el('div', { className: 'form-actions' }, [submit]),
    );
    const dialog = modal('Create task', form);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      setLoading(submit, true);
      try {
        const created = await TaskForgeAPI.request(`/projects/${projectId}/tasks/`, {
          method: 'POST',
          body: JSON.stringify({
            title: title.value,
            description: description.value,
            assigned_to_id: assignee.value ? Number(assignee.value) : null,
            priority: priority.value,
            due_date: dueDate.value || null,
          }),
        });
        const labelIds = [...taskLabels.selectedOptions].map((option) => Number(option.value));
        if (labelIds.length) await TaskForgeAPI.request(`/tasks/${created.id}/labels/`, { method: 'PATCH', body: JSON.stringify({ label_ids: labelIds }) });
        dialog.close();
        toast('Task created.');
        await reloadTasks();
      } catch (error) {
        toast(error.message, 'error');
      } finally {
        setLoading(submit, false);
      }
    });
    title.focus();
  }

  function labelsModal() {
    const wrapper = el('div');
    const form = el('form', { className: 'form-row' });
    const name = el('input', { placeholder: 'Label name', required: true, maxLength: 50 });
    const color = el('input', { type: 'color', value: '#175CD3', ariaLabel: 'Label color' });
    const add = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Add' });
    const list = el('div', { className: 'resource-list' });
    function render() {
      list.replaceChildren(...labels.map((label) => {
        const remove = el('button', { className: 'btn btn-small btn-quiet danger-text', type: 'button', text: 'Delete' });
        remove.addEventListener('click', async () => { if (confirm(`Delete label ${label.name}?`)) { await TaskForgeAPI.request(`/project-labels/${label.id}/`, { method: 'DELETE' }); await refresh(); } });
        return el('div', { className: 'resource-row' }, [el('span', { className: 'task-label', text: label.name, style: `--label-color:${label.color}` }), remove]);
      }));
    }
    async function refresh() { labels = await TaskForgeAPI.request(`/projects/${projectId}/labels/`); render(); populateLabels(); renderBoard(); }
    form.append(name, color, add);
    form.addEventListener('submit', async (event) => { event.preventDefault(); try { await TaskForgeAPI.request(`/projects/${projectId}/labels/`, { method: 'POST', body: JSON.stringify({ name: name.value, color: color.value }) }); name.value = ''; await refresh(); } catch (error) { toast(error.message, 'error'); } });
    wrapper.append(form, list); render(); modal('Project labels', wrapper);
  }

  async function openActivity() {
    const drawer = document.getElementById('activity-drawer');
    drawer.classList.add('open');
    document.getElementById('activity-toggle').setAttribute('aria-expanded', 'true');
    const list = document.getElementById('activity-list');
    list.replaceChildren(el('div', { className: 'loading', text: 'Loading activity...' }));
    try {
      const activities = await TaskForgeAPI.request(`/projects/${projectId}/activities/`);
      list.replaceChildren(...activities.map((item) => {
        const message = item.task_id
          ? el('a', { href: `task-details.html?id=${item.task_id}`, text: item.message })
          : el('p', { text: item.message });
        return el('article', { className: 'activity-item' }, [avatar(item.actor || { username: 'System' }), el('div', {}, [message, el('time', { text: formatDate(item.created_at, true) })])]);
      }));
      if (!activities.length) list.append(el('div', { className: 'empty-state', text: 'No project activity yet.' }));
    } catch (error) { list.replaceChildren(el('div', { className: 'danger-text', text: error.message })); }
  }

  function closeActivity() {
    document.getElementById('activity-drawer').classList.remove('open');
    document.getElementById('activity-toggle').setAttribute('aria-expanded', 'false');
  }

  function membersModal() {
    const wrapper = el('div');
    const form = el('form', { className: 'form-row' });
    const identifier = el('input', { placeholder: 'Username or email', required: true });
    const role = el('select', {}, [
      el('option', { value: 'member', text: 'Member' }),
      el('option', { value: 'manager', text: 'Manager' }),
    ]);
    const add = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Add' });
    form.append(identifier, role, add);
    const list = el('div', { className: 'member-list', style: 'margin-top:18px' });

    function renderMembers() {
      list.replaceChildren(...members.map((membership) => {
        const roleSelect = el('select', { disabled: membership.role === 'owner' }, [
          el('option', { value: 'member', text: 'Member' }),
          el('option', { value: 'manager', text: 'Manager' }),
          ...(membership.role === 'owner' ? [el('option', { value: 'owner', text: 'Owner' })] : []),
        ]);
        roleSelect.value = membership.role;
        roleSelect.addEventListener('change', async () => {
          try {
            await TaskForgeAPI.request(`/projects/${projectId}/members/${membership.id}/`, {
              method: 'PATCH', body: JSON.stringify({ role: roleSelect.value }),
            });
            toast('Member role updated.');
            await refreshMembers();
          } catch (error) { toast(error.message, 'error'); roleSelect.value = membership.role; }
        });
        const remove = el('button', { className: 'btn btn-small btn-quiet danger-text', type: 'button', text: 'Remove', disabled: membership.role === 'owner' });
        remove.addEventListener('click', async () => {
          if (!confirm(`Remove ${membership.user.username} from this project?`)) return;
          try {
            await TaskForgeAPI.request(`/projects/${projectId}/members/${membership.id}/`, { method: 'DELETE' });
            toast('Member removed.');
            await refreshMembers();
          } catch (error) { toast(error.message, 'error'); }
        });
        return el('div', { className: 'member-row' }, [
          el('div', { className: 'member-identity' }, [
            avatar(membership.user),
            el('div', {}, [el('strong', { text: membership.user.full_name || membership.user.username }), el('span', { text: membership.user.email })]),
          ]),
          roleSelect,
          remove,
        ]);
      }));
    }

    async function refreshMembers() {
      members = await TaskForgeAPI.request(`/projects/${projectId}/members/`);
      renderMembers();
      populateAssignees();
    }
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      setLoading(add, true);
      try {
        await TaskForgeAPI.request(`/projects/${projectId}/members/`, {
          method: 'POST', body: JSON.stringify({ identifier: identifier.value, role: role.value }),
        });
        identifier.value = '';
        toast('Member added.');
        await refreshMembers();
      } catch (error) { toast(error.message, 'error'); }
      finally { setLoading(add, false); }
    });
    wrapper.append(form, list);
    renderMembers();
    modal('Project members', wrapper);
  }

  document.getElementById('create-task').addEventListener('click', taskForm);
  document.getElementById('manage-members').addEventListener('click', membersModal);
  document.getElementById('manage-labels').addEventListener('click', labelsModal);
  document.getElementById('activity-toggle').addEventListener('click', openActivity);
  document.getElementById('activity-close').addEventListener('click', closeActivity);
  ['status-filter', 'priority-filter', 'assignee-filter', 'label-filter', 'due-filter'].forEach((id) => document.getElementById(id).addEventListener('change', renderBoard));
  document.getElementById('task-search').addEventListener('input', renderBoard);
  document.getElementById('clear-filters').addEventListener('click', () => { ['status-filter', 'priority-filter', 'assignee-filter', 'label-filter', 'due-filter'].forEach((id) => { document.getElementById(id).value = ''; }); document.getElementById('task-search').value = ''; renderBoard(); });
  await loadData();
  if (new URLSearchParams(location.search).get('activity') === 'open') await openActivity();
  TaskForgeRealtime.connect(`/projects/${projectId}/board/`, (event) => {
    if (!['task_created', 'task_updated', 'task_deleted', 'task_status_changed', 'comment_created', 'member_added', 'attachment_added', 'attachment_deleted', 'checklist_updated'].includes(event.type)) return;
    clearTimeout(realtimeReload);
    realtimeReload = setTimeout(() => {
      if (event.type === 'member_added') loadData();
      else reloadTasks().catch((error) => toast(error.message, 'error'));
      if (document.getElementById('activity-drawer').classList.contains('open')) openActivity();
    }, 120);
  });
});
