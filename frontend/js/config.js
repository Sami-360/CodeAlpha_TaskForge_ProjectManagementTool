const localFrontend = ['127.0.0.1', 'localhost'].includes(window.location.hostname)
  && window.location.port === '5500';
const backendOrigin = window.location.protocol === 'file:'
  ? 'http://127.0.0.1:8000'
  : localFrontend
    ? `http://${window.location.hostname}:8000`
    : window.location.origin;
const backendUrl = new URL(backendOrigin);
const websocketProtocol = backendUrl.protocol === 'https:' ? 'wss:' : 'ws:';

window.TaskForgeConfig = Object.freeze({
  apiBase: `${backendOrigin}/api`,
  wsBase: `${websocketProtocol}//${backendUrl.host}/ws`,
  loginPage: 'login.html',
  dashboardPage: 'dashboard.html',
});
