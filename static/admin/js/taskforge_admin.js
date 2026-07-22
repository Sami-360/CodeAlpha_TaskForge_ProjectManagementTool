(function () {
  const filter = document.getElementById('nav-filter');
  const groups = Array.from(document.querySelectorAll('.admin-nav-group'));
  if (!filter || !groups.length) return;

  const applyFilter = () => {
    const query = filter.value.trim().toLowerCase();
    let hasMatch = false;

    groups.forEach((group) => {
      let groupHasMatch = false;
      group.querySelectorAll('.admin-model-link').forEach((row) => {
        const matches = !query || row.textContent.toLowerCase().includes(query);
        row.hidden = !matches;
        groupHasMatch ||= matches;
      });
      group.hidden = !groupHasMatch;
      hasMatch ||= groupHasMatch;
    });

    filter.classList.toggle('no-results', Boolean(query) && !hasMatch);
    sessionStorage.setItem('taskforgeAdminFilter', query);
  };

  filter.addEventListener('input', applyFilter);
  filter.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    filter.value = '';
    applyFilter();
  });

  filter.value = sessionStorage.getItem('taskforgeAdminFilter') || '';
  applyFilter();
})();
