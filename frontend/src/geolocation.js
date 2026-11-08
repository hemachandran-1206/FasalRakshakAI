// Asks the browser for the user's position. Resolves to {latitude, longitude} or null if
// unavailable / denied / timed out, so the caller can carry on without location.
// Browsers only allow this on https:// pages or localhost.
export function getBrowserLocation(timeoutMs = 8000) {
  return new Promise((resolve) => {
    if (!("geolocation" in navigator)) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: false, timeout: timeoutMs, maximumAge: 60000 },
    );
  });
}
