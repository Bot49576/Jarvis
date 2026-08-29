import { dashboardConfig } from './dashboard.config.js';
import { DashboardClient, isLocalPreview } from './api-client.js';
import { createJarvisVisualizer } from './visualizer.js';

const app = document.querySelector('#app');
const voiceCore = document.querySelector('#voice-core');
const voiceState = document.querySelector('#voice-state');
const voiceHint = document.querySelector('#voice-hint');
const topStatus = document.querySelector('#top-status');
const chatStatus = document.querySelector('#chat-status');
const clock = document.querySelector('#clock');
const dashboard = document.querySelector('#dashboard');
const dashboardButton = document.querySelector('#mobile-dashboard-button');
const messages = document.querySelector('#messages');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');
const sessions = document.querySelector('#sessions');
const fileInput = document.querySelector('#file-input');
const fileState = document.querySelector('#file-state');
const installButton = document.querySelector('#install-button');
let installPrompt = null;
const dashboardClient = new DashboardClient();
const localPreview = isLocalPreview();
const visualizer = createJarvisVisualizer({
  app,
  bars: [...document.querySelectorAll('.wave i')],
  voiceState,
  topStatus,
  chatStatus,
});

function applyTheme(theme) {
  const root = document.documentElement.style;
  root.setProperty('--accent', theme.accent);
  root.setProperty('--panel-radius', theme.panelRadius);
  root.setProperty('--panel-gap', theme.panelGap);
  root.setProperty('--rail-left', theme.leftRail);
  root.setProperty('--rail-right', theme.rightRail);
}

function renderLeftModules(modules) {
  const zone = document.querySelector('#left-modules');
  zone.replaceChildren(...modules.filter((module) => module.enabled).map((module) => {
    const panel = document.createElement('section');
    panel.className = `panel compact-panel${module.desktopOnly ? ' desktop-only' : ''}`;
    panel.dataset.moduleId = module.id;
    const head = document.createElement('div');
    head.className = 'panel-head';
    head.innerHTML = `<span>${module.title}</span><b>${module.badge}</b>`;
    panel.append(head);
    if (module.type === 'metrics') {
      module.items.forEach(([label, value]) => {
        const metric = document.createElement('div');
        metric.className = 'metric';
        metric.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
        panel.append(metric);
      });
    } else {
      const note = document.createElement('p');
      note.className = 'module-note';
      note.textContent = module.text;
      panel.append(note);
    }
    return panel;
  }));
}

function renderQuickActions(actions) {
  const zone = document.querySelector('#quick-actions');
  const enabled = actions.filter((action) => action.enabled);
  document.querySelector('#quick-actions-panel').hidden = enabled.length === 0;
  zone.replaceChildren(...enabled.map((action) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'quick-action';
    button.dataset.actionId = action.id;
    button.disabled = !action.available;
    button.innerHTML = `${action.label}<small>${action.hint}</small>`;
    button.addEventListener('click', () => handleQuickAction(action.id, action.label));
    return button;
  }));
}

function handleQuickAction(id, label) {
  if (id === 'search-demo') {
    visualizer.pulseState('working', 3000, 'Demo: JARVIS sucht nach einer Antwort');
    return;
  }
  if (id === 'voice-demo') {
    visualizer.pulseState('speaking', 3500, 'Demo: Ausschlag folgt später der echten JARVIS-Stimme');
    return;
  }
  if (id === 'error-demo') {
    visualizer.pulseState('error', 3500, 'Demo: Ein Fehler wird rot angezeigt');
    return;
  }
  if (id === 'offline-demo') {
    visualizer.setState('offline', 'Demo: Offline-Zustand · mit RESET zurücksetzen');
    return;
  }
  if (id === 'reset') {
    visualizer.setState('ready', 'Ring gedrückt halten · noch keine echte Aufnahme');
    return;
  }
  voiceHint.textContent = `${label}: lokale PWA-Anzeige geöffnet.`;
}

function appendMessage(role, text) {
  const message = document.createElement('div');
  message.className = `message ${role}`;
  message.textContent = text;
  messages.append(message);
  messages.scrollTop = messages.scrollHeight;
}

function showConnectionError(error) {
  const message = error instanceof Error ? error.message : 'JARVIS ist gerade nicht erreichbar.';
  visualizer.setState('error', message);
  chatStatus.textContent = 'VERBINDUNGSFEHLER';
}

async function loadSession(sessionId) {
  const session = await dashboardClient.session(sessionId);
  messages.replaceChildren();
  session.messages.forEach((message) => appendMessage(message.role === 'user' ? 'liam' : 'jarvis', message.text));
}

