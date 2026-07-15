document.addEventListener('DOMContentLoaded', () => {
  if (TaskForgeAPI.getRefreshToken()) {
    window.location.replace(TaskForgeConfig.dashboardPage);
    return;
  }

  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const form = loginForm || registerForm;
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    const errorNode = document.getElementById('form-error');
    errorNode.textContent = '';
    const data = Object.fromEntries(new FormData(form).entries());
    if (registerForm && data.password !== data.password_confirm) {
      errorNode.textContent = 'Password confirmation does not match.';
      return;
    }
    TaskForgeUI.setLoading(button, true, loginForm ? 'Signing in...' : 'Creating account...');
    try {
      const endpoint = loginForm ? '/auth/login/' : '/auth/register/';
      const response = await TaskForgeAPI.request(endpoint, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      TaskForgeAPI.setTokens(response.access, response.refresh);
      window.location.replace(TaskForgeConfig.dashboardPage);
    } catch (error) {
      errorNode.textContent = error.message;
    } finally {
      TaskForgeUI.setLoading(button, false);
    }
  });
});
