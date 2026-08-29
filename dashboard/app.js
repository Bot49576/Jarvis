import { DashboardClient, consumePairingTokenFromFragment } from './api-client.js';

const app = document.querySelector('#app');
const track = document.querySelector('#track');
const buttons = [...document.querySelectorAll('[data-go]')];
const topStatus = document.querySelector('#top-status');
const pairingResultPromise = Promise.resolve(consumePairingTokenFromFragment());
const dashboardClient = new DashboardClient();
let page = 0;
let pointerStart = null;
let installPrompt = null;

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
    topStatus.textContent = 'NICHT FREIGEGEBEN';
    app.dataset.state = 'error';
    return;
  }
  try {
    await dashboardClient.status();
    topStatus.textContent = result === 'paired' ? 'VERBUNDEN' : 'BEREIT';
  } catch {
    topStatus.textContent = 'NICHT FREIGEGEBEN';
    app.dataset.state = 'error';
  }
}

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
