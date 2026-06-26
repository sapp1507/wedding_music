const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

function secretFromUrl() {
  return new URLSearchParams(window.location.search).get("secret") || "";
}

function getCookie(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  const secret = secretFromUrl();
  if (secret) {
    headers["X-Song-Request-Secret"] = secret;
  }
  const csrfToken = getCookie("csrftoken");
  if (csrfToken && !["GET", "HEAD", "OPTIONS"].includes(options.method || "GET")) {
    headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.link ||
      data?.song_title ||
      data?.non_field_errors?.[0] ||
      "Не удалось выполнить запрос";
    throw new Error(Array.isArray(message) ? message[0] : message);
  }

  return data;
}

export function fetchMoments() {
  return request("/songs/moments/");
}

export function fetchCsrfToken() {
  return request("/csrf/");
}

export function fetchPublicSongs() {
  return request("/songs/public/");
}

export function fetchAllSongs() {
  return request("/songs/");
}

export function fetchCurrentUser() {
  return request("/auth/me/");
}

export function loginAdmin(payload) {
  return request("/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logoutAdmin() {
  return request("/auth/logout/", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function createSongRequest(payload) {
  return request("/songs/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function previewSongLink(link) {
  return request("/songs/preview-link/", {
    method: "POST",
    body: JSON.stringify({ link }),
  });
}

export function setSongApproval(id, approved) {
  return request(`/songs/${id}/approve/`, {
    method: "PATCH",
    body: JSON.stringify({ approved }),
  });
}

export function csvExportUrl() {
  return `${API_BASE_URL}/songs/export/`;
}
