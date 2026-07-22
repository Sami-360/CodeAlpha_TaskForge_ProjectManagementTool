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

  function initials(user) {
    const value = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username || 'U';
    return value.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
  }

  function avatar(user, className = 'avatar') {
    if (user.avatar) return el('img', { className, src: user.avatar, alt: '' });
    return el('span', { className, text: initials(user), ariaHidden: 'true' });
  }

  function formatDate(value, includeTime = false) {
    if (!value) return 'Not set';
    const options = includeTime
      ? { dateStyle: 'medium', timeStyle: 'short' }
      : { dateStyle: 'medium' };
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
    const close = () => backdrop.remove();
    const backdrop = el('div', { className: 'modal-backdrop' });
    const dialog = el('section', { className: 'modal', role: 'dialog', ariaModal: 'true' });
    const closeButton = el('button', { className: 'icon-btn', type: 'button', ariaLabel: 'Close', text: 'X' });
    closeButton.addEventListener('click', close);
    dialog.append(
      el('header', { className: 'modal-header' }, [el('h2', { text: title }), closeButton]),
      el('div', { className: 'modal-body' }, [content]),
    );
    backdrop.append(dialog);
    backdrop.addEventListener('click', (event) => { if (event.target === backdrop) close(); });
    document.addEventListener('keydown', function escape(event) {
      if (event.key === 'Escape') {
        close();
        document.removeEventListener('keydown', escape);
      }
    });
    document.body.append(backdrop);
    closeButton.focus();
    return { close, dialog };
  }

  async function loadNotifications() {
    const panel = document.getElementById('notification-panel');
    if (!panel) return;
    panel.replaceChildren(el('div', { className: 'loading', text: 'Loading notifications...' }));
    try {
      const data = await TaskForgeAPI.request('/notifications/');
      const count = document.getElementById('notification-count');
      count.textContent = String(data.unread_count);
      count.classList.toggle('hidden', data.unread_count === 0);
      panel.replaceChildren();
      const header = el('div', { className: 'panel-header' }, [
        el('h3', { text: 'Notifications' }),
        el('button', { className: 'btn btn-small btn-quiet', type: 'button', text: 'Mark all read' }),
      ]);
      header.lastChild.addEventListener('click', async () => {
        await TaskForgeAPI.request('/notifications/read-all/', { method: 'PATCH' });
        await loadNotifications();
      });
      panel.append(header);
      if (!data.results.length) panel.append(el('div', { className: 'empty-state', text: 'No notifications yet.' }));
      data.results.forEach((item) => {
        const row = el('article', { className: `notification-item ${item.is_read ? '' : 'unread'}` }, [
          el('p', { text: item.message }),
          el('time', { text: formatDate(item.created_at, true) }),
        ]);
        if (!item.is_read) row.addEventListener('click', async () => {
          await TaskForgeAPI.request(`/notifications/${item.id}/read/`, { method: 'PATCH' });
          await loadNotifications();
        });
        panel.append(row);
      });
    } catch (error) {
      panel.replaceChildren(el('div', { className: 'empty-state danger-text', text: error.message }));
    }
  }

  async function initShell(activePage) {
    if (!TaskForgeAPI.getRefreshToken()) {
      window.location.replace(TaskForgeConfig.loginPage);
      return null;
    }
    TaskForgeSidebar.init();
    document.querySelector(`[data-nav="${activePage}"]`)?.classList.add('active');
    document.getElementById('logout-button')?.addEventListener('click', () => {
      TaskForgeAPI.clearTokens();
      window.location.replace(TaskForgeConfig.loginPage);
    });
    const notificationButton = document.getElementById('notification-button');
    notificationButton?.addEventListener('click', async () => {
      const panel = document.getElementById('notification-panel');
      panel.classList.toggle('hidden');
      if (!panel.classList.contains('hidden')) await loadNotifications();
    });
    try {
      const user = await TaskForgeAPI.request('/auth/me/');
      document.querySelectorAll('[data-user-name]').forEach((node) => {
        node.textContent = user.full_name || user.username;
      });
      const holder = document.getElementById('topbar-avatar');
      if (holder) holder.replaceWith(avatar(user, 'avatar'));
      TaskForgeSidebar.setUser(user);
      loadNotifications();
      TaskForgeRealtime.connect('/notifications/', (event) => {
        if (event.type === 'notification_created') loadNotifications();
      });
      return user;
    } catch (error) {
      TaskForgeAPI.clearTokens();
      window.location.replace(TaskForgeConfig.loginPage);
      return null;
    }
  }

  window.TaskForgeUI = { el, avatar, initials, formatDate, toast, setLoading, modal, initShell, loadNotifications };
})();
