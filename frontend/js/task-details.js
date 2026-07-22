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
  let attachments = [];
  let checklists = [];
  let labels = [];
  const canManage = () => ['owner', 'manager'].includes(project.current_user_role);

  async function load() {
    try {
      task = await TaskForgeAPI.request(`/tasks/${taskId}/`);
      [project, members, comments, attachments, checklists, labels] = await Promise.all([
        TaskForgeAPI.request(`/projects/${task.project.id}/`),
        TaskForgeAPI.request(`/projects/${task.project.id}/members/`),
        TaskForgeAPI.request(`/tasks/${taskId}/comments/`),
        TaskForgeAPI.request(`/tasks/${taskId}/attachments/`),
        TaskForgeAPI.request(`/tasks/${taskId}/checklists/`),
        TaskForgeAPI.request(`/projects/${task.project.id}/labels/`),
      ]);
      renderTask();
      renderComments();
      renderAttachments();
      renderChecklists();
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
        el('div', { className: 'label-list' }, task.labels.map((label) => el('span', { className: 'task-label', text: label.name, style: `--label-color:${label.color}` }))),
      ]),
      el('section', { className: 'task-detail-section' }, [
        el('dl', { className: 'detail-grid' }, [
          detail('Status', task.status.replace('_', ' ')),
          detail('Priority', task.priority),
          detail('Assignee', task.assigned_to?.full_name || task.assigned_to?.username || 'Unassigned'),
          detail('Created by', task.created_by.full_name || task.created_by.username),
          detail('Due date', dueStateLabel(task)),
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
      const manageLabels = el('button', { className: 'btn btn-secondary', type: 'button', text: 'Labels' });
      manageLabels.addEventListener('click', editLabels);
      actions.append(manageLabels);
    }
    if (canManage() || task.assigned_to?.id === currentUser.id) {
      const completion = el('button', { className: 'btn btn-secondary', type: 'button', text: task.status === 'done' ? 'Reopen' : 'Complete' });
      completion.addEventListener('click', async () => {
        try {
          task = await TaskForgeAPI.request(`/tasks/${task.id}/${task.status === 'done' ? 'reopen' : 'complete'}/`, { method: 'PATCH' });
          toast(task.status === 'done' ? 'Task completed.' : 'Task reopened.');
          await load();
        } catch (error) { toast(error.message, 'error'); }
      });
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
      actions.prepend(statusSelect, completion);
    }
  }

  function dueStateLabel(value) {
    const states = {
      no_due_date: 'No due date', due_today: 'Due today', due_tomorrow: 'Due tomorrow',
      due_soon: `Due soon (${formatDate(value.due_date)})`, overdue: `Overdue (${formatDate(value.due_date)})`,
      completed: 'Completed', scheduled: formatDate(value.due_date),
    };
    return states[value.due_state] || 'Not set';
  }

  function editLabels() {
    const form = el('form', { className: 'form-grid' });
    const choices = el('div', { className: 'label-picker' });
    labels.forEach((label) => {
      const checkbox = el('input', { type: 'checkbox', value: String(label.id), checked: task.labels.some((item) => item.id === label.id) });
      choices.append(el('label', { className: 'label-choice' }, [checkbox, el('span', { className: 'task-label', text: label.name, style: `--label-color:${label.color}` })]));
    });
    const submit = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Save labels' });
    form.append(choices, el('div', { className: 'form-actions' }, [submit]));
    const dialog = modal('Task labels', form);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const labelIds = [...choices.querySelectorAll('input:checked')].map((input) => Number(input.value));
      try {
        task = await TaskForgeAPI.request(`/tasks/${task.id}/labels/`, { method: 'PATCH', body: JSON.stringify({ label_ids: labelIds }) });
        dialog.close(); renderTask(); toast('Labels updated.');
      } catch (error) { toast(error.message, 'error'); }
    });
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

  function readableSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function renderAttachments() {
    const list = document.getElementById('attachment-list');
    list.replaceChildren();
    if (!attachments.length) list.append(el('div', { className: 'empty-state', text: 'No attachments yet.' }));
    attachments.forEach((item) => {
      const open = el('button', { className: 'btn btn-small btn-secondary', type: 'button', text: 'Download' });
      open.addEventListener('click', async () => { try { await TaskForgeAPI.download(`/task-attachments/${item.id}/download/`, item.original_name); } catch (error) { toast(error.message, 'error'); } });
      const actions = el('div', { className: 'resource-actions' }, [open]);
      if (item.uploaded_by.id === currentUser.id || canManage()) {
        const remove = el('button', { className: 'btn btn-small btn-quiet danger-text', type: 'button', text: 'Delete' });
        remove.addEventListener('click', async () => {
          if (!confirm(`Delete ${item.original_name}?`)) return;
          try { await TaskForgeAPI.request(`/task-attachments/${item.id}/`, { method: 'DELETE' }); await reloadAttachments(); toast('Attachment deleted.'); }
          catch (error) { toast(error.message, 'error'); }
        });
        actions.append(remove);
      }
      list.append(el('article', { className: 'resource-row' }, [
        el('div', {}, [el('strong', { text: item.original_name }), el('small', { text: `${readableSize(item.file_size)} - ${item.uploaded_by.full_name || item.uploaded_by.username} - ${formatDate(item.uploaded_at, true)}` })]),
        actions,
      ]));
    });
  }

  async function reloadAttachments() {
    attachments = await TaskForgeAPI.request(`/tasks/${taskId}/attachments/`);
    renderAttachments();
  }

  document.getElementById('attachment-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = document.getElementById('attachment-file');
    const button = event.currentTarget.querySelector('button');
    if (!input.files[0]) return;
    const data = new FormData();
    data.set('file', input.files[0]);
    setLoading(button, true, 'Uploading...');
    try { await TaskForgeAPI.request(`/tasks/${taskId}/attachments/`, { method: 'POST', body: data }); input.value = ''; await reloadAttachments(); toast('Attachment uploaded.'); }
    catch (error) { toast(error.message, 'error'); }
    finally { setLoading(button, false); }
  });

  function renderChecklists() {
    document.getElementById('add-checklist').classList.toggle('hidden', !canManage());
    const list = document.getElementById('checklist-list');
    list.replaceChildren();
    if (!checklists.length) list.append(el('div', { className: 'empty-state', text: 'No checklists yet.' }));
    checklists.forEach((checklist) => {
      const items = el('div', { className: 'checklist-items' });
      checklist.items.forEach((item) => {
        const checkbox = el('input', { type: 'checkbox', checked: item.is_completed, disabled: !(canManage() || task.assigned_to?.id === currentUser.id), ariaLabel: `Complete ${item.text}` });
        checkbox.addEventListener('change', async () => {
          try { await TaskForgeAPI.request(`/checklist-items/${item.id}/toggle/`, { method: 'PATCH' }); await reloadChecklists(); }
          catch (error) { checkbox.checked = !checkbox.checked; toast(error.message, 'error'); }
        });
        items.append(el('label', { className: `checklist-item ${item.is_completed ? 'completed' : ''}` }, [checkbox, el('span', { text: item.text })]));
      });
      const controls = el('div', { className: 'resource-actions' });
      if (canManage() || task.assigned_to?.id === currentUser.id) {
        const add = el('button', { className: 'btn btn-small btn-secondary', type: 'button', text: 'Add item' });
        add.addEventListener('click', () => addChecklistItem(checklist));
        controls.append(add);
      }
      if (canManage()) {
        const remove = el('button', { className: 'btn btn-small btn-quiet danger-text', type: 'button', text: 'Delete' });
        remove.addEventListener('click', async () => { if (confirm('Delete this checklist?')) { await TaskForgeAPI.request(`/checklists/${checklist.id}/`, { method: 'DELETE' }); await reloadChecklists(); } });
        controls.append(remove);
      }
      list.append(el('section', { className: 'checklist' }, [
        el('div', { className: 'checklist-head' }, [el('strong', { text: checklist.title }), el('span', { text: `${checklist.completed_count}/${checklist.total_count}` })]),
        el('div', { className: 'progress-track' }, [el('div', { className: 'progress-fill', style: `width:${checklist.completed_percentage}%` })]),
        items, controls,
      ]));
    });
  }

  async function reloadChecklists() {
    checklists = await TaskForgeAPI.request(`/tasks/${taskId}/checklists/`);
    renderChecklists();
  }

  function addChecklistItem(checklist) {
    const form = el('form', { className: 'form-grid' });
    const text = el('input', { required: true, maxLength: 300 });
    const submit = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Add item' });
    form.append(el('div', { className: 'field' }, [el('label', { text: 'Item' }), text]), submit);
    const dialog = modal('Add checklist item', form);
    form.addEventListener('submit', async (event) => { event.preventDefault(); try { await TaskForgeAPI.request(`/checklists/${checklist.id}/items/`, { method: 'POST', body: JSON.stringify({ text: text.value, position: checklist.items.length }) }); dialog.close(); await reloadChecklists(); } catch (error) { toast(error.message, 'error'); } });
  }

  document.getElementById('add-checklist').addEventListener('click', () => {
    const form = el('form', { className: 'form-grid' });
    const title = el('input', { required: true, maxLength: 150 });
    const submit = el('button', { className: 'btn btn-primary', type: 'submit', text: 'Create checklist' });
    form.append(el('div', { className: 'field' }, [el('label', { text: 'Title' }), title]), submit);
    const dialog = modal('Create checklist', form);
    form.addEventListener('submit', async (event) => { event.preventDefault(); try { await TaskForgeAPI.request(`/tasks/${taskId}/checklists/`, { method: 'POST', body: JSON.stringify({ title: title.value }) }); dialog.close(); await reloadChecklists(); } catch (error) { toast(error.message, 'error'); } });
  });

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
