(function () {
  const COLLAPSE_KEY = 'taskforgeWorkspaceSidebarCollapsed';
  let sidebar;
  let overlay;
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

  function toggleCollapsed() {
    const collapsed = !document.body.classList.contains('sidebar-collapsed');
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    localStorage.setItem(COLLAPSE_KEY, String(collapsed));
    const control = document.getElementById('sidebar-collapse');
    control?.setAttribute('aria-expanded', String(!collapsed));
    control?.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    control?.setAttribute('title', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    const controlIcon = control?.querySelector('.material-symbols-outlined');
    if (controlIcon) controlIcon.textContent = collapsed ? 'menu' : 'menu_open';
  }

  function link(href, label, icon, nav) {
    const item = document.createElement('a');
    item.className = 'nav-link';
    item.href = href;
    item.title = label;
    if (nav) item.dataset.nav = nav;
    const glyph = document.createElement('span');
    glyph.className = 'nav-icon material-symbols-outlined';
    glyph.textContent = icon;
    glyph.setAttribute('aria-hidden', 'true');
    const text = document.createElement('span');
    text.className = 'nav-label';
    text.textContent = label;
    item.append(glyph, text);
    item.addEventListener('click', closeMobile);
    return item;
  }

  function buildNavigation() {
    const navigation = sidebar.querySelector('.nav-list');
    navigation.replaceChildren();
    const label = document.createElement('span');
    label.className = 'nav-section-label';
    label.textContent = 'Workspace';
    const inbox = link('dashboard.html?notifications=open', 'Inbox', 'notifications', 'inbox');
    inbox.classList.add('sidebar-inbox-link');
    inbox.setAttribute('aria-controls', 'notification-panel');
    inbox.setAttribute('aria-expanded', 'false');
    inbox.addEventListener('click', (event) => {
      const notificationButton = document.getElementById('notification-button');
      if (!notificationButton) return;
      event.preventDefault();
      closeMobile();
      notificationButton.click();
    });
    const badge = document.createElement('span');
    badge.id = 'sidebar-unread-count';
    badge.className = 'nav-badge hidden';
    inbox.append(badge);
    navigation.append(
      label,
      link('dashboard.html', 'Dashboard', 'space_dashboard', 'dashboard'),
      link('dashboard.html#recent-tasks', 'My Tasks', 'check_circle', 'tasks'),
      link('projects.html', 'Projects', 'folder_open', 'projects'),
      inbox,
      link('profile.html', 'Profile', 'person', 'profile'),
    );

    const action = link('projects.html?action=create', 'New project', 'add');
    action.className = 'sidebar-quick-action';
    navigation.append(action);

    const projectsLabel = document.createElement('span');
    projectsLabel.className = 'nav-section-label sidebar-projects-label';
    projectsLabel.textContent = 'Recent projects';
    const projects = document.createElement('div');
    projects.id = 'sidebar-projects';
    projects.className = 'sidebar-project-list';
    projects.append(status('Loading projects...'));
    navigation.append(projectsLabel, projects);

    const teamLabel = document.createElement('span');
    teamLabel.className = 'nav-section-label sidebar-team-label';
    teamLabel.textContent = 'Project team';
    const team = document.createElement('div');
    team.id = 'sidebar-team';
    team.className = 'sidebar-team-list';
    team.append(status('Open a project to view its team.'));
    navigation.append(teamLabel, team);
  }

  function status(message) {
    const node = document.createElement('span');
    node.className = 'sidebar-status';
    node.textContent = message;
    return node;
  }

  async function loadProjects() {
    const holder = document.getElementById('sidebar-projects');
    if (!holder) return;
    try {
      const projects = await TaskForgeAPI.request('/projects/?sort=updated');
      holder.replaceChildren();
      projects.slice(0, 5).forEach((project) => {
        const item = link(`project-board.html?id=${project.id}`, project.name, 'folder');
        item.classList.add('sidebar-project-link');
        holder.append(item);
      });
      if (!projects.length) holder.append(status('No projects yet.'));
    } catch (error) {
      holder.replaceChildren(status('Projects unavailable.'));
    }
  }

  function init() {
    sidebar = document.getElementById('sidebar');
    if (!sidebar || sidebar.dataset.enhanced === 'true') return;
    sidebar.dataset.enhanced = 'true';
    if (localStorage.getItem(COLLAPSE_KEY) === 'true') document.body.classList.add('sidebar-collapsed');
    buildNavigation();

    const brand = sidebar.querySelector('.brand');
    if (brand) {
      let copy = brand.querySelector(':scope > .brand-copy');
      if (!copy) {
        copy = document.createElement('span');
        copy.className = 'brand-copy';
        brand.querySelector('.brand-name')?.replaceWith(copy);
      }
      copy.replaceChildren(
        Object.assign(document.createElement('strong'), { className: 'brand-name', textContent: 'TaskForge' }),
        Object.assign(document.createElement('small'), { textContent: 'Project workspace' }),
      );
      if (sidebar.querySelector('#sidebar-collapse')) return;
      const collapse = document.createElement('button');
      collapse.id = 'sidebar-collapse';
      collapse.className = 'sidebar-collapse';
      collapse.type = 'button';
      const collapsed = document.body.classList.contains('sidebar-collapsed');
      collapse.append(Object.assign(document.createElement('span'), {
        className: 'material-symbols-outlined',
        textContent: collapsed ? 'menu' : 'menu_open',
      }));
      collapse.title = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
      collapse.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
      collapse.setAttribute('aria-expanded', String(!collapsed));
      collapse.addEventListener('click', (event) => { event.preventDefault(); toggleCollapsed(); });
      brand.insertAdjacentElement('afterend', collapse);
    }

    const logout = document.getElementById('logout-button');
    if (logout) {
      const logoutIcon = Object.assign(document.createElement('span'), {
        className: 'material-symbols-outlined',
        textContent: 'logout',
      });
      logoutIcon.setAttribute('aria-hidden', 'true');
      logout.replaceChildren(logoutIcon, Object.assign(document.createElement('span'), { className: 'nav-label', textContent: 'Sign out' }));
    }
    overlay = document.createElement('button');
    overlay.type = 'button';
    overlay.className = 'sidebar-overlay';
    overlay.setAttribute('aria-label', 'Close navigation');
    overlay.addEventListener('click', closeMobile);
    document.body.append(overlay);

    mobileToggle = document.getElementById('mobile-menu');
    mobileToggle?.setAttribute('aria-controls', 'sidebar');
    mobileToggle?.setAttribute('aria-expanded', 'false');
    mobileToggle?.addEventListener('click', () => sidebar.classList.contains('open') ? closeMobile() : openMobile());
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeMobile(); });
    window.addEventListener('resize', () => { if (!isMobile()) closeMobile(); });
    loadProjects();
  }

  function openMobile() {
    sidebar?.classList.add('open');
    overlay?.classList.add('visible');
    mobileToggle?.setAttribute('aria-expanded', 'true');
    document.body.classList.add('sidebar-drawer-open');
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
    const details = document.createElement('span');
    details.className = 'sidebar-user-details';
    details.append(Object.assign(document.createElement('strong'), { textContent: user.full_name || user.username }));
    details.append(Object.assign(document.createElement('small'), { textContent: `@${user.username}` }));
    summary.replaceChildren(TaskForgeUI.avatar(user, 'avatar'), details);
    summary.title = user.full_name || user.username;
  }

  function setUnread(count) {
    const badge = document.getElementById('sidebar-unread-count');
    if (!badge) return;
    badge.textContent = count > 99 ? '99+' : String(count);
    badge.classList.toggle('hidden', !count);
  }

  function setInboxOpen(isOpen) {
    const inbox = sidebar?.querySelector('[data-nav="inbox"]');
    if (!inbox) return;
    sidebar.querySelectorAll('.nav-link[data-nav]').forEach((item) => {
      const shouldBeActive = item === inbox ? isOpen : !isOpen && item.getAttribute('aria-current') === 'page';
      item.classList.toggle('active', shouldBeActive);
    });
    inbox.setAttribute('aria-expanded', String(isOpen));
  }

  function setContext(context) {
    const holder = document.getElementById('sidebar-team');
    if (!holder) return;
    holder.replaceChildren();
    const members = context?.members || [];
    members.slice(0, 6).forEach((membership) => {
      const row = document.createElement('div');
      row.className = 'sidebar-team-member';
      const copy = document.createElement('span');
      copy.className = 'sidebar-user-details';
      copy.append(Object.assign(document.createElement('strong'), { textContent: membership.user.full_name || membership.user.username }));
      copy.append(Object.assign(document.createElement('small'), { textContent: membership.role }));
      row.append(TaskForgeUI.avatar(membership.user, 'avatar avatar-small'), copy);
      row.title = `${membership.user.full_name || membership.user.username} - ${membership.role}`;
      holder.append(row);
    });
    if (!members.length) holder.append(status('No project members to show.'));
  }

  window.TaskForgeSidebar = { init, setUser, setUnread, setInboxOpen, setContext, closeMobile, loadProjects };
})();
