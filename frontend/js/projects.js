document.addEventListener('DOMContentLoaded', async () => {
  const user = await TaskForgeUI.initShell('projects');
  if (!user) return;
  const { el, modal, toast, setLoading } = TaskForgeUI;
  let projects = [];

  function progress(project) {
    const total = project.task_stats.total;
    return total ? Math.round((project.task_stats.done / total) * 100) : 0;
  }

  function render() {
    const query = document.getElementById('project-search').value.trim().toLowerCase();
    const role = document.getElementById('role-filter').value;
    const filtered = projects.filter((project) =>
      (!query || project.name.toLowerCase().includes(query))
      && (!role || project.current_user_role === role)
    );
    const list = document.getElementById('project-list');
    list.replaceChildren();
    if (!filtered.length) {
      list.append(el('div', { className: 'panel empty-state', text: 'No matching projects.' }));
      return;
    }
    filtered.forEach((project) => {
      const value = progress(project);
      const actions = el('div', { className: 'project-actions' }, [
        el('a', { className: 'btn btn-small btn-primary', href: `project-board.html?id=${project.id}`, text: 'Open board' }),
      ]);
      if (project.current_user_role === 'owner') {
        const edit = el('button', { className: 'btn btn-small btn-secondary', type: 'button', text: 'Edit' });
        edit.addEventListener('click', () => openProjectForm(project));
        const remove = el('button', { className: 'btn btn-small btn-quiet danger-text', type: 'button', text: 'Delete' });
        remove.addEventListener('click', () => deleteProject(project));
        actions.append(edit, remove);
      }
      list.append(el('article', { className: 'panel project-card' }, [
        el('div', { className: 'project-meta' }, [
          el('h3', { text: project.name }),
          el('span', { className: `badge badge-${project.current_user_role}`, text: project.current_user_role }),
        ]),
        el('p', { text: project.description || 'No description provided.' }),
        el('div', { className: 'progress-track', title: `${value}% complete` }, [
          el('div', { className: 'progress-fill', style: `width:${value}%` }),
        ]),
        el('div', { className: 'project-meta' }, [
          el('span', { text: `${project.member_count} members` }),
          el('span', { text: `${project.task_stats.done}/${project.task_stats.total} tasks done` }),
        ]),
        actions,
      ]));
    });
  }

  async function loadProjects() {
    const list = document.getElementById('project-list');
    list.replaceChildren(el('div', { className: 'loading', text: 'Loading projects...' }));
    try {
      projects = await TaskForgeAPI.request('/projects/');
      render();
    } catch (error) {
      list.replaceChildren(el('div', { className: 'panel empty-state danger-text', text: error.message }));
    }
  }

  function openProjectForm(project = null) {
    const form = el('form', { className: 'form-grid' });
    const name = el('input', { name: 'name', required: true, maxLength: 200, value: project?.name || '' });
    const description = el('textarea', { name: 'description', value: project?.description || '' });
    const submit = el('button', { className: 'btn btn-primary', type: 'submit', text: project ? 'Save changes' : 'Create project' });
    form.append(
      el('div', { className: 'field' }, [el('label', { text: 'Project name' }), name]),
      el('div', { className: 'field' }, [el('label', { text: 'Description' }), description]),
      el('div', { className: 'form-actions' }, [submit]),
    );
    const dialog = modal(project ? 'Edit project' : 'Create project', form);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      setLoading(submit, true);
      try {
        await TaskForgeAPI.request(project ? `/projects/${project.id}/` : '/projects/', {
          method: project ? 'PATCH' : 'POST',
          body: JSON.stringify({ name: name.value, description: description.value }),
        });
        dialog.close();
        toast(project ? 'Project updated.' : 'Project created.');
        await loadProjects();
      } catch (error) {
        toast(error.message, 'error');
      } finally {
        setLoading(submit, false);
      }
    });
    name.focus();
  }

  async function deleteProject(project) {
    if (!window.confirm(`Delete "${project.name}" and all related work?`)) return;
    try {
      await TaskForgeAPI.request(`/projects/${project.id}/`, { method: 'DELETE' });
      toast('Project deleted.');
      await loadProjects();
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  document.getElementById('create-project').addEventListener('click', () => openProjectForm());
  document.getElementById('project-search').addEventListener('input', render);
  document.getElementById('role-filter').addEventListener('change', render);
  await loadProjects();
  if (new URLSearchParams(location.search).get('action') === 'create') openProjectForm();
});
