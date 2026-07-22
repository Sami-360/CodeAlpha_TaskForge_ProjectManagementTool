(function () {
  function el(tag, options = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(options).forEach(([key, value]) => {
      if (key === 'className') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key === 'style') node.setAttribute('style', value);
      else if (key.startsWith('data-')) node.setAttribute(key, value);
      else node[key] = value;
    });
    children.filter(Boolean).forEach((child) => node.append(child));
    return node;
  }

  function initials(user = {}) {
    const value = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.full_name || user.username || 'U';
    return value.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
  }

  function avatar(user = {}, className = 'avatar') {
    const label = user.full_name || user.username || 'User';
    const fallback = () => el('span', { className, text: initials(user), title: label, ariaLabel: `${label} avatar` });
    if (!user.avatar) return fallback();
    const image = el('img', { className, src: user.avatar, alt: `${label} avatar`, title: label });
    image.addEventListener('error', () => image.replaceWith(fallback()), { once: true });
    return image;
  }

  function formatDate(value, includeTime = false) {
    if (!value) return 'Not set';
    const options = includeTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' };
    return new Intl.DateTimeFormat(undefined, options).format(new Date(value));
  }

  function toast(message, type = 'success') {
    let region = document.getElementById('toast-region');
    if (!region) {
      region = el('div', { id: 'toast-region', className: 'toast-region', ariaLive: 'polite' });
      document.body.append(region);
    }
    const item = el('div', { className: `toast ${type}`, text: message, role: 'status' });
    region.append(item);
    setTimeout(() => item.remove(), 4200);
  }

  function setLoading(button, loading, label = 'Working...') {
    if (!button) return;
    if (loading) {
      button.dataset.originalLabel = button.textContent;
      button.textContent = label;
      button.disabled = true;
    } else {
      button.textContent = button.dataset.originalLabel || button.textContent;
      button.disabled = false;
    }
  }

  function modal(title, content) {
    const returnFocus = document.activeElement;
    const backdrop = el('div', { className: 'modal-backdrop' });
    const dialog = el('section', { className: 'modal', role: 'dialog', ariaModal: 'true', ariaLabel: title });
    const closeButton = el('button', { className: 'icon-btn', type: 'button', ariaLabel: 'Close', text: 'X' });
    const close = () => {
      backdrop.remove();
      document.removeEventListener('keydown', escape);
      if (returnFocus?.isConnected) returnFocus.focus();
    };
    const escape = (event) => { if (event.key === 'Escape') close(); };
    closeButton.addEventListener('click', close);
    dialog.append(el('header', { className: 'modal-header' }, [el('h2', { text: title }), closeButton]), el('div', { className: 'modal-body' }, [content]));
    backdrop.append(dialog);
    backdrop.addEventListener('click', (event) => { if (event.target === backdrop) close(); });
    document.addEventListener('keydown', escape);
    document.body.append(backdrop);
    closeButton.focus();
    return { close, dialog };
  }

  function notificationTarget(item) {
    if (item.task_id) return `task-details.html?id=${item.task_id}`;
    if (item.project_id) return `project-board.html?id=${item.project_id}`;
    return '';
  }

  async function loadNotifications() {
    const panel = document.getElementById('notification-panel');
    if (!panel) return;
    panel.replaceChildren(el('div', { className: 'loading', text: 'Loading notifications...' }));
    try {
      const data = await TaskForgeAPI.request('/notifications/');
      const count = document.getElementById('notification-count');
      if (count) {
        count.textContent = data.unread_count > 99 ? '99+' : String(data.unread_count);
        count.classList.toggle('hidden', data.unread_count === 0);
      }
      TaskForgeSidebar.setUnread(data.unread_count);
      panel.replaceChildren();
      const markAll = el('button', { className: 'btn btn-small btn-quiet', type: 'button', text: 'Mark all read', disabled: data.unread_count === 0 });
      markAll.addEventListener('click', async () => {
        await TaskForgeAPI.request('/notifications/read-all/', { method: 'PATCH' });
        await loadNotifications();
      });
      panel.append(el('div', { className: 'panel-header' }, [el('h3', { text: 'Notifications' }), markAll]));
      if (!data.results.length) panel.append(el('div', { className: 'empty-state', text: 'No notifications yet.' }));
      const seen = new Set();
      data.results.forEach((item) => {
        if (seen.has(item.id)) return;
        seen.add(item.id);
        const target = notificationTarget(item);
        const content = target ? el('a', { href: target, text: item.message }) : el('p', { text: item.message });
        const row = el('article', { className: `notification-item ${item.is_read ? '' : 'unread'}`, 'data-notification-id': String(item.id) }, [content, el('time', { text: formatDate(item.created_at, true) })]);
        if (!item.is_read) {
          const read = el('button', { className: 'notification-read', type: 'button', text: 'Mark read', ariaLabel: `Mark notification ${item.id} as read` });
          read.addEventListener('click', async (event) => {
            event.preventDefault();
            await TaskForgeAPI.request(`/notifications/${item.id}/read/`, { method: 'PATCH' });
            await loadNotifications();
          });
          row.append(read);
        }
        panel.append(row);
      });
    } catch (error) {
      panel.replaceChildren(el('div', { className: 'empty-state danger-text', text: error.message }));
    }
  }

  function enhanceTopbar(user) {
    const topbar = document.querySelector('.topbar');
    const actions = topbar?.querySelector('.topbar-actions');
    if (!topbar || !actions || topbar.dataset.enhanced === 'true') return;
    topbar.dataset.enhanced = 'true';
    const search = el('div', { className: 'global-search' });
    const input = el('input', { type: 'search', placeholder: 'Search projects and tasks', ariaLabel: 'Global search', autocomplete: 'off' });
    const clear = el('button', { className: 'search-clear hidden', type: 'button', text: 'X', ariaLabel: 'Clear search' });
    const results = el('div', { className: 'search-results hidden', role: 'listbox' });
    let timer;
    let requestNumber = 0;
    function closeSearch() { results.classList.add('hidden'); }
    function group(title, items, mapper) {
      if (!items.length) return null;
      const section = el('section', { className: 'search-group' }, [el('h3', { text: title })]);
      items.forEach((item) => section.append(mapper(item)));
      return section;
    }
    async function runSearch() {
      const query = input.value.trim();
      clear.classList.toggle('hidden', !query);
      if (query.length < 2) {
        results.replaceChildren(el('div', { className: 'search-message', text: query ? 'Enter at least 2 characters.' : 'Start typing to search.' }));
        results.classList.remove('hidden');
        return;
      }
      const sequence = ++requestNumber;
      results.replaceChildren(el('div', { className: 'search-message', text: 'Searching...' }));
      results.classList.remove('hidden');
      try {
        const data = await TaskForgeAPI.request(`/search/?q=${encodeURIComponent(query)}`);
        if (sequence !== requestNumber) return;
        const projects = group('Projects', data.projects, (item) => el('a', { className: 'search-result', href: `project-board.html?id=${item.id}` }, [el('strong', { text: item.name }), el('span', { text: item.description || 'No description' })]));
        const tasks = group('Tasks', data.tasks, (item) => el('a', { className: 'search-result', href: `task-details.html?id=${item.id}` }, [el('strong', { text: item.title }), el('span', { text: `${item.project.name} - ${item.status.replace('_', ' ')}` })]));
        results.replaceChildren(...[projects, tasks].filter(Boolean));
        if (!projects && !tasks) results.append(el('div', { className: 'search-message', text: 'No matching projects or tasks.' }));
      } catch (error) {
        results.replaceChildren(el('div', { className: 'search-message danger-text', text: error.message }));
      }
    }
    input.addEventListener('focus', runSearch);
    input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(runSearch, 260); });
    input.addEventListener('keydown', (event) => { if (event.key === 'Escape') { closeSearch(); input.blur(); } });
    clear.addEventListener('click', () => { input.value = ''; input.focus(); runSearch(); });
    search.append(input, clear, results);
    topbar.insertBefore(search, actions);

    const oldChip = actions.querySelector('.user-chip');
    oldChip?.remove();
    const notificationButton = actions.querySelector('#notification-button');
    if (notificationButton) {
      const count = notificationButton.querySelector('#notification-count');
      notificationButton.replaceChildren(el('span', { className: 'material-symbols-outlined', text: 'notifications', ariaHidden: 'true' }));
      if (count) notificationButton.append(count);
    }
    const accountButton = el('button', { className: 'account-button', type: 'button', ariaExpanded: 'false', ariaLabel: 'Open account menu' }, [avatar(user, 'avatar'), el('span', { text: user.full_name || user.username })]);
    const menu = el('div', { className: 'account-menu hidden' }, [
      el('a', { href: 'profile.html', text: 'View profile' }),
      el('a', { href: 'profile.html?edit=true', text: 'Edit profile' }),
      el('button', { type: 'button', text: 'Sign out' }),
    ]);
    menu.lastChild.addEventListener('click', logout);
    accountButton.addEventListener('click', () => {
      menu.classList.toggle('hidden');
      accountButton.setAttribute('aria-expanded', String(!menu.classList.contains('hidden')));
    });
    const account = el('div', { className: 'account-control' }, [accountButton, menu]);
    actions.append(account);
    document.addEventListener('click', (event) => {
      if (!search.contains(event.target)) closeSearch();
      if (!account.contains(event.target)) { menu.classList.add('hidden'); accountButton.setAttribute('aria-expanded', 'false'); }
    });
  }

  function logout() {
    TaskForgeAPI.clearTokens();
    window.location.replace(TaskForgeConfig.loginPage);
  }

  async function initShell(activePage) {
    if (!TaskForgeAPI.getRefreshToken()) { window.location.replace(TaskForgeConfig.loginPage); return null; }
    TaskForgeSidebar.init();
    const activeLink = document.querySelector(`[data-nav="${activePage}"]`);
    activeLink?.classList.add('active');
    activeLink?.setAttribute('aria-current', 'page');
    document.getElementById('logout-button')?.addEventListener('click', logout);
    const notificationButton = document.getElementById('notification-button');
    notificationButton?.addEventListener('click', async () => {
      const panel = document.getElementById('notification-panel');
      panel.classList.toggle('hidden');
      const isOpen = !panel.classList.contains('hidden');
      notificationButton.setAttribute('aria-expanded', String(isOpen));
      TaskForgeSidebar.setInboxOpen(isOpen);
      if (isOpen) await loadNotifications();
    });
    try {
      const user = await TaskForgeAPI.request('/auth/me/');
      document.querySelectorAll('[data-user-name]').forEach((node) => { node.textContent = user.full_name || user.username; });
      TaskForgeSidebar.setUser(user);
      enhanceTopbar(user);
      await loadNotifications();
      if (new URLSearchParams(location.search).get('notifications') === 'open') {
        document.getElementById('notification-panel')?.classList.remove('hidden');
        notificationButton?.setAttribute('aria-expanded', 'true');
        TaskForgeSidebar.setInboxOpen(true);
      }
      TaskForgeRealtime.connect('/notifications/', (event) => { if (event.type === 'notification_created') loadNotifications(); });
      return user;
    } catch (error) {
      TaskForgeAPI.clearTokens();
      window.location.replace(TaskForgeConfig.loginPage);
      return null;
    }
  }

  window.TaskForgeUI = { el, avatar, initials, formatDate, toast, setLoading, modal, initShell, loadNotifications };
})();
