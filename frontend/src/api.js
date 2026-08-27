// Tiny fetch wrapper around the FastAPI backend (proxied at /api by Vite).
const TOKEN_KEY = "aisa_token";
const USER_KEY = "aisa_user";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const getStoredUser = () => {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch {
    return null;
  }
};
// Some preview/proxy layers drop the Authorization header in transit, so the
// token also travels as an X-Api-Token header and a SameSite=Lax cookie; the
// backend accepts whichever channel arrives. (Cookie is not HttpOnly — the
// SPA manages it; SameSite=Lax keeps it out of cross-site requests.)
const TOKEN_COOKIE = "aisa_token";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7; // 7 days, matches JWT expiry

export const setSession = (token, user) => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  document.cookie = `${TOKEN_COOKIE}=${token}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
};
export const clearSession = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; samesite=lax`;
};

export async function api(path, { method = "GET", body, silent401 = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    headers["X-Api-Token"] = token; // fallback channel (see setSession note)
  }

  let payload;
  if (body !== undefined) {
    if (body instanceof FormData) {
      payload = body;
    } else {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
  }

  const res = await fetch(`/api${path}`, { method, headers, body: payload });
  if (res.status === 401 && !path.startsWith("/auth/login") && !silent401) {
    // Only invalidate the session if the token used by this request is still
    // the active one — otherwise a stale in-flight 401 (e.g. an /auth/me
    // check with an old token) would wipe out a brand-new login.
    if (token && getToken() === token) {
      clearSession();
      if (!window.location.pathname.startsWith("/login")) window.location.href = "/login";
    }
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : data.detail?.[0]?.msg || res.statusText;
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return data;
}

export function fmtDate(d) {
  if (!d) return "—";
  const dt = new Date(d);
  return dt.toLocaleDateString(undefined, { month: "short", day: "numeric" }) + " " + dt.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function fmtDateTime(d) {
  if (!d) return "—";
  return new Date(d).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
