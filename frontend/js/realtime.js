(function () {
  function connect(path, onEvent) {
    let socket;
    let retryTimer;
    let stopped = false;
    let refreshAttempted = false;

    function open() {
      if (stopped) return;
      socket = new WebSocket(`${TaskForgeConfig.wsBase}${path}`);
      socket.addEventListener('message', async (event) => {
        let payload;
        try {
          payload = JSON.parse(event.data);
        } catch (error) {
          return;
        }
        if (payload.type === 'authentication_required') {
          socket.send(JSON.stringify({
            type: 'authenticate',
            token: TaskForgeAPI.getAccessToken(),
          }));
          return;
        }
        if (payload.type === 'authentication_error' && !refreshAttempted) {
          refreshAttempted = true;
          if (await TaskForgeAPI.refreshAccessToken()) {
            socket.close();
          }
          return;
        }
        if (payload.type === 'authenticated') {
          refreshAttempted = false;
          return;
        }
        onEvent(payload);
      });
      socket.addEventListener('close', (event) => {
        if (stopped || event.code === 4403) return;
        clearTimeout(retryTimer);
        retryTimer = setTimeout(open, 2500);
      });
    }

    open();
    return {
      close() {
        stopped = true;
        clearTimeout(retryTimer);
        socket?.close();
      },
    };
  }

  window.TaskForgeRealtime = { connect };
})();
