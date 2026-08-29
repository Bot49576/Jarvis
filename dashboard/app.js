import { DashboardClient, consumePairingTokenFromFragment, isLocalPreview } from './api-client.js';
import { chooseAcknowledgement } from './acknowledgements.js';
import { createJarvisVisualizer } from './visualizer.js';

const app = document.querySelector('#app');
const track = document.querySelector('#track');
const buttons = [...document.querySelectorAll('[data-go]')];
const topStatus = document.querySelector('#top-status');
const voiceCore = document.querySelector('#voice-core');
const voiceState = document.querySelector('#voice-state');
const micButton = document.querySelector('#mic-button');
const composer = document.querySelector('#composer');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');
const messages = document.querySelector('#messages');
const sessions = document.querySelector('#sessions');
const chatStatus = document.querySelector('#chat-status');
const homeAttachButton = document.querySelector('#home-attach-button');
const homeFileInput = document.querySelector('#home-file-input');
const homeFileState = document.querySelector('#home-file-state');
const chatAttachButton = document.querySelector('#attach-button');
const chatFileInput = document.querySelector('#file-input');
const fileState = document.querySelector('#file-state');
const installButton = document.querySelector('#install-button');
const healthPanel = document.querySelector('#health-panel');
const healthValue = document.querySelector('#health-value');
const healthTitle = document.querySelector('#health-title');
const healthCopy = document.querySelector('#health-copy');
const eventsMode = document.querySelector('#events-mode');
const eventsList = document.querySelector('#events-list');
const errorPanel = document.querySelector('#error-panel');
const pairingResultPromise = Promise.resolve(consumePairingTokenFromFragment());
const dashboardClient = new DashboardClient();
const localPreview = isLocalPreview();
const visualizer = createJarvisVisualizer({
  app,
  bars: [...document.querySelectorAll('.wave i')],
  voiceState,
  topStatus,
});

let page = 0;
let pointerStart = null;
let installPrompt = null;
let connected = false;
let busy = false;
let pendingFiles = [];
let microphoneStream = null;
let inputAudioContext = null;
let inputAnalyser = null;
let microphoneFrame = null;
let microphoneStarting = false;
let mediaRecorder = null;
let recordedChunks = [];
let recordingTimer = null;
let pushToTalkHeld = false;
let pushToTalkPointerId = null;
let pushToTalkControl = null;
let recordingSurface = null;
let activeAudio = null;
let outputAudioContext = null;
let outputFrame = null;
let statusTimer = null;
let previousAcknowledgement = '';

function showPage(nextPage) {
  page = Math.max(0, Math.min(2, nextPage));
  app.dataset.page = String(page);
  track.style.transform = `translateX(-${page * 100}%)`;
  buttons.forEach((button, index) => button.classList.toggle('active', index === page));
}

buttons.forEach((button) => button.addEventListener('click', () => showPage(Number(button.dataset.go))));
track.addEventListener('pointerdown', (event) => { pointerStart = event.clientX; });
track.addEventListener('pointerup', (event) => {
  if (pointerStart === null) return;
  const distance = event.clientX - pointerStart;
  if (Math.abs(distance) > 55) showPage(page + (distance < 0 ? 1 : -1));
  pointerStart = null;
});
track.addEventListener('pointercancel', () => { pointerStart = null; });

function currentTime() {
  return new Intl.DateTimeFormat('de-AT', { hour: '2-digit', minute: '2-digit' }).format(new Date());
}

function serviceCard(name) {
  return document.querySelector(`[data-service="${name}"]`);
}

function renderService(name, service) {
  const card = serviceCard(name);
  if (!card || !service) return;
  const indicator = card.querySelector('i');
  const label = card.querySelector('strong');
  const detail = card.querySelector('small');
  indicator.className = service.state === 'ready' ? 'ok' : service.state === 'warning' ? 'warn' : 'bad';
  label.textContent = service.label || 'UNBEKANNT';
  detail.textContent = service.detail || 'Kein Detail verfügbar';
}

