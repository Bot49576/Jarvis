const STATE_COPY = {
  ready: { voice: '◉  BEREIT', top: 'BEREIT' },
  listening: { voice: '◉  ICH HÖRE ZU …', top: 'HÖRT ZU' },
  working: { voice: '◉  ICH PRÜFE DAS …', top: 'PRÜFT' },
  speaking: { voice: '◉  JARVIS ANTWORTET …', top: 'ANTWORTET' },
  error: { voice: '◉  FEHLER', top: 'FEHLER' },
  offline: { voice: '◉  JARVIS IST OFFLINE', top: 'OFFLINE' },
};

const SHAPE = [0.34, 0.58, 0.82, 0.96, 1, 0.96, 0.82, 0.58, 0.34];

export function createJarvisVisualizer({ app, bars, voiceState, topStatus }) {
  let state = 'ready';
  let frame = null;
  let startedAt = performance.now();
  let inputLevel = 0;
  let inputUpdatedAt = 0;

  function setVoiceLevel(level) {
    inputLevel = Math.max(0, Math.min(1, Number(level) || 0));
    inputUpdatedAt = performance.now();
  }

  function paintBars(level, now) {
    bars.forEach((bar, index) => {
      const flutter = 0.76 + (Math.sin(now / 78 + index * 1.61) + 1) * 0.16;
      const height = 5 + level * 62 * SHAPE[index] * flutter;
      bar.style.height = `${Math.max(5, height).toFixed(1)}px`;
      bar.style.opacity = `${(0.42 + level * 0.58).toFixed(2)}`;
    });
  }

  function animate(now) {
    const elapsed = now - startedAt;
    let level = 0.07 + Math.abs(Math.sin(elapsed / 720)) * 0.05;
    if (state === 'listening') {
      level = now - inputUpdatedAt < 180 ? Math.max(0.08, inputLevel) : 0.12;
    } else if (state === 'working') {
      level = 0.18 + Math.abs(Math.sin(elapsed / 310)) * 0.26;
    } else if (state === 'speaking') {
      level = now - inputUpdatedAt < 180 ? Math.max(0.16, inputLevel) : 0.5 + Math.abs(Math.sin(elapsed / 105)) * 0.38;
    } else if (state === 'error' || state === 'offline') {
      level = 0.04;
    }
    paintBars(level, now);
    frame = requestAnimationFrame(animate);
  }

  function setState(nextState, customVoiceText = '') {
    state = STATE_COPY[nextState] ? nextState : 'ready';
    startedAt = performance.now();
    app.dataset.state = state;
    voiceState.querySelector('strong').textContent = customVoiceText || STATE_COPY[state].voice;
    topStatus.textContent = STATE_COPY[state].top;
  }

  function stop() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
  }

  setState('ready');
  frame = requestAnimationFrame(animate);

  return {
    get state() { return state; },
    setState,
    setVoiceLevel,
    stop,
  };
}
