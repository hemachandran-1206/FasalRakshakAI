const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const KEY = "fr_token";

// token lives in sessionStorage (cleared when the tab closes); wrapped because storage can be blocked
export const tokenStore = {
  get() { try { return sessionStorage.getItem(KEY); } catch { return null; } },
  set(t) { try { sessionStorage.setItem(KEY, t); } catch { /* ignore */ } },
  clear() { try { sessionStorage.removeItem(KEY); } catch { /* ignore */ } },
};

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

async function request(path, options = {}, { auth = false, raw = false } = {}) {
  const headers = { ...(options.headers || {}) };
  if (auth && tokenStore.get()) headers.Authorization = `Bearer ${tokenStore.get()}`;
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (res.status === 401 && auth) onUnauthorized();
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep statusText */ }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return null;
  return raw ? res : res.json();
}

const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---- public ----
// onProgress(0..1) reports upload progress (fetch cannot, so XHR is used when it is given)
export function detect(file, coords, crop, lang = "en", onProgress) {
  const form = new FormData();
  form.append("file", file);
  if (crop) form.append("crop", crop);
  form.append("lang", lang);
  if (coords) {
    form.append("latitude", coords.latitude);
    form.append("longitude", coords.longitude);
  }
  if (!onProgress) return request("/api/detect", { method: "POST", body: form });
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/api/detect`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onerror = () => reject(new Error("Network error"));
    xhr.onload = () => {
      let body = null;
      try { body = JSON.parse(xhr.responseText); } catch { /* not json */ }
      if (xhr.status >= 200 && xhr.status < 300) return resolve(body);
      const d = body?.detail;
      reject(new Error(typeof d === "string" ? d : d ? JSON.stringify(d) : xhr.statusText || `Request failed (${xhr.status})`));
    };
    xhr.send(form);
  });
}
export const getAdvisory = (crop, disease, lang = "en") =>
  request(`/api/advisories/${encodeURIComponent(crop)}/${encodeURIComponent(disease)}?lang=${lang}`);
export const getCase = (code, lang = "en") => request(`/api/cases/${encodeURIComponent(code)}?lang=${lang}`);
export const getCatalogue = () => request("/api/catalogue");
export const getHotspots = () => request("/api/hotspots");
export const getReports = () => request("/api/reports");

// ---- auth ----
export function login(email, password) {
  return request("/api/auth/login", { method: "POST", body: new URLSearchParams({ username: email, password }) });
}
export const me = () => request("/api/auth/me", {}, { auth: true });
export const changePassword = (current_password, new_password) =>
  request("/api/auth/change-password", json("POST", { current_password, new_password }), { auth: true });

// ---- admin ----
export const adminReviews = (params = {}) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null));
  return request(`/api/admin/reviews?${q}`, {}, { auth: true });
};
export const adminReview = (id) => request(`/api/admin/reviews/${id}`, {}, { auth: true });
export const adminExperts = () => request("/api/admin/experts", {}, { auth: true });
export const createExpert = (data) => request("/api/admin/experts", json("POST", data), { auth: true });
export const assignReview = (id, expert_id) =>
  request(`/api/admin/reviews/${id}/assign`, json("POST", { expert_id }), { auth: true });

// ---- advisories (staff) ----
export const listAdvisories = (params = {}) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null));
  return request(`/api/admin/advisories?${q}`, {}, { auth: true });
};
export const saveAdvisory = (data) => request("/api/admin/advisories", json("PUT", data), { auth: true });
export const verifyAdvisory = (id) => request(`/api/admin/advisories/${id}/verify`, { method: "POST" }, { auth: true });
export const importAdvisories = (file) => {
  const form = new FormData(); form.append("file", file);
  return request("/api/admin/advisories/import", { method: "POST", body: form }, { auth: true });
};
export async function exportAdvisories() {
  const res = await request("/api/admin/advisories/export.csv", {}, { auth: true, raw: true });
  return URL.createObjectURL(await res.blob());
}

// ---- expert ----
export const expertReviews = (status = "assigned") => request(`/api/expert/reviews?status=${status}`, {}, { auth: true });
export const expertReview = (id) => request(`/api/expert/reviews/${id}`, {}, { auth: true });
export const submitDecision = (id, data) => request(`/api/expert/reviews/${id}/decision`, json("POST", data), { auth: true });

// farmers' photos are private: fetch with the token and turn into a blob URL for <img>
export async function reviewImageUrl(id) {
  const res = await request(`/api/reviews/${id}/image`, {}, { auth: true, raw: true });
  return URL.createObjectURL(await res.blob());
}
