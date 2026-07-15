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
  let realtimeReload;

  const canManage = () => ['owner', 'manager'].includes(project.current_user_role);
  const canChangeStatus = (task) => canManage() || task.assigned_to?.id === currentUser.id;

  async function loadData() {
    try {
      [project, members, tasks] = await Promise.all([
        TaskForgeAPI.request(`/projects/${projectId}/`),
        TaskForgeAPI.request(`/projects/${projectId}/members/`),
        TaskForgeAPI.request(`/projects/${projectId}/tasks/`),
      ]);
      document.getElementById('project-name').textContent = project.name;
      document.getElementById('project-description').textContent = project.description || 'No project description.';
      document.getElementById('create-task').classList.toggle('hidden', !canManage());
      document.getElementById('manage-members').classList.toggle('hidden', project.current_user_role !== 'owner');
      populateAssignees();
      renderBoard();
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  function populateAssignees() {
    const filter = document.getElementById('assignee-filter');
    const current = filter.value;
    filter.replaceChildren(el('option', { value: '', text: 'All assignees' }));
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
    const overdue = document.getElementById('overdue-filter').value;
    return tasks.filter((task) =>
      (!priority || task.priority === priority)
      && (!assignee || task.assigned_to?.id === Number(assignee))
      && (!overdue || String(task.is_overdue) === overdue)
    );
  }

  function taskCard(task) {
    const card = el('article', { className: 'task-card', draggable: canManage(), 'data-task-id': String(task.id) });
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
    card.append(
      el('h4', {}, [el('a', { href: `task-details.html?id=${task.id}`, text: task.title })]),
      el('span', { className: `badge badge-${task.priority}`, text: task.priority }),
      el('div', { className: 'task-card-meta' }, [
        el('span', { text: task.assigned_to?.full_name || task.assigned_to?.username || 'Unassigned' }),
        el('span', { className: task.is_overdue ? 'overdue' : '', text: task.due_date ? formatDate(task.due_date) : 'No due date' }),
      ]),
      el('div', { className: 'task-card-meta' }, [
        el('span', { text: `${task.comment_count} comments` }),
        el('span', { text: `#${task.position}` }),
      ]),
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
      if (canManage()) {
        list.addEventListener('dragover', (event) => event.preventDefault());
        list.addEventListener('drop', async (event) => {
          event.preventDefault();
          const dragged = document.querySelector('.task-card.dragging');
          if (!dragged) return;
          try {
            await TaskForgeAPI.request(`/tasks/${dragged.dataset.taskId}/position/`, {
              method: 'PATCH',
              body: JSON.stringify({ status, position: list.children.length }),
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
    const submit = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Create task' });
    form.append(
      el('div', { className: 'field' }, [el('label', { text: 'Title' }), title]),
      el('div', { className: 'field' }, [el('label', { text: 'Description' }), description]),
      el('div', { className: 'form-row' }, [
        el('div', { className: 'field' }, [el('label', { text: 'Assignee' }), assignee]),
        el('div', { className: 'field' }, [el('label', { text: 'Priority' }), priority]),
      ]),
      el('div', { className: 'field' }, [el('label', { text: 'Due date' }), dueDate]),
      el('div', { className: 'form-actions' }, [submit]),
    );
    const dialog = modal('Create task', form);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      setLoading(submit, true);
      try {
        await TaskForgeAPI.request(`/projects/${projectId}/tasks/`, {
          method: 'POST',
          body: JSON.stringify({
            title: title.value,
            description: description.value,
            assigned_to_id: assignee.value ? Number(assignee.value) : null,
            priority: priority.value,
            due_date: dueDate.value || null,
          }),
        });
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
  ['priority-filter', 'assignee-filter', 'overdue-filter'].forEach((id) => document.getElementById(id).addEventListener('change', renderBoard));
  await loadData();
  TaskForgeRealtime.connect(`/projects/${projectId}/board/`, (event) => {
    if (!['task_created', 'task_updated', 'task_deleted', 'task_status_changed', 'comment_created', 'member_added'].includes(event.type)) return;
    clearTimeout(realtimeReload);
    realtimeReload = setTimeout(() => {
      if (event.type === 'member_added') loadData();
      else reloadTasks().catch((error) => toast(error.message, 'error'));
    }, 120);
  });
});
