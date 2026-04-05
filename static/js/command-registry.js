const ENV_URL = window.ENV_URL || 'http://localhost:8000';

const COMMANDS = [
  { id: 'go_dashboard',  label: 'Go to Dashboard',   group: 'Navigation',    keywords: ['home','main','overview'], icon: '⌂', action: () => window.location.href = '/' },
  { id: 'go_docs',       label: 'Open API Docs',      group: 'Navigation',    keywords: ['swagger','docs','api'],   icon: '📖', action: () => window.open(ENV_URL + '/docs', '_blank') },
  { id: 'go_health',     label: 'Check Health',       group: 'Navigation',    keywords: ['status','ping','alive'],  icon: '♥', action: () => window.open(ENV_URL + '/health', '_blank') },
  { id: 'reset_easy',    label: 'Reset Task: Easy',   group: 'Actions',       keywords: ['easy','start','reset'],   icon: '▶', action: () => callReset('easy') },
  { id: 'reset_medium',  label: 'Reset Task: Medium', group: 'Actions',       keywords: ['medium','start','reset'], icon: '▶', action: () => callReset('medium') },
  { id: 'reset_hard',    label: 'Reset Task: Hard',   group: 'Actions',       keywords: ['hard','start','reset'],   icon: '▶', action: () => callReset('hard') },
  { id: 'get_grade',     label: 'Get Grade / Score',  group: 'Actions',       keywords: ['grade','score','result'], icon: '✦', action: () => callGrade() },
  { id: 'get_state',     label: 'Get Current State',  group: 'Actions',       keywords: ['state','status','step'],  icon: '≡', action: () => callState() },
  { id: 'toggle_theme',  label: 'Toggle Dark/Light',  group: 'Themes',        keywords: ['dark','light','theme'],   icon: '◑', action: () => window.appState.accessibility.toggleTheme() },
  { id: 'focus_mode',    label: 'Focus Mode',         group: 'Accessibility', keywords: ['focus','distraction'],    icon: '◎', action: () => window.appState.accessibility.setMode('focus') },
  { id: 'dyslexia_mode', label: 'Dyslexia Mode',      group: 'Accessibility', keywords: ['dyslexia','font','read'], icon: 'Aa', action: () => window.appState.accessibility.setMode('dyslexia') },
  { id: 'high_contrast', label: 'High Contrast',      group: 'Accessibility', keywords: ['contrast','vision','bold'],icon: '◐', action: () => window.appState.accessibility.setMode('highContrast') },
  { id: 'reduced_motion',label: 'Reduce Motion',      group: 'Accessibility', keywords: ['motion','animation','calm'],icon:'∼', action: () => window.appState.accessibility.setMode('reducedMotion') },
  { id: 'reset_a11y',   label: 'Reset Accessibility', group: 'Accessibility', keywords: ['reset','normal','default'],icon:'↺', action: () => window.appState.accessibility.setMode('none') },
];

async function callReset(taskId) {
  showToast(`Resetting task: ${taskId}…`);
  try {
    const r = await fetch(`${ENV_URL}/reset?task_id=${taskId}`, { method: 'POST' });
    const d = await r.json();
    showToast(`✓ Task "${taskId}" ready — budget: ${d.observation?.total_hours_left}h`, 'success');
    if (window.refreshDashboard) window.refreshDashboard();
  } catch(e) { showToast('Connection error', 'error'); }
}
async function callGrade() {
  showToast('Fetching score…');
  try {
    const r = await fetch(`${ENV_URL}/grade`);
    const d = await r.json();
    showToast(`Score: ${d.score ?? d.error}`, 'success');
  } catch(e) { showToast('Connection error', 'error'); }
}
async function callState() {
  try {
    const r = await fetch(`${ENV_URL}/state`);
    const d = await r.json();
    showToast(`Step ${d.step_count} | Task: ${d.task_id}`, 'success');
  } catch(e) { showToast('Connection error', 'error'); }
}

function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:9999;padding:10px 18px;border-radius:10px;font-family:var(--font-mono);font-size:13px;color:var(--text);background:var(--bg2);border:0.5px solid var(--border-strong);backdrop-filter:blur(12px);box-shadow:0 8px 32px rgba(0,0,0,0.4);transform:translateY(8px);opacity:0;transition:all 200ms ease;max-width:320px;`;
  t.textContent = msg;
  if (type === 'success') t.style.borderColor = 'rgba(52,211,153,0.4)';
  if (type === 'error')   t.style.borderColor = 'rgba(248,113,113,0.4)';
  document.body.appendChild(t);
  requestAnimationFrame(() => { t.style.transform = 'translateY(0)'; t.style.opacity = '1'; });
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateY(8px)'; setTimeout(() => t.remove(), 200); }, 3000);
}

function fuzzyMatch(str, query) {
  const s = str.toLowerCase(), q = query.toLowerCase();
  if (s.includes(q)) return 1;
  let score = 0, qi = 0;
  for (let i = 0; i < s.length && qi < q.length; i++) {
    if (s[i] === q[qi]) { score += 1 - (i * 0.01); qi++; }
  }
  return qi === q.length ? score / q.length : 0;
}

window.CommandRegistry = {
  getAll: () => COMMANDS,
  search(query) {
    if (!query.trim()) return COMMANDS;
    return COMMANDS.map(c => {
      const s1 = fuzzyMatch(c.label, query);
      const s2 = Math.max(...c.keywords.map(k => fuzzyMatch(k, query)));
      return { ...c, _score: Math.max(s1, s2 * 0.8) };
    }).filter(c => c._score > 0.2).sort((a, b) => b._score - a._score);
  },
  execute(id) {
    const cmd = COMMANDS.find(c => c.id === id);
    if (cmd) { cmd.action(); window.appState.recentCommands.add(id, cmd.label); }
  }
};

window.showToast = showToast;
