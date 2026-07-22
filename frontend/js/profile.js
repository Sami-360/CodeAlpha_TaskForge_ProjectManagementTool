document.addEventListener('DOMContentLoaded', async () => {
  const shellUser = await TaskForgeUI.initShell('profile');
  if (!shellUser) return;
  const { el, avatar, formatDate, toast, setLoading } = TaskForgeUI;
  let user = shellUser;
  let previewUrl;

  function stat(label, value) {
    return el('div', { className: 'profile-stat' }, [
      el('strong', { text: String(value) }),
      el('span', { text: label }),
    ]);
  }

  function renderAvatarPreview(file) {
    const preview = document.getElementById('avatar-preview');
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (file) {
      previewUrl = URL.createObjectURL(file);
      preview.replaceChildren(el('img', { className: 'profile-avatar', src: previewUrl, alt: 'Selected avatar preview' }));
    } else {
      preview.replaceChildren(avatar(user, 'profile-avatar'));
    }
  }

  function render() {
    const summary = document.getElementById('profile-summary');
    summary.replaceChildren(
      avatar(user, 'profile-avatar'),
      el('h3', { text: user.full_name || user.username }),
      el('p', { text: `@${user.username}` }),
      el('p', { text: user.email }),
      el('p', { text: user.bio || 'No bio added.' }),
      el('p', { text: `Joined ${formatDate(user.date_joined)}` }),
      el('div', { className: 'profile-stats' }, [
        stat('Owned projects', user.projects_owned_count),
        stat('Joined projects', user.projects_joined_count),
        stat('Assigned tasks', user.tasks_assigned_count),
        stat('Completed', user.completed_tasks_count),
        stat('Pending', user.pending_tasks_count),
      ]),
    );
    document.getElementById('first_name').value = user.first_name || '';
    document.getElementById('last_name').value = user.last_name || '';
    document.getElementById('bio').value = user.bio || '';
    document.getElementById('bio-count').textContent = String((user.bio || '').length);
    document.getElementById('remove-avatar').classList.toggle('hidden', !user.avatar);
    renderAvatarPreview();
  }

  const avatarInput = document.getElementById('avatar');
  avatarInput.addEventListener('change', () => {
    const file = avatarInput.files[0];
    const error = document.getElementById('profile-error');
    error.textContent = '';
    if (!file) { renderAvatarPreview(); return; }
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      error.textContent = 'Choose a JPG, PNG, or WebP image up to 5 MB.';
      avatarInput.value = '';
      renderAvatarPreview();
      return;
    }
    renderAvatarPreview(file);
  });

  document.getElementById('bio').addEventListener('input', (event) => {
    document.getElementById('bio-count').textContent = String(event.target.value.length);
  });

  document.getElementById('remove-avatar').addEventListener('click', async (event) => {
    if (!confirm('Remove your current avatar?')) return;
    setLoading(event.currentTarget, true, 'Removing...');
    try {
      user = await TaskForgeAPI.request('/auth/me/avatar/', { method: 'DELETE' });
      avatarInput.value = '';
      render();
      toast('Avatar removed.');
    } catch (error) { toast(error.message, 'error'); }
    finally { setLoading(event.currentTarget, false); }
  });

  document.getElementById('profile-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('button[type="submit"]');
    const formData = new FormData();
    formData.set('first_name', document.getElementById('first_name').value);
    formData.set('last_name', document.getElementById('last_name').value);
    formData.set('bio', document.getElementById('bio').value);
    const image = document.getElementById('avatar').files[0];
    if (image) formData.set('avatar', image);
    setLoading(button, true, 'Saving...');
    try {
      user = await TaskForgeAPI.request('/auth/me/', { method: 'PATCH', body: formData });
      avatarInput.value = '';
      render(); toast('Profile updated.');
    } catch (error) { toast(error.message, 'error'); }
    finally { setLoading(button, false); }
  });

  render();
  window.addEventListener('beforeunload', () => { if (previewUrl) URL.revokeObjectURL(previewUrl); });
});
