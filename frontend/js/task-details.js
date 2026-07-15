document.addEventListener('DOMContentLoaded', async () => {
  const currentUser = await TaskForgeUI.initShell('projects');
  if (!currentUser) return;
  const { el, avatar, formatDate, modal, toast, setLoading } = TaskForgeUI;
  const taskId = Number(new URLSearchParams(location.search).get('id'));
  if (!taskId) { window.location.replace('projects.html'); return; }
  let task;
  let project;
  let members = [];
  let comments = [];
  const canManage = () => ['owner', 'manager'].includes(project.current_user_role);

  async function load() {
    try {
      task = await TaskForgeAPI.request(`/tasks/${taskId}/`);
      [project, members, comments] = await Promise.all([
        TaskForgeAPI.request(`/projects/${task.project.id}/`),
        TaskForgeAPI.request(`/projects/${task.project.id}/members/`),
        TaskForgeAPI.request(`/tasks/${taskId}/comments/`),
      ]);
      renderTask();
      renderComments();
    } catch (error) { toast(error.message, 'error'); }
  }

  function detail(label, value) {
    return el('div', { className: 'detail-item' }, [el('dt', { text: label }), el('dd', { text: value })]);
  }

  function renderTask() {
    document.getElementById('task-title').textContent = task.title;
    document.getElementById('task-project').textContent = task.project.name;
    document.getElementById('back-to-board').href = `project-board.html?id=${task.project.id}`;
    const detailPanel = document.getElementById('task-detail');
    detailPanel.replaceChildren(
      el('section', { className: 'task-detail-section' }, [
        el('h3', { text: task.title }),
        el('p', { className: task.description ? '' : 'muted', text: task.description || 'No description provided.' }),
      ]),
      el('section', { className: 'task-detail-section' }, [
        el('dl', { className: 'detail-grid' }, [
          detail('Status', task.status.replace('_', ' ')),
          detail('Priority', task.priority),
          detail('Assignee', task.assigned_to?.full_name || task.assigned_to?.username || 'Unassigned'),
          detail('Created by', task.created_by.full_name || task.created_by.username),
          detail('Due date', task.due_date ? formatDate(task.due_date) : 'Not set'),
          detail('Position', String(task.position)),
          detail('Created', formatDate(task.created_at, true)),
          detail('Updated', formatDate(task.updated_at, true)),
        ]),
      ]),
    );
    const actions = document.getElementById('task-actions');
    actions.replaceChildren();
    if (canManage()) {
      const edit = el('button', { className: 'btn btn-secondary', type: 'button', text: 'Edit task' });
      edit.addEventListener('click', editTask);
      const remove = el('button', { className: 'btn btn-danger', type: 'button', text: 'Delete task' });
      remove.addEventListener('click', deleteTask);
      actions.append(edit, remove);
    }
    if (canManage() || task.assigned_to?.id === currentUser.id) {
      const statusSelect = el('select', { ariaLabel: 'Task status' }, [
        el('option', { value: 'todo', text: 'To Do' }),
        el('option', { value: 'in_progress', text: 'In Progress' }),
        el('option', { value: 'done', text: 'Done' }),
      ]);
      statusSelect.value = task.status;
      statusSelect.addEventListener('change', async () => {
        try {
          task = await TaskForgeAPI.request(`/tasks/${task.id}/status/`, {
            method: 'PATCH', body: JSON.stringify({ status: statusSelect.value }),
          });
          toast('Status updated.');
          await load();
        } catch (error) { toast(error.message, 'error'); statusSelect.value = task.status; }
      });
      actions.prepend(statusSelect);
    }
  }

  function editTask() {
    const form = el('form', { className: 'form-grid' });
    const title = el('input', { value: task.title, required: true });
    const description = el('textarea', { value: task.description });
    const assignee = el('select', {}, [el('option', { value: '', text: 'Unassigned' })]);
    members.forEach((membership) => assignee.append(el('option', { value: String(membership.user.id), text: membership.user.full_name || membership.user.username })));
    assignee.value = task.assigned_to ? String(task.assigned_to.id) : '';
    const priority = el('select', {}, ['low', 'medium', 'high'].map((value) => el('option', { value, text: value })));
    priority.value = task.priority;
    const dueDate = el('input', { type: 'date', value: task.due_date || '' });
    const submit = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Save changes' });
    form.append(
      el('div', { className: 'field' }, [el('label', { text: 'Title' }), title]),
      el('div', { className: 'field' }, [el('label', { text: 'Description' }), description]),
      el('div', { className: 'form-row' }, [el('div', { className: 'field' }, [el('label', { text: 'Assignee' }), assignee]), el('div', { className: 'field' }, [el('label', { text: 'Priority' }), priority])]),
      el('div', { className: 'field' }, [el('label', { text: 'Due date' }), dueDate]),
      el('div', { className: 'form-actions' }, [submit]),
    );
    const dialog = modal('Edit task', form);
    form.addEventListener('submit', async (event) => {
      event.preventDefault(); setLoading(submit, true);
      try {
        await TaskForgeAPI.request(`/tasks/${task.id}/`, { method: 'PATCH', body: JSON.stringify({ title: title.value, description: description.value, assigned_to_id: assignee.value ? Number(assignee.value) : null, priority: priority.value, due_date: dueDate.value || null }) });
        dialog.close(); toast('Task updated.'); await load();
      } catch (error) { toast(error.message, 'error'); }
      finally { setLoading(submit, false); }
    });
  }

  async function deleteTask() {
    if (!confirm(`Delete "${task.title}"?`)) return;
    try {
      await TaskForgeAPI.request(`/tasks/${task.id}/`, { method: 'DELETE' });
      window.location.replace(`project-board.html?id=${task.project.id}`);
    } catch (error) { toast(error.message, 'error'); }
  }

  function renderComments() {
    const list = document.getElementById('comment-list');
    list.replaceChildren();
    if (!comments.length) list.append(el('div', { className: 'empty-state', text: 'No comments yet.' }));
    comments.forEach((comment) => {
      const actions = el('div', { className: 'comment-actions' });
      if (comment.user.id === currentUser.id) {
        const edit = el('button', { className: 'btn btn-small btn-secondary', type: 'button', text: 'Edit' });
        edit.addEventListener('click', () => editComment(comment));
        actions.append(edit);
      }
      if (comment.user.id === currentUser.id || canManage()) {
        const remove = el('button', { className: 'btn btn-small btn-quiet danger-text', type: 'button', text: 'Delete' });
        remove.addEventListener('click', () => deleteComment(comment));
        actions.append(remove);
      }
      list.append(el('article', { className: 'comment' }, [
        el('header', { className: 'comment-head' }, [
          el('div', { className: 'member-identity' }, [avatar(comment.user), el('div', {}, [el('strong', { text: comment.user.full_name || comment.user.username }), el('span', { text: formatDate(comment.created_at, true) })])]),
        ]),
        el('p', { text: comment.message }),
        actions,
      ]));
    });
  }

  async function reloadComments() {
    comments = await TaskForgeAPI.request(`/tasks/${taskId}/comments/`);
    renderComments();
  }

  function editComment(comment) {
    const form = el('form', { className: 'form-grid' });
    const message = el('textarea', { value: comment.message, maxLength: 2000, required: true });
    const submit = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Save comment' });
    form.append(el('div', { className: 'field' }, [el('label', { text: 'Comment' }), message]), el('div', { className: 'form-actions' }, [submit]));
    const dialog = modal('Edit comment', form);
    form.addEventListener('submit', async (event) => {
      event.preventDefault(); setLoading(submit, true);
      try {
        await TaskForgeAPI.request(`/comments/${comment.id}/`, { method: 'PATCH', body: JSON.stringify({ message: message.value }) });
        dialog.close(); toast('Comment updated.'); await reloadComments();
      } catch (error) { toast(error.message, 'error'); }
      finally { setLoading(submit, false); }
    });
  }

  async function deleteComment(comment) {
    if (!confirm('Delete this comment?')) return;
    try { await TaskForgeAPI.request(`/comments/${comment.id}/`, { method: 'DELETE' }); toast('Comment deleted.'); await reloadComments(); }
    catch (error) { toast(error.message, 'error'); }
  }

  document.getElementById('comment-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = document.getElementById('comment-message');
    const button = event.currentTarget.querySelector('button');
    setLoading(button, true, 'Posting...');
    try {
      await TaskForgeAPI.request(`/tasks/${taskId}/comments/`, { method: 'POST', body: JSON.stringify({ message: message.value }) });
      message.value = ''; toast('Comment added.'); await reloadComments();
    } catch (error) { toast(error.message, 'error'); }
    finally { setLoading(button, false); }
  });

  await load();
});
