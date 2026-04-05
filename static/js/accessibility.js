window.addEventListener('appstate:change', e => {
  const { type, mode, theme } = e.detail || {};
  if (type === 'accessibility') {
    const badge = document.getElementById('a11y-badge');
    if (badge) badge.textContent = mode === 'none' ? 'default' : mode;
  }
  if (type === 'theme') {
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = theme === 'dark' ? '◑ Light' : '◑ Dark';
  }
});
