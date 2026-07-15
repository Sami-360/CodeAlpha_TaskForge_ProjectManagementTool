document.addEventListener('DOMContentLoaded', async () => {
  const shellUser = await TaskForgeUI.initShell('profile');
  if (!shellUser) return;
  const { el, avatar, formatDate, toast, setLoading } = TaskForgeUI;
  let user = shellUser;

  function render() {
    const summary = document.getElementById('profile-summary');
    summary.replaceChildren(
      avatar(user),
      el('h3', { text: user.full_name || user.username }),
      el('p', { text: `@${user.username}` }),
      el('p', { text: user.email }),
      el('p', { text: user.bio || 'No bio added.' }),
      el('p', { text: `Joined ${formatDate(user.date_joined)}` }),
    );
    document.getElementById('first_name').value = user.first_name || '';
    document.getElementById('last_name').value = user.last_name || '';
    document.getElementById('bio').value = user.bio || '';
  }

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
      render(); toast('Profile updated.');
    } catch (error) { toast(error.message, 'error'); }
    finally { setLoading(button, false); }
  });

  render();
});
