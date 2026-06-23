// ─────────────────────────────────────────────────────────────
// REAL BACKEND AUTH (FastAPI + JWT)
// ─────────────────────────────────────────────────────────────

// Change this block:
const API_BASE = "/api";

const TOKEN_KEY = "pcs_auth_token";

function parseJWT(token) {
  try {
    const payload = token.split(".")[1];

    const decoded = atob(
      payload.replace(/-/g, "+").replace(/_/g, "/")
    );

    return JSON.parse(decoded);
  } catch (err) {
    console.error("JWT Parse Error:", err);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────
// LOGIN
// ─────────────────────────────────────────────────────────────

export async function login(username, password, role) {
  try {
    const response = await fetch(
      `${API_BASE}/auth/login`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          password,
          role
        }),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return {
        ok: false,
        error:
          data.detail ||
          data.message ||
          "Authentication failed",
      };
    }

    sessionStorage.setItem(
      TOKEN_KEY,
      data.access_token
    );

    return {
      ok: true,
      user: data.user,
    };
  } catch (err) {
    console.error(err);

    return {
      ok: false,
      error:
        "Unable to connect to authentication server.",
    };
  }
}

// ─────────────────────────────────────────────────────────────
// LOGOUT
// ─────────────────────────────────────────────────────────────

export function logout() {
  sessionStorage.removeItem(TOKEN_KEY);
}

// ─────────────────────────────────────────────────────────────
// CURRENT SESSION
// ─────────────────────────────────────────────────────────────

export function getSession() {
  const token =
    sessionStorage.getItem(TOKEN_KEY);

  if (!token) {
    return null;
  }

  const payload = parseJWT(token);

  if (!payload) {
    sessionStorage.removeItem(TOKEN_KEY);
    return null;
  }

  const now =
    Math.floor(Date.now() / 1000);

  if (payload.exp && payload.exp < now) {
    sessionStorage.removeItem(TOKEN_KEY);
    return null;
  }

  return {
    username: payload.sub,
    name: payload.name,
    role: payload.role,
  };
}

// ─────────────────────────────────────────────────────────────
// ACCESS TOKEN
// ─────────────────────────────────────────────────────────────

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}
