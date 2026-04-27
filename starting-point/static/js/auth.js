// starting-point/static/js/auth.js
// JWT token management and auth flow

const TOKEN_KEY = 'sp_token';

export function getToken() {
  const cookieToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('token='));
  if (cookieToken) {
    const token = cookieToken.split('=')[1];
    localStorage.setItem(TOKEN_KEY, token);
    document.cookie = 'token=; max-age=0; path=/';
    return token;
  }
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn() {
  return !!getToken();
}

export async function fetchWithAuth(url, options = {}) {
  const token = getToken();
  if (!token) {
    window.location.href = '/login.html';
    return;
  }
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`,
  };
  if (options.body && typeof options.body === 'string') {
    headers['Content-Type'] = 'application/json';
  }
  const resp = await fetch(url, { ...options, headers });
  if (resp.status === 401) {
    clearToken();
    window.location.href = '/login.html';
    return;
  }
  return resp;
}

export async function getCurrentUser() {
  const resp = await fetchWithAuth('/api/auth/me');
  if (!resp) return null;
  return resp.json();
}
