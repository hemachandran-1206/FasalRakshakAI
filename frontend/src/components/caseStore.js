// Remembers the case codes submitted from this browser (convenience only; the code itself is the key).
const KEY = "fr_recent_cases";

export function recentCases() {
  try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch { return []; }
}
export function rememberCase(code) {
  try { localStorage.setItem(KEY, JSON.stringify([code, ...recentCases().filter((c) => c !== code)].slice(0, 5))); } catch { /* ignore */ }
}
