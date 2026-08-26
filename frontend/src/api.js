const BASE = import.meta.env.BASE_URL;
const API_BASE = `${BASE}api`;

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // risposta senza corpo JSON, tengo lo statusText
    }
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  listDesktops: () => request("/desktops"),
  orphanIds: () => request("/desktops/orphans"),
  desktopInfo: (id) => request(`/desktops/${id}`),
  desktopLogs: (id, tail = 200) => request(`/desktops/${id}/logs?tail=${tail}`),
  desktopUsage: (id) => request(`/desktops/${id}/usage`),
  fleetUsage: () => request("/desktops/usage"),
  openDesktopSession: (id) => request(`/desktops/${id}/session`, { method: "POST" }),
  createDesktop: (payload) =>
    request("/desktops", { method: "POST", body: JSON.stringify(payload) }),
  startDesktop: (id) => request(`/desktops/${id}/start`, { method: "POST" }),
  stopDesktop: (id) => request(`/desktops/${id}/stop`, { method: "POST" }),
  restartDesktop: (id) => request(`/desktops/${id}/restart`, { method: "POST" }),
  deleteDesktop: (id, removeConfig) =>
    request(`/desktops/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ remove_config: removeConfig }),
    }),
  getSettings: () => request("/settings"),
  updateSettings: (payload) => request("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  setDesktopLimits: (id, payload) =>
    request(`/desktops/${id}/limits`, { method: "PUT", body: JSON.stringify(payload) }),

  login: (username, password) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),
  changePassword: (password) =>
    request("/auth/change-password", { method: "POST", body: JSON.stringify({ password }) }),

  listUsers: () => request("/users"),
  createUser: (payload) => request("/users", { method: "POST", body: JSON.stringify(payload) }),
  setUserPassword: (username, password) =>
    request(`/users/${username}/password`, { method: "PUT", body: JSON.stringify({ password }) }),
  deleteUser: (username) => request(`/users/${username}`, { method: "DELETE" }),
};

export function wsUrl(path) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${BASE}${path}`;
}