function renderEvents(events = []) {
  eventsList.replaceChildren();
  const visibleEvents = events.slice(0, 5);
  if (!visibleEvents.length) {
    const row = document.createElement('p');
    const time = document.createElement('time');
    const message = document.createElement('span');
    time.textContent = currentTime();
    message.textContent = 'Systemstatus erfolgreich geladen.';
    row.append(time, message);
    eventsList.append(row);
    return;
  }
  visibleEvents.forEach((event) => {
    const row = document.createElement('p');
    row.dataset.level = event.level || 'info';
    const time = document.createElement('time');
    const message = document.createElement('span');
    time.textContent = event.time || '--:--';
    message.textContent = event.message || 'Statusmeldung';
    row.append(time, message);
    eventsList.append(row);
  });
}

function renderSystemStatus(status) {
  const health = status.health || {};
  const services = status.services || {};
  const score = Number.isFinite(Number(health.score)) ? Math.max(0, Math.min(100, Number(health.score))) : 0;
  healthValue.textContent = String(Math.round(score));
  healthTitle.textContent = health.title || (status.online ? 'SYSTEM ERREICHBAR' : 'SYSTEM OFFLINE');
  healthCopy.textContent = health.detail || 'Der aktuelle Zustand wurde geladen.';
  healthPanel.dataset.state = health.state || (score === 100 ? 'ready' : 'degraded');
  renderService('render', services.render);
  renderService('memory', services.memory);
  renderService('gemini', services.gemini);
  renderService('fish', services.fish);
  renderEvents(status.events);

  const problems = Object.values(services).filter((service) => service?.state && service.state !== 'ready');
  eventsMode.textContent = problems.length ? 'EINGESCHRÄNKT' : 'LIVE';
  errorPanel.className = problems.length ? 'error-clear warning' : 'error-clear';
  errorPanel.querySelector('i').textContent = problems.length ? '!' : '✓';
  errorPanel.querySelector('strong').textContent = problems.length ? 'EINSCHRÄNKUNG ERKANNT' : 'KEINE KRITISCHEN FEHLER';
  errorPanel.querySelector('span').textContent = problems.length
    ? problems.map((service) => `${service.label}: ${service.detail || 'Prüfung nötig'}`).join(' · ')
    : 'Alle notwendigen JARVIS-Dienste sind eingerichtet.';
}

function renderSystemUnavailable() {
  healthValue.textContent = '0';
  healthTitle.textContent = 'JARVIS NICHT ERREICHBAR';
  healthCopy.textContent = 'Die Verbindung zum JARVIS-Dienst ist unterbrochen.';
  healthPanel.dataset.state = 'error';
  ['render', 'memory', 'gemini', 'fish'].forEach((name) => renderService(name, {
    state: 'error', label: 'NICHT ERREICHBAR', detail: 'Verbindung unterbrochen',
  }));
  eventsMode.textContent = 'OFFLINE';
  errorPanel.className = 'error-clear error';
  errorPanel.querySelector('i').textContent = '!';
  errorPanel.querySelector('strong').textContent = 'VERBINDUNG UNTERBROCHEN';
  errorPanel.querySelector('span').textContent = 'Bitte Internetverbindung oder Render-Dienst prüfen.';
}

async function refreshSystemStatus() {
  if (!connected || document.hidden) return;
  try {
    renderSystemStatus(await dashboardClient.status());
  } catch {
    renderSystemUnavailable();
  }
}

