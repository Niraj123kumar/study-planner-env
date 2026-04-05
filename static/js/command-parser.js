const PATTERNS = [
  { re: /show\s+(math|physics|chemistry|biology|history)\s+scores?/i, intent: 'navigate', confidence: 1.0,
    extract: m => ({ subject: m[1], commandId: 'go_docs' }) },
  { re: /\b(dark|light)\s+mode\b/i, intent: 'theme', confidence: 1.0,
    extract: m => ({ theme: m[1].toLowerCase(), commandId: 'toggle_theme' }) },
  { re: /focus\s+mode\s*(on|off)?/i, intent: 'accessibility', confidence: 1.0,
    extract: m => ({ mode: 'focus', enabled: m[1] !== 'off', commandId: 'focus_mode' }) },
  { re: /dyslexia\s+mode/i, intent: 'accessibility', confidence: 1.0,
    extract: () => ({ mode: 'dyslexia', commandId: 'dyslexia_mode' }) },
  { re: /high\s*contrast/i, intent: 'accessibility', confidence: 1.0,
    extract: () => ({ mode: 'highContrast', commandId: 'high_contrast' }) },
  { re: /reduce\s+motion/i, intent: 'accessibility', confidence: 1.0,
    extract: () => ({ mode: 'reducedMotion', commandId: 'reduced_motion' }) },
  { re: /reset\s+(easy|medium|hard)/i, intent: 'action', confidence: 1.0,
    extract: m => ({ task: m[1], commandId: `reset_${m[1]}` }) },
  { re: /\b(grade|score|result)\b/i, intent: 'action', confidence: 0.9,
    extract: () => ({ commandId: 'get_grade' }) },
  { re: /\b(health|status|alive|ping)\b/i, intent: 'action', confidence: 0.8,
    extract: () => ({ commandId: 'go_health' }) },
  { re: /\b(docs?|api|swagger)\b/i, intent: 'navigate', confidence: 0.8,
    extract: () => ({ commandId: 'go_docs' }) },
];

function wordVariance(input, pattern) {
  const words = pattern.source.replace(/[\\()?.*+]/g, ' ').split(/\s+/).filter(Boolean);
  const found = words.filter(w => input.toLowerCase().includes(w.toLowerCase()));
  return found.length / Math.max(words.length, 1);
}

function parseCommand(input) {
  if (!input || input.trim().length < 2) return null;
  const results = [];
  for (const p of PATTERNS) {
    const m = input.match(p.re);
    if (m) {
      const payload = p.extract(m);
      results.push({ intent: p.intent, confidence: p.confidence, payload, commandId: payload.commandId });
    } else {
      const variance = wordVariance(input, p.re);
      if (variance > 0.5) {
        const payload = p.extract(['', '']);
        results.push({ intent: p.intent, confidence: p.confidence * variance * 0.8, payload, commandId: payload.commandId });
      }
    }
  }
  if (!results.length) return null;
  results.sort((a, b) => b.confidence - a.confidence);
  const best = results[0];
  const chain = results.length > 1 && input.includes(' and ') ? results.slice(1, 3) : undefined;
  return { ...best, chain };
}

window.parseCommand = parseCommand;
