const STATE_COPY = {
  ready: { voice: '◉   BEREIT', top: 'BEREIT', chat: 'BEREIT' },
  listening: { voice: '◉   ICH HÖRE ZU …', top: 'HÖRT ZU', chat: 'SPRACHDEMO AKTIV' },
  working: { voice: '◉   ANTWORT WIRD GESUCHT …', top: 'DENKT NACH', chat: 'ANTWORT WIRD GESUCHT' },
  speaking: { voice: '◉   JARVIS SPRICHT …', top: 'ANTWORTET', chat: 'SPRACHAUSGABE' },
  error: { voice: '◉   FEHLER', top: 'FEHLER', chat: 'FEHLER ERKANNT' },
  offline: { voice: '◉   OFFLINE', top: 'OFFLINE', chat: 'KEINE VERBINDUNG' },
};

const ACTIVE_STATES = new Set(['listening', 'working', 'speaking']);

export function createJarvisVisualizer({ app, bars, voiceState, topStatus, chatStatus }) {
  let state = 'ready';
  let frame = null;
  let startedAt = performance.now();

  const shape = [0.45, 0.72, 0.92, 1, 0.9, 0.68, 0.42];

  function setVoiceLevel(level, now = performance.now()) {
    const safeLevel = Math.max(0, Math.min(1, level));
    bars.forEach((bar, index) => {
      const flutter = 0.82 + (Math.sin(now / 85 + index * 1.73) + 1) * 0.13;
      const height = 5 + safeLevel * 64 * shape[index] * flutter;
      bar.style.height = `${Math.max(5, height).toFixed(1)}px`;
      bar.style.opacity = `${0.42 + safeLevel * 0.58}`;
    });
  }

  function animate(now) {
    const elapsed = now - startedAt;
    let level = 0.08;
    if (state === 'listening') level = 0.55 + Math.abs(Math.sin(elapsed / 145)) * 0.45;
    if (state === 'working') level = 0.22 + Math.abs(Math.sin(elapsed / 330)) * 0.38;
    if (state === 'speaking') level = 0.82 + Math.abs(Math.sin(elapsed / 92) * Math.cos(elapsed / 231)) * 0.18;
    setVoiceLevel(level, now);
    frame = requestAnimationFrame(animate);
  }

  function ensureAnimation() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(animate);
  }

  function setState(nextState, hint) {
    if (!STATE_COPY[nextState]) nextState = 'ready';
    state = nextState;
    startedAt = performance.now();
    app.dataset.systemState = state;
    voiceState.textContent = STATE_COPY[state].voice;
    topStatus.textContent = STATE_COPY[state].top;
    chatStatus.textContent = STATE_COPY[state].chat;
    if (hint) document.querySelector('#voice-hint').textContent = hint;
    ensureAnimation();
  }

  function pulseState(nextState, duration, hint) {
    setState(nextState, hint);
    window.setTimeout(() => {
      if (state === nextState) setState('ready', 'Ring gedrückt halten · noch keine echte Aufnahme');
    }, duration);
  }

  setState('ready');

  return {
    get state() { return state; },
    setState,
    setVoiceLevel,
    pulseState,
    isActive() { return ACTIVE_STATES.has(state); },
  };
}