function appendMessage(role, text, { sources = [], files = [] } = {}) {
  const article = document.createElement('article');
  article.className = `bubble ${role}`;
  const author = role === 'user' ? 'LIAM' : 'JARVIS';
  const meta = document.createElement('small');
  meta.textContent = `${author} · ${role === 'ack' ? 'SOFORT' : currentTime()}`;
  const paragraph = document.createElement('p');
  paragraph.textContent = text;
  article.append(meta, paragraph);

  if (files.length) {
    const attachmentLine = document.createElement('div');
    attachmentLine.className = 'source';
    attachmentLine.textContent = `⌁ ${files.join(', ')}`;
    article.append(attachmentLine);
  }
  if (sources.length) {
    const sourceLine = document.createElement('div');
    sourceLine.className = 'source source-links';
    sourceLine.append('◈ ');
    sources.forEach((source, index) => {
      if (index) sourceLine.append(' · ');
      const link = document.createElement('a');
      link.textContent = source.title || `Quelle ${index + 1}`;
      link.href = /^https?:\/\//i.test(source.url || '') ? source.url : '#';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      sourceLine.append(link);
    });
    article.append(sourceLine);
  }
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function appendAcknowledgement(text) {
  const article = appendMessage('ack', text);
  const thinking = document.createElement('span');
  thinking.className = 'thinking';
  thinking.append(document.createElement('i'), document.createElement('i'), document.createElement('i'));
  article.append(thinking);
  return article;
}

function setBusy(nextBusy, label = '') {
  busy = nextBusy;
  sendButton.disabled = nextBusy;
  chatAttachButton.disabled = nextBusy;
  micButton.disabled = nextBusy;
  voiceCore.disabled = nextBusy;
  if (label) chatStatus.textContent = label;
}

function showError(error) {
  const message = error instanceof Error ? error.message : 'JARVIS ist gerade nicht erreichbar.';
  appendMessage('jarvis', message);
  chatStatus.textContent = 'FEHLER';
  visualizer.setState(navigator.onLine ? 'error' : 'offline', '◉  ANFRAGE FEHLGESCHLAGEN');
}

function renderSession(session) {
  messages.replaceChildren();
  session.messages.forEach((message) => appendMessage(
    message.role === 'user' ? 'user' : 'jarvis',
    message.text,
  ));
}

async function loadSession(sessionId) {
  renderSession(await dashboardClient.session(sessionId));
}

async function connectDashboard() {
  const pairingResult = await pairingResultPromise;
  if (pairingResult === 'invalid') {
    visualizer.setState('error', '◉  GERÄT NICHT FREIGEGEBEN');
    chatStatus.textContent = 'NICHT FREIGEGEBEN';
    return;
  }
  try {
    const status = await dashboardClient.status();
    renderSystemStatus(status);
    const payload = await dashboardClient.sessions();
    sessions.replaceChildren(...payload.sessions.map(
      (session) => new Option(session.title, session.session_id),
    ));
    if (sessions.value) await loadSession(sessions.value);
    connected = true;
    chatStatus.textContent = 'MEMORY AKTIV';
    visualizer.setState('ready', pairingResult === 'paired' ? '◉  GERÄT VERBUNDEN' : '');
    clearInterval(statusTimer);
    statusTimer = setInterval(refreshSystemStatus, 30_000);
  } catch (error) {
    connected = false;
    renderSystemUnavailable();
    if (localPreview) {
      chatStatus.textContent = 'LOKALE ANSICHT';
      visualizer.setState('ready');
      return;
    }
    showError(error);
  }
}

function selectedFileLabel(files) {
  if (!files.length) return 'TEXT · AUDIO · DATEI';
  return files.length === 1 ? files[0].name : `${files.length} DATEIEN BEREIT`;
}

function setPendingFiles(files) {
  pendingFiles = [...files].slice(0, 4);
  const label = selectedFileLabel(pendingFiles);
  fileState.textContent = label;
  homeFileState.textContent = pendingFiles.length ? label : 'DATEI SENDEN';
  homeFileState.title = pendingFiles.length ? label : '';
}

function chooseHomeFiles() { homeFileInput.click(); }
function chooseChatFiles() { chatFileInput.click(); }

homeAttachButton.addEventListener('click', chooseHomeFiles);
chatAttachButton.addEventListener('click', chooseChatFiles);
homeFileInput.addEventListener('change', () => {
  setPendingFiles(homeFileInput.files);
  showPage(1);
});
chatFileInput.addEventListener('change', () => setPendingFiles(chatFileInput.files));

function sampleAnalyser(analyser, callback) {
  const samples = new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(samples);
  let sum = 0;
  for (const sample of samples) {
    const normalized = (sample - 128) / 128;
    sum += normalized * normalized;
  }
  callback(Math.min(1, Math.sqrt(sum / samples.length) * 7.5));
}

function sampleMicrophone() {
  if (!inputAnalyser) return;
  sampleAnalyser(inputAnalyser, (level) => visualizer.setVoiceLevel(level));
  microphoneFrame = requestAnimationFrame(sampleMicrophone);
}

function recordingMimeType() {
  const types = ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm'];
  return types.find((type) => MediaRecorder.isTypeSupported(type)) || '';
}

function createAudioContext() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) throw new Error('Audioverarbeitung wird nicht unterstützt.');
  return new AudioContextClass();
}

