import { DashboardClient, consumePairingTokenFromFragment, isLocalPreview } from './api-client.js';
import { createJarvisVisualizer } from './visualizer.js';

const app = document.querySelector('#app');
const track = document.querySelector('#track');
const buttons = [...document.querySelectorAll('[data-go]')];
const topStatus = document.querySelector('#top-status');
const voiceCore = document.querySelector('#voice-core');
const voiceState = document.querySelector('#voice-state');
const homeAttachButton = document.querySelector('#home-attach-button');
const homeFileInput = document.querySelector('#home-file-input');
const homeFileState = document.querySelector('#home-file-state');
const chatFileInput = document.querySelector('#file-input');
const fileState = document.querySelector('#file-state');
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
let microphoneStream = null;
let audioContext = null;
let analyser = null;
let microphoneFrame = null;
let microphoneStarting = false;
let pendingFiles = [];

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

async function verifyDeviceAccess() {
  const result = await pairingResultPromise;
  if (result === 'invalid') {
    visualizer.setState('error', '◉  GERÄT NICHT FREIGEGEBEN');
    return;
  }
  try {
    await dashboardClient.status();
    visualizer.setState('ready', result === 'paired' ? '◉  GERÄT VERBUNDEN' : '');
  } catch {
    if (localPreview) {
      visualizer.setState('ready');
      return;
    }
    visualizer.setState('offline');
  }
}

function sampleMicrophone() {
  if (!analyser) return;
  const samples = new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(samples);
  let sum = 0;
  for (const sample of samples) {
    const normalized = (sample - 128) / 128;
    sum += normalized * normalized;
  }
  visualizer.setVoiceLevel(Math.min(1, Math.sqrt(sum / samples.length) * 7.5));
  microphoneFrame = requestAnimationFrame(sampleMicrophone);
}

async function stopListening(nextState = 'ready') {
  if (microphoneFrame !== null) cancelAnimationFrame(microphoneFrame);
  microphoneFrame = null;
  analyser = null;
  microphoneStream?.getTracks().forEach((track) => track.stop());
  microphoneStream = null;
  if (audioContext) await audioContext.close().catch(() => {});
  audioContext = null;
  voiceCore.setAttribute('aria-pressed', 'false');
  voiceCore.setAttribute('aria-label', 'Spracheingabe starten');
  visualizer.setState(nextState);
}

async function startListening() {
  if (microphoneStarting) return;
  if (!navigator.mediaDevices?.getUserMedia) {
    visualizer.setState('error', '◉  MIKROFON NICHT VERFÜGBAR');
    return;
  }
  microphoneStarting = true;
  try {
    microphoneStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    audioContext = new AudioContext();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.72;
    audioContext.createMediaStreamSource(microphoneStream).connect(analyser);
    voiceCore.setAttribute('aria-pressed', 'true');
    voiceCore.setAttribute('aria-label', 'Spracheingabe beenden');
    visualizer.setState('listening');
    sampleMicrophone();
  } catch {
    await stopListening('error');
  } finally {
    microphoneStarting = false;
  }
}

voiceCore.addEventListener('click', async () => {
  if (microphoneStarting) return;
  if (microphoneStream) await stopListening();
  else await startListening();
});

homeAttachButton.addEventListener('click', () => homeFileInput.click());
homeFileInput.addEventListener('change', () => {
  pendingFiles = [...homeFileInput.files];
  if (!pendingFiles.length) {
    homeFileState.textContent = 'DATEI SENDEN';
    return;
  }
  const label = pendingFiles.length === 1 ? pendingFiles[0].name : `${pendingFiles.length} DATEIEN BEREIT`;
  homeFileState.textContent = label;
  homeFileState.title = label;
  fileState.textContent = label;
  try {
    const transfer = new DataTransfer();
    pendingFiles.forEach((file) => transfer.items.add(file));
    chatFileInput.files = transfer.files;
  } catch {
    // iOS behält die Auswahl intern; die Übergabe an JARVIS folgt in Schritt 04.
  }
  showPage(1);
});

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  installPrompt = event;
  document.querySelector('#install-button').hidden = false;
});
document.querySelector('#install-button').addEventListener('click', async () => {
  if (!installPrompt) return;
  installPrompt.prompt();
  await installPrompt.userChoice;
  installPrompt = null;
  document.querySelector('#install-button').hidden = true;
});

document.querySelector('#composer').addEventListener('submit', (event) => event.preventDefault());
showPage(0);
verifyDeviceAccess();
if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js'));
window.addEventListener('offline', () => visualizer.setState('offline'));
window.addEventListener('online', () => verifyDeviceAccess());
window.addEventListener('pagehide', () => {
  if (microphoneStream) stopListening();
  visualizer.stop();
});
