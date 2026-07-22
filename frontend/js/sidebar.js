(function () {
  const STORAGE_KEY = 'taskforgeSidebarCollapsed';
  let sidebar;
  let overlay;
  let desktopToggle;
  let mobileToggle;

  function isMobile() {
    return window.matchMedia('(max-width: 760px)').matches;
  }

  function closeMobile() {
    sidebar?.classList.remove('open');
    overlay?.classList.remove('visible');
    mobileToggle?.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('sidebar-drawer-open');
  }

  function openMobile() {
    sidebar?.classList.add('open');
    overlay?.classList.add('visible');
    mobileToggle?.setAttribute('aria-expanded', 'true');
    document.body.classList.add('sidebar-drawer-open');
  }

  function applyDesktopState(collapsed) {
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    desktopToggle?.setAttribute('aria-expanded', String(!collapsed));
    desktopToggle?.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    desktopToggle?.setAttribute('title', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    if (desktopToggle) desktopToggle.textContent = collapsed ? '>' : '<';
  }

  function decorateNavigation() {
    const icons = { dashboard: 'space_dashboard', projects: 'folder_open', profile: 'person' };
    const navigation = sidebar.querySelector('.nav-list');
    if (navigation && !navigation.querySelector('.nav-section-label')) {
      navigation.prepend(Object.assign(document.createElement('span'), {
        className: 'nav-section-label',
        textContent: 'Workspace',
      }));
    }
    document.querySelectorAll('.nav-link[data-nav]').forEach((link) => {
      if (link.querySelector('.nav-icon')) return;
      const label = link.textContent.trim();
      link.replaceChildren(
        Object.assign(document.createElement('span'), {
          className: 'nav-icon material-symbols-outlined',
          textContent: icons[link.dataset.nav] || 'circle',
          ariaHidden: 'true',
        }),
        Object.assign(document.createElement('span'), { className: 'nav-label', textContent: label }),
      );
      link.title = label;
      link.addEventListener('click', () => { if (isMobile()) closeMobile(); });
    });
    if (navigation && !navigation.querySelector('.sidebar-quick-action')) {
      const action = document.createElement('a');
      action.className = 'sidebar-quick-action';
      action.href = 'projects.html?action=create';
      action.title = 'Create project';
      const actionIcon = document.createElement('span');
      actionIcon.className = 'nav-icon material-symbols-outlined';
      actionIcon.textContent = 'add';
      actionIcon.setAttribute('aria-hidden', 'true');
      const actionLabel = document.createElement('span');
      actionLabel.className = 'nav-label';
      actionLabel.textContent = 'New project';
      action.append(actionIcon, actionLabel);
      action.addEventListener('click', () => { if (isMobile()) closeMobile(); });
      navigation.append(action);
    }
  }

  function init() {
    sidebar = document.getElementById('sidebar');
    if (!sidebar || sidebar.dataset.enhanced === 'true') return;
    sidebar.dataset.enhanced = 'true';
    decorateNavigation();

    const brandName = sidebar.querySelector('.brand-name');
    if (brandName && !sidebar.querySelector('.brand-copy')) {
      const copy = document.createElement('span');
      copy.className = 'brand-copy';
      const title = document.createElement('strong');
      title.className = 'brand-name';
      title.textContent = brandName.textContent;
      const caption = document.createElement('small');
      caption.textContent = 'Project workspace';
      copy.append(title, caption);
      brandName.replaceWith(copy);
    }

    const logout = document.getElementById('logout-button');
    if (logout && !logout.querySelector('.material-symbols-outlined')) {
      const icon = document.createElement('span');
      icon.className = 'material-symbols-outlined';
      icon.textContent = 'logout';
      icon.setAttribute('aria-hidden', 'true');
      const label = document.createElement('span');
      label.className = 'nav-label';
      label.textContent = logout.textContent.trim();
      logout.replaceChildren(icon, label);
    }

    overlay = document.createElement('button');
    overlay.type = 'button';
    overlay.className = 'sidebar-overlay';
    overlay.setAttribute('aria-label', 'Close navigation');
    overlay.addEventListener('click', closeMobile);
    document.body.append(overlay);

    desktopToggle = document.createElement('button');
    desktopToggle.type = 'button';
    desktopToggle.className = 'sidebar-toggle';
    desktopToggle.setAttribute('aria-controls', 'sidebar');
    desktopToggle.addEventListener('click', () => {
      const collapsed = !document.body.classList.contains('sidebar-collapsed');
      localStorage.setItem(STORAGE_KEY, String(collapsed));
      applyDesktopState(collapsed);
    });
    sidebar.append(desktopToggle);

    mobileToggle = document.getElementById('mobile-menu');
    mobileToggle?.setAttribute('aria-controls', 'sidebar');
    mobileToggle?.setAttribute('aria-expanded', 'false');
    mobileToggle?.addEventListener('click', () => {
      if (sidebar.classList.contains('open')) closeMobile();
      else openMobile();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeMobile();
    });
    window.addEventListener('resize', () => { if (!isMobile()) closeMobile(); });
    applyDesktopState(localStorage.getItem(STORAGE_KEY) === 'true');
  }

  function setUser(user) {
    const foot = sidebar?.querySelector('.sidebar-foot');
    if (!foot) return;
    let summary = foot.querySelector('.sidebar-user');
    if (!summary) {
      summary = document.createElement('a');
      summary.className = 'sidebar-user';
      summary.href = 'profile.html';
      foot.prepend(summary);
    }
    const image = TaskForgeUI.avatar(user, 'avatar');
    const details = document.createElement('span');
    details.className = 'sidebar-user-details';
    const name = document.createElement('strong');
    name.textContent = user.full_name || user.username;
    const username = document.createElement('small');
    username.textContent = `@${user.username}`;
    details.append(name, username);
    summary.replaceChildren(image, details);
    summary.title = user.full_name || user.username;
  }

  window.TaskForgeSidebar = { init, setUser, closeMobile };
})();