async function releaseMicrophone(nextState = 'ready') {
  if (microphoneFrame !== null) cancelAnimationFrame(microphoneFrame);
  microphoneFrame = null;
  inputAnalyser = null;
  microphoneStream?.getTracks().forEach((track) => track.stop());
  microphoneStream = null;
  if (inputAudioContext) await inputAudioContext.close().catch(() => {});
  inputAudioContext = null;
  clearTimeout(recordingTimer);
  recordingTimer = null;
  voiceCore.setAttribute('aria-pressed', 'false');
  voiceCore.setAttribute('aria-label', 'Zum Sprechen gedrückt halten');
  micButton.classList.remove('recording');
  micButton.setAttribute('aria-pressed', 'false');
  micButton.setAttribute('aria-label', 'Zum Sprechen gedrückt halten');
  visualizer.setState(nextState);
}

async function transcribeAndSend(blob, mimeType, surface) {
  if (!blob.size) throw new Error('Die Sprachaufnahme war leer.');
  if (surface !== 'home') showPage(1);
  visualizer.setState('working');
  chatStatus.textContent = 'SPRACHE WIRD VERARBEITET';
  const extension = mimeType.includes('mp4') ? 'm4a' : 'webm';
  const transcript = await dashboardClient.transcribe(blob, `aufnahme.${extension}`);
  messageInput.value = transcript.text;
  await sendCurrentMessage();
}

async function stopRecording(submit = true) {
  const recorder = mediaRecorder;
  const surface = recordingSurface || 'chat';
  mediaRecorder = null;
  recordingSurface = null;
  if (!recorder || recorder.state === 'inactive') {
    await releaseMicrophone();
    return;
  }
  const stopped = new Promise((resolve) => recorder.addEventListener('stop', resolve, { once: true }));
  recorder.stop();
  await stopped;
  const mimeType = recorder.mimeType || recordingMimeType() || 'audio/webm';
  const blob = new Blob(recordedChunks, { type: mimeType });
  recordedChunks = [];
  await releaseMicrophone(submit ? 'working' : 'ready');
  if (submit) {
    try {
      await transcribeAndSend(blob, mimeType, surface);
    } catch (error) {
      showError(error);
      setBusy(false);
    }
  }
}

async function startRecording({ pushToTalk = false, source = 'chat' } = {}) {
  if (microphoneStarting || mediaRecorder) return;
  if (!connected) {
    showError(new Error('Dieses Gerät ist noch nicht mit JARVIS verbunden.'));
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    showError(new Error('Spracheingabe wird auf diesem Gerät nicht unterstützt.'));
    return;
  }
  microphoneStarting = true;
  try {
    microphoneStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    if (pushToTalk && !pushToTalkHeld) {
      await releaseMicrophone();
      return;
    }
    inputAudioContext = createAudioContext();
    inputAnalyser = inputAudioContext.createAnalyser();
    inputAnalyser.fftSize = 512;
    inputAnalyser.smoothingTimeConstant = 0.72;
    inputAudioContext.createMediaStreamSource(microphoneStream).connect(inputAnalyser);
    const mimeType = recordingMimeType();
    mediaRecorder = new MediaRecorder(microphoneStream, mimeType ? { mimeType } : undefined);
    recordingSurface = source;
    recordedChunks = [];
    mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data.size) recordedChunks.push(event.data);
    });
    mediaRecorder.start(250);
    const activeControl = source === 'home' ? voiceCore : micButton;
    activeControl.setAttribute('aria-pressed', 'true');
    activeControl.setAttribute('aria-label', 'Zum Senden loslassen');
    if (source === 'chat') micButton.classList.add('recording');
    visualizer.setState('listening');
    chatStatus.textContent = 'HÖRT ZU · ZUM SENDEN LOSLASSEN';
    sampleMicrophone();
    recordingTimer = setTimeout(() => {
      pushToTalkHeld = false;
      pushToTalkPointerId = null;
      pushToTalkControl = null;
      stopRecording(true);
    }, 120_000);
  } catch {
    await releaseMicrophone('error');
  } finally {
    microphoneStarting = false;
  }
}

