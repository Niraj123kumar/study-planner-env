let activeIndex = -1;
let currentResults = [];
let debounceTimer = null;

function injectPalette() {
  const html = `
<div id="palette-backdrop" aria-hidden="true" role="dialog" aria-modal="true" aria-label="Command palette">
  <div id="palette-modal" tabindex="-1">
    <div id="palette-search-wrap">
      <svg id="palette-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <input id="palette-input" type="text" placeholder="Search commands or type naturally…" autocomplete="off" spellcheck="false" aria-label="Search commands" />
      <span id="palette-kbd">ESC</span>
    </div>
    <div id="palette-results" role="listbox" aria-label="Commands"></div>
    <div id="palette-status" aria-live="polite" aria-atomic="true"></div>
    <div id="palette-footer">
      <span class="palette-hint"><kbd>↑↓</kbd> navigate</span>
      <span class="palette-hint"><kbd>↵</kbd> execute</span>
      <span class="palette-hint"><kbd>ESC</kbd> close</span>
    </div>
  </div>
</div>`;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('palette-backdrop').addEventListener('click', e => {
    if (e.target.id === 'palette-backdrop') window.appState.commandPalette.close();
  });
  document.getElementById('palette-input').addEventListener('input', e => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => renderResults(e.target.value), 150);
  });
  document.getElementById('palette-input').addEventListener('keydown', handleKeydown);
  document.getElementById('palette-modal').addEventListener('keydown', trapFocus);
}

function trapFocus(e) {
  if (e.key === 'Escape') { window.appState.commandPalette.close(); return; }
  if (e.key !== 'Tab') return;
  const focusable = document.getElementById('palette-modal').querySelectorAll('input,[tabindex]:not([tabindex="-1"])');
  const arr = Array.from(focusable);
  const idx = arr.indexOf(document.activeElement);
  if (e.shiftKey) { arr[idx <= 0 ? arr.length - 1 : idx - 1].focus(); }
  else { arr[idx >= arr.length - 1 ? 0 : idx + 1].focus(); }
  e.preventDefault();
}

function handleKeydown(e) {
  const items = document.querySelectorAll('.palette-item');
  if (e.key === 'ArrowDown') { e.preventDefault(); activeIndex = Math.min(activeIndex + 1, items.length - 1); updateActive(items); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); activeIndex = Math.max(activeIndex - 1, 0); updateActive(items); }
  else if (e.key === 'Enter') { e.preventDefault(); if (activeIndex >= 0 && currentResults[activeIndex]) executeItem(currentResults[activeIndex]); }
  else if (e.key === 'Escape') { window.appState.commandPalette.close(); }
}

function updateActive(items) {
  items.forEach((el, i) => el.classList.toggle('active', i === activeIndex));
  if (items[activeIndex]) items[activeIndex].scrollIntoView({ block: 'nearest' });
}

function executeItem(item) {
  window.CommandRegistry.execute(item.id);
  window.appState.commandPalette.close();
  document.getElementById('palette-input').value = '';
  renderResults('');
}

function renderResults(query) {
  const container = document.getElementById('palette-results');
  const status    = document.getElementById('palette-status');
  activeIndex = -1;
  currentResults = [];

  let magicResult = null;
  if (query.length > 2) {
    const parsed = window.parseCommand(query);
    if (parsed && parsed.confidence > 0.7) magicResult = { id: parsed.commandId, label: `✦ ${parsed.payload?.commandId || query}`, _magic: true };
  }

  const recent  = window.appState.recentCommands.list;
  const matched = query.trim() ? window.CommandRegistry.search(query) : window.CommandRegistry.getAll();

  const groups = {};
  if (magicResult) { groups['Magic'] = [magicResult]; currentResults.push(magicResult); }
  if (!query.trim() && recent.length) {
    groups['Recent'] = recent.map(r => ({ id: r.commandId, label: r.label, _recent: true }));
    groups['Recent'].forEach(c => currentResults.push(c));
  }
  matched.forEach(c => {
    if (!groups[c.group]) groups[c.group] = [];
    if (!currentResults.find(r => r.id === c.id)) { groups[c.group].push(c); currentResults.push(c); }
  });

  let html = '';
  let globalIdx = 0;
  for (const [group, cmds] of Object.entries(groups)) {
    if (!cmds.length) continue;
    html += `<div class="palette-group-label">${group}</div>`;
    cmds.forEach(cmd => {
      const icon = cmd.icon || (cmd._magic ? '✦' : cmd._recent ? '↺' : '⊹');
      const cls  = cmd._magic ? 'palette-item magic' : 'palette-item';
      html += `<div class="${cls} stagger-item" role="option" data-id="${cmd.id}" data-idx="${globalIdx}" style="animation-delay:${globalIdx * 30}ms">
        <div class="palette-icon">${icon}</div>
        <span class="palette-label">${cmd.label}</span>
        ${!cmd._magic && !cmd._recent ? `<span class="palette-group-badge">${cmd.group}</span>` : ''}
      </div>`;
      globalIdx++;
    });
  }
  if (!html) html = '<div style="padding:24px;text-align:center;color:var(--text-dim);font-size:13px;">No commands found</div>';
  container.innerHTML = html;
  status.textContent = `${currentResults.length} command${currentResults.length !== 1 ? 's' : ''} found`;

  container.querySelectorAll('.palette-item').forEach(el => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.dataset.idx);
      if (currentResults[idx]) executeItem(currentResults[idx]);
    });
    el.addEventListener('mouseenter', () => {
      activeIndex = parseInt(el.dataset.idx);
      updateActive(container.querySelectorAll('.palette-item'));
    });
  });
}

document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    window.appState.commandPalette.isOpen ? window.appState.commandPalette.close() : window.appState.commandPalette.open();
  }
});

document.addEventListener('DOMContentLoaded', () => {
  injectPalette();
  renderResults('');
});
