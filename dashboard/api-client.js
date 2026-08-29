const TOKEN_STORAGE_KEY = 'liam-jarvis-dashboard-token';

export function consumePairingTokenFromFragment() {
  const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const token = (fragment.get('pair') || '').trim();
  if (!token) return 'none';

  // Das Fragment wird nie an Render gesendet und verschwindet sofort aus der Adresszeile.
  window.history.replaceState({}, '', `${window.location.pathname}${window.location.search}`);
  if (!/^[a-f0-9]{64}$/i.test(token)) return 'invalid';

  return fetch('/api/dashboard/pair', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  }).then(async (response) => {
    if (!response.ok) return 'invalid';
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    return 'paired';
  }).catch(() => 'invalid');
}

export class DashboardClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  get token() {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY) || '';
  }

  get isConfigured() {
    // HttpOnly-Geräte-Cookies sind für JavaScript absichtlich unsichtbar.
    // Auf der echten HTTPS-Seite wird die Verbindung direkt beim Server geprüft.
    return Boolean(this.token) || window.location.protocol === 'https:';
  }

  async request(path, options = {}) {
    const authorization = this.token ? { Authorization: `Bearer ${this.token}` } : {};
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      credentials: 'same-origin',
      headers: {
        ...authorization,
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `JARVIS antwortet nicht (${response.status}).`);
    return payload;
  }

  status() { return this.request('/api/dashboard/status'); }
  sessions() { return this.request('/api/dashboard/sessions'); }
  session(id) { return this.request(`/api/dashboard/sessions/${encodeURIComponent(id)}`); }
  createSession(title = 'Neue Unterhaltung') {
    return this.request('/api/dashboard/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  }
  chat(sessionId, text) {
    return this.request('/api/dashboard/chat', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, text }),
    });
  }
}

export function isLocalPreview() {
  return ['127.0.0.1', 'localhost'].includes(window.location.hostname);
}
