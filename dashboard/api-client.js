const TOKEN_STORAGE_KEY = 'liam-jarvis-dashboard-token';

export class DashboardClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  get token() {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY) || '';
  }

  get isConfigured() {
    return Boolean(this.token);
  }

  async request(path, options = {}) {
    if (!this.token) throw new Error('Dieses Gerät ist noch nicht freigegeben.');
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${this.token}`,
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
