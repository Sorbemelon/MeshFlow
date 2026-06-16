export const DEMO_SESSION_STORAGE_KEY = "meshflow_demo_session_id";

export function getStoredDemoSessionId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(DEMO_SESSION_STORAGE_KEY);
}

export function storeDemoSessionId(sessionId: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(DEMO_SESSION_STORAGE_KEY, sessionId);
}

export function clearStoredDemoSessionId(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(DEMO_SESSION_STORAGE_KEY);
}
