(function () {
  const ACCESS_KEY = 'taskforge_access';
  const REFRESH_KEY = 'taskforge_refresh';

  function getAccessToken() { return localStorage.getItem(ACCESS_KEY); }
  function getRefreshToken() { return localStorage.getItem(REFRESH_KEY); }
  function setTokens(access, refresh) {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  }
  function clearTokens() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }

  async function parseResponse(response) {
    if (response.status === 204) return null;
    const contentType = response.headers.get('content-type') || '';
    return contentType.includes('application/json') ? response.json() : response.text();
  }

  function errorMessage(data, fallback) {
    if (!data) return fallback;
    if (typeof data === 'string') return data;
    if (data.detail) return data.detail;
    const firstKey = Object.keys(data)[0];
    if (!firstKey) return fallback;
    const value = data[firstKey];
    const text = Array.isArray(value) ? value[0] : value;
    return `${firstKey.replaceAll('_', ' ')}: ${text}`;
  }

  async function refreshAccessToken() {
    const refresh = getRefreshToken();
    if (!refresh) return false;
    const response = await fetch(`${TaskForgeConfig.apiBase}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!response.ok) {
      clearTokens();
      return false;
    }
    const data = await response.json();
    setTokens(data.access, data.refresh);
    return true;
  }

  async function request(path, options = {}, retry = true) {
    const headers = new Headers(options.headers || {});
    const token = getAccessToken();
    const isFormData = options.body instanceof FormData;
    if (token) headers.set('Authorization', `Bearer ${token}`);
    if (options.body && !isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    const response = await fetch(`${TaskForgeConfig.apiBase}${path}`, { ...options, headers });
    if (response.status === 401 && retry && getRefreshToken()) {
      const refreshed = await refreshAccessToken();
      if (refreshed) return request(path, options, false);
    }
    const data = await parseResponse(response);
    if (!response.ok) {
      const error = new Error(errorMessage(data, `Request failed with ${response.status}`));
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  async function download(path, filename, retry = true) {
    const token = getAccessToken();
    const response = await fetch(`${TaskForgeConfig.apiBase}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (response.status === 401 && retry && await refreshAccessToken()) {
      return download(path, filename, false);
    }
    if (!response.ok) throw new Error(`Download failed with ${response.status}`);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  window.TaskForgeAPI = {
    request,
    setTokens,
    clearTokens,
    getAccessToken,
    getRefreshToken,
    refreshAccessToken,
    download,
  };
})();