async function loadDashboardConnection() {
  if (!dashboardClient.isConfigured) {
    if (!localPreview) {
      messages.replaceChildren();
      appendMessage('jarvis', 'Dieses Gerät ist noch nicht mit Liam JARVIS gekoppelt. Die Gerätefreigabe folgt in Schritt 03.');
      sendButton.disabled = true;
      visualizer.setState('offline', 'Gerät noch nicht freigegeben · Schritt 03');
    }
    return;
  }
  try {
    visualizer.setState('working', 'Sichere Verbindung zu JARVIS wird geprüft');
    await dashboardClient.status();
    const payload = await dashboardClient.sessions();
    sessions.replaceChildren(...payload.sessions.map((session) => new Option(session.title, session.session_id)));
    if (sessions.value) await loadSession(sessions.value);
    sendButton.disabled = false;
    visualizer.setState('ready', 'Dashboard sicher mit JARVIS verbunden');
  } catch (error) {
    sendButton.disabled = true;
    showConnectionError(error);
  }
}

applyTheme(dashboardConfig.theme);
renderLeftModules(dashboardConfig.leftModules);
renderQuickActions(dashboardConfig.quickActions);

function setListening(active) {
  visualizer.setState(
    active ? 'listening' : 'ready',
    active ? 'Lokale Bedienungsdemo · keine Aufnahme wird übertragen' : 'Ring gedrückt halten · noch keine echte Aufnahme',
  );
}

voiceCore.addEventListener('pointerdown', (event) => { event.preventDefault(); setListening(true); });
['pointerup', 'pointercancel', 'pointerleave'].forEach((name) => voiceCore.addEventListener(name, () => setListening(false)));

dashboardButton.addEventListener('click', () => {
  dashboard.classList.toggle('open');
  dashboardButton.innerHTML = dashboard.classList.contains('open') ? 'DASHBOARD SCHLIESSEN <span>⌃</span>' : 'DASHBOARD ÖFFNEN <span>⌄</span>';
  if (dashboard.classList.contains('open')) dashboard.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

sendButton.addEventListener('click', async () => {
  const text = messageInput.value.trim();
  if (!text) { voiceHint.textContent = 'Bitte zuerst eine Nachricht eingeben.'; return; }
  appendMessage('liam', text);
  messageInput.value = '';
  visualizer.setState('working', 'Lokale Demo: JARVIS sucht nach einer Antwort');

  if (dashboardClient.isConfigured) {
    try {
      const reply = await dashboardClient.chat(sessions.value, text);
      appendMessage('jarvis', reply.text);
      if (reply.sources?.length) {
        appendMessage('jarvis', `Quellen: ${reply.sources.map((source) => source.title).join(', ')}`);
      }
      visualizer.setState('speaking', 'JARVIS hat geantwortet');
      setTimeout(() => {
        if (visualizer.state === 'speaking') visualizer.setState('ready', 'Dashboard sicher mit JARVIS verbunden');
      }, 2200);
    } catch (error) {
      showConnectionError(error);
    }
    return;
  }

  setTimeout(() => {
    if (visualizer.state !== 'working') return;
    visualizer.setState('speaking', 'Lokale Demo: Die gefundene Antwort wird gesprochen');
    setTimeout(() => {
      if (visualizer.state === 'speaking') visualizer.setState('ready', 'Ring gedrückt halten · noch keine echte Aufnahme');
    }, 2200);
  }, 1600);
});

messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendButton.click(); }
});

document.querySelector('#new-session').addEventListener('click', async () => {
  if (dashboardClient.isConfigured) {
    try {
      const session = await dashboardClient.createSession();
      sessions.add(new Option(session.title, session.session_id), 0);
      sessions.selectedIndex = 0;
      messages.replaceChildren();
      chatStatus.textContent = 'NEUE SESSION BEREIT';
    } catch (error) {
      showConnectionError(error);
    }
    return;
  }
  const count = sessions.options.length + 1;
  sessions.add(new Option(`Neue Unterhaltung ${count}`, `session-${count}`), 0);
  sessions.selectedIndex = 0;
  chatStatus.textContent = 'NEUE LOKALE SESSION';
});

sessions.addEventListener('change', async () => {
  if (!dashboardClient.isConfigured) return;
  try {
    await loadSession(sessions.value);
    visualizer.setState('ready', 'Unterhaltung geladen');
  } catch (error) {
    showConnectionError(error);
  }
});

document.querySelector('#attach-button').addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  const files = [...fileInput.files];
  fileState.textContent = files.length === 0 ? 'KEINE DATEI' : files.length === 1 ? files[0].name : `${files.length} DATEIEN AUSGEWÄHLT`;
});

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  installPrompt = event;
  installButton.hidden = false;
});
installButton.addEventListener('click', async () => {
  if (!installPrompt) return;
  installPrompt.prompt();
  await installPrompt.userChoice;
  installPrompt = null;
  installButton.hidden = true;
});
window.addEventListener('appinstalled', () => { installButton.hidden = true; });

setInterval(() => {
  clock.textContent = new Intl.DateTimeFormat('de-AT', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date());
}, 1000);

if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js'));

// Für Stufe 02: echter Audiopegel kann ohne Grafikumbau mit setVoiceLevel(0..1) eingespeist werden.
window.JarvisVisuals = visualizer;

loadDashboardConnection();
