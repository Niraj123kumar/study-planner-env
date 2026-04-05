const dispatch = (detail) => window.dispatchEvent(new CustomEvent('appstate:change', { detail }));

const safeGet = (key, fallback) => {
  try { const v = localStorage.getItem(key); return v !== null ? JSON.parse(v) : fallback; }
  catch { return fallback; }
};
const safeSet = (key, val) => {
  try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
};

const MODES = ['focus', 'dyslexia', 'highContrast', 'reducedMotion', 'none'];
const MODE_CLASSES = { focus: 'focus-mode', dyslexia: 'dyslexia-mode', highContrast: 'high-contrast', reducedMotion: 'reduced-motion' };

window.appState = {
  accessibility: {
    mode: safeGet('a11y-mode', 'none'),
    theme: safeGet('theme', 'dark'),
    setMode(mode) {
      if (!MODES.includes(mode)) return;
      Object.values(MODE_CLASSES).forEach(c => document.documentElement.classList.remove(c));
      if (mode !== 'none') document.documentElement.classList.add(MODE_CLASSES[mode]);
      this.mode = mode;
      safeSet('a11y-mode', mode);
      dispatch({ type: 'accessibility', mode });
    },
    toggleTheme() {
      this.theme = this.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.classList.toggle('light', this.theme === 'light');
      safeSet('theme', this.theme);
      dispatch({ type: 'theme', theme: this.theme });
    },
    init() {
      const stored = safeGet('a11y-mode', null);
      if (!stored) {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) this.setMode('reducedMotion');
        else if (window.matchMedia('(prefers-contrast: more)').matches) this.setMode('highContrast');
      } else { this.setMode(stored); }
    }
  },
  recentCommands: {
    list: safeGet('recent-cmds', []),
    add(commandId, label) {
      this.list = [{ commandId, label, ts: Date.now() }, ...this.list.filter(c => c.commandId !== commandId)].slice(0, 5);
      safeSet('recent-cmds', this.list);
      dispatch({ type: 'recentCommands', list: this.list });
    },
    clear() { this.list = []; safeSet('recent-cmds', []); dispatch({ type: 'recentCommands', list: [] }); }
  },
  commandPalette: {
    isOpen: false,
    _prev: null,
    open() {
      this._prev = document.activeElement;
      this.isOpen = true;
      const bd = document.getElementById('palette-backdrop');
      if (bd) { bd.classList.add('open'); bd.removeAttribute('aria-hidden'); }
      setTimeout(() => { const inp = document.getElementById('palette-input'); if (inp) inp.focus(); }, 50);
      dispatch({ type: 'palette', isOpen: true });
    },
    close() {
      this.isOpen = false;
      const bd = document.getElementById('palette-backdrop');
      if (bd) { bd.classList.remove('open'); bd.setAttribute('aria-hidden', 'true'); }
      if (this._prev && this._prev.focus) this._prev.focus();
      dispatch({ type: 'palette', isOpen: false });
    }
  }
};

window.appState.accessibility.init();
