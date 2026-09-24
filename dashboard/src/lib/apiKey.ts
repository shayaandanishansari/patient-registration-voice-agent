// The REST API needs an X-API-Key. Two sources:
// - VITE_API_KEY in dashboard/.env.local, for running locally with no sign-in step.
//   Anything VITE_* ends up in the built bundle, so never set it on a public deploy.
// - Otherwise the key is typed in at sign-in and kept only in this tab's
//   sessionStorage.
// The embedded build (served by the backend at /dashboard/) needs neither: the
// backend asks for the key before serving the page and sets a session cookie
// that same-origin API calls carry.
const STORAGE_KEY = "registration.apiKey";

export const COOKIE_AUTH = import.meta.env.MODE === "embedded";

export const ENV_API_KEY: string | undefined = import.meta.env.VITE_API_KEY || undefined;

export function getApiKey(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY) ?? ENV_API_KEY ?? null;
  } catch {
    return ENV_API_KEY ?? null;
  }
}

export function setApiKey(key: string): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, key);
  } catch {
    // Storage blocked: the key just won't survive a reload.
  }
}

export function clearApiKey(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to clear.
  }
}
