const storageKey = "verihire.employerToken";

export function readEmployerToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.sessionStorage.getItem(storageKey) ?? "";
}

export function writeEmployerToken(token: string): void {
  window.sessionStorage.setItem(storageKey, token);
}

export function clearEmployerToken(): void {
  window.sessionStorage.removeItem(storageKey);
}

export function employerAuthHeaders(): HeadersInit {
  const token = readEmployerToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
