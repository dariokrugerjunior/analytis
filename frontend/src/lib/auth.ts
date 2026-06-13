const KEY = "analytis_api_key";

export function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function setApiKey(key: string): void {
  if (!key.trim()) return;
  window.localStorage.setItem(KEY, key.trim());
}

export function clearApiKey(): void {
  window.localStorage.removeItem(KEY);
}