async function beginPushToTalk(event, source, control) {
  if (!event.isPrimary || event.button !== 0 || control.disabled || pushToTalkHeld) return;
  event.preventDefault();
  event.stopPropagation?.();
  pushToTalkHeld = true;
  pushToTalkPointerId = event.pointerId;
  pushToTalkControl = control;
  if (event.pointerId >= 0) control.setPointerCapture?.(event.pointerId);
  await startRecording({ pushToTalk: true, source });
}

async function finishPushToTalk(event, control, submit = true) {
  if (!pushToTalkHeld || pushToTalkControl !== control
      || (event.pointerId !== undefined && event.pointerId !== pushToTalkPointerId)) return;
  event.preventDefault();
  event.stopPropagation?.();
  pushToTalkHeld = false;
  pushToTalkPointerId = null;
  pushToTalkControl = null;
  if (mediaRecorder) await stopRecording(submit);
}

function bindPushToTalk(control, source) {
  control.addEventListener('pointerdown', (event) => beginPushToTalk(event, source, control));
  control.addEventListener('pointerup', (event) => finishPushToTalk(event, control, true));
  control.addEventListener('pointercancel', (event) => finishPushToTalk(event, control, false));
  control.addEventListener('contextmenu', (event) => event.preventDefault());
  control.addEventListener('keydown', (event) => {
    if ((event.key === ' ' || event.key === 'Enter') && !event.repeat) beginPushToTalk({
      isPrimary: true,
      button: 0,
      pointerId: -1,
      preventDefault: () => event.preventDefault(),
      stopPropagation: () => event.stopPropagation(),
    }, source, control);
  });
  control.addEventListener('keyup', (event) => {
    if (event.key === ' ' || event.key === 'Enter') finishPushToTalk({
      pointerId: -1,
      preventDefault: () => event.preventDefault(),
      stopPropagation: () => event.stopPropagation(),
    }, control, true);
  });
}

bindPushToTalk(voiceCore, 'home');
bindPushToTalk(micButton, 'chat');

function stopOutputAudio() {
  if (outputFrame !== null) cancelAnimationFrame(outputFrame);
  outputFrame = null;
  if (activeAudio) {
    activeAudio.pause();
    URL.revokeObjectURL(activeAudio.src);
  }
  activeAudio = null;
  if (outputAudioContext) outputAudioContext.close().catch(() => {});
  outputAudioContext = null;
}

function sampleOutput(analyser) {
  if (!activeAudio || activeAudio.paused) return;
  sampleAnalyser(analyser, (level) => visualizer.setVoiceLevel(level));
  outputFrame = requestAnimationFrame(() => sampleOutput(analyser));
}

async function beginPlayback(audio, bubble) {
  stopOutputAudio();
  activeAudio = audio;
  try {
    await audio.play();
    bubble.querySelector('.play-reply')?.remove();
  } catch {
    activeAudio = null;
    if (!bubble.querySelector('.play-reply')) {
      const playButton = document.createElement('button');
      playButton.type = 'button';
      playButton.className = 'play-reply';
      playButton.textContent = '▶ ANTWORT ABSPIELEN';
      playButton.addEventListener('click', () => beginPlayback(audio, bubble), { once: true });
      bubble.append(playButton);
    }
    visualizer.setState('ready');
    return;
  }
  try {
    outputAudioContext = createAudioContext();
    const analyser = outputAudioContext.createAnalyser();
    analyser.fftSize = 512;
    outputAudioContext.createMediaElementSource(audio).connect(analyser);
    analyser.connect(outputAudioContext.destination);
    await outputAudioContext.resume();
    sampleOutput(analyser);
  } catch {
    if (outputAudioContext) outputAudioContext.close().catch(() => {});
    outputAudioContext = null;
  }
  audio.addEventListener('ended', () => {
    stopOutputAudio();
    visualizer.setState('ready');
    chatStatus.textContent = 'MEMORY AKTIV';
  }, { once: true });
  visualizer.setState('speaking');
  chatStatus.textContent = 'JARVIS SPRICHT';
}

async function speakReply(text, bubble) {
  try {
    const blob = await dashboardClient.speech(text);
    const audio = new Audio(URL.createObjectURL(blob));
    audio.preload = 'auto';
    await beginPlayback(audio, bubble);
  } catch {
    chatStatus.textContent = 'TEXTANTWORT BEREIT';
    visualizer.setState('ready');
  }
}

async function ensureSession() {
  if (sessions.value) return sessions.value;
  const session = await dashboardClient.createSession();
  sessions.add(new Option(session.title, session.session_id), 0);
  sessions.selectedIndex = 0;
  return session.session_id;
}

async function sendCurrentMessage() {
  if (busy) return;
  const text = messageInput.value.trim();
  const files = [...pendingFiles];
  if (!text && !files.length) return;
  if (!connected) {
    showError(new Error('Dieses Gerät ist noch nicht mit JARVIS verbunden.'));
    return;
  }
  setBusy(true, 'JARVIS ARBEITET');
  visualizer.setState('working');
  const visibleText = text || 'Bitte analysiere die angehängte Datei.';
  appendMessage('user', visibleText, { files: files.map((file) => file.name) });
  const acknowledgement = chooseAcknowledgement(text, {
    hasFiles: files.length > 0,
    previous: previousAcknowledgement,
  });
  const acknowledgementBubble = acknowledgement ? appendAcknowledgement(acknowledgement) : null;
  if (acknowledgement) previousAcknowledgement = acknowledgement;
  messageInput.value = '';
  setPendingFiles([]);
  homeFileInput.value = '';
  chatFileInput.value = '';
  try {
    const sessionId = await ensureSession();
    const reply = await dashboardClient.chat(sessionId, text, files);
    acknowledgementBubble?.remove();
    const bubble = appendMessage('jarvis', reply.text, { sources: reply.sources || [] });
    setBusy(false, reply.voice_enabled ? 'SPRACHAUSGABE WIRD GELADEN' : 'MEMORY AKTIV');
    if (reply.voice_enabled) await speakReply(reply.text, bubble);
    else visualizer.setState('ready');
  } catch (error) {
    acknowledgementBubble?.remove();
    setBusy(false);
    showError(error);
  }
}

composer.addEventListener('submit', (event) => {
  event.preventDefault();
  sendCurrentMessage();
});
messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendCurrentMessage();
  }
});
document.querySelector('#new-session').addEventListener('click', async () => {
  if (!connected || busy) return;
  try {
    const session = await dashboardClient.createSession();
    sessions.add(new Option(session.title, session.session_id), 0);
    sessions.selectedIndex = 0;
    messages.replaceChildren();
    chatStatus.textContent = 'NEUE UNTERHALTUNG';
  } catch (error) {
    showError(error);
  }
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

showPage(0);
connectDashboard();
if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js'));
window.addEventListener('offline', () => {
  connected = false;
  renderSystemUnavailable();
  visualizer.setState('offline');
});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) refreshSystemStatus();
});
window.addEventListener('online', connectDashboard);
window.addEventListener('pagehide', () => {
  clearInterval(statusTimer);
  if (mediaRecorder) stopRecording(false);
  else if (microphoneStream) releaseMicrophone();
  stopOutputAudio();
  visualizer.stop();
});
