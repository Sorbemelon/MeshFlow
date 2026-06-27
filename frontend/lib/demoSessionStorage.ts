export const DEMO_SESSION_STORAGE_KEY = "meshflow_demo_session_id";
const DEMO_SESSION_RESET_STORAGE_KEY = "meshflow_demo_session_reset_id";
const DEMO_SESSION_RESET_PENDING_STORAGE_KEY =
  "meshflow_demo_session_reset_pending_id";
const DEMO_SESSION_RESET_FAILURE_STORAGE_KEY =
  "meshflow_demo_session_reset_failure";

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
  window.localStorage.removeItem(DEMO_SESSION_RESET_STORAGE_KEY);
  window.localStorage.removeItem(DEMO_SESSION_RESET_PENDING_STORAGE_KEY);
  window.localStorage.removeItem(DEMO_SESSION_RESET_FAILURE_STORAGE_KEY);
}

export function clearStoredDemoSessionId(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(DEMO_SESSION_STORAGE_KEY);
  window.localStorage.removeItem(DEMO_SESSION_RESET_STORAGE_KEY);
  window.localStorage.removeItem(DEMO_SESSION_RESET_PENDING_STORAGE_KEY);
  window.localStorage.removeItem(DEMO_SESSION_RESET_FAILURE_STORAGE_KEY);
}

export function markStoredDemoSessionReset(sessionId: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(DEMO_SESSION_RESET_STORAGE_KEY, sessionId);
  window.localStorage.removeItem(DEMO_SESSION_RESET_PENDING_STORAGE_KEY);
  window.localStorage.removeItem(DEMO_SESSION_RESET_FAILURE_STORAGE_KEY);
}

export function clearStoredDemoSessionReset(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(DEMO_SESSION_RESET_STORAGE_KEY);
}

export function isStoredDemoSessionReset(sessionId: string): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  return window.localStorage.getItem(DEMO_SESSION_RESET_STORAGE_KEY) === sessionId;
}

export function markStoredDemoSessionResetPending(sessionId: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(DEMO_SESSION_RESET_PENDING_STORAGE_KEY, sessionId);
  window.localStorage.removeItem(DEMO_SESSION_RESET_FAILURE_STORAGE_KEY);
}

export function clearStoredDemoSessionResetPending(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(DEMO_SESSION_RESET_PENDING_STORAGE_KEY);
}

export function isStoredDemoSessionResetPending(sessionId: string): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  return (
    window.localStorage.getItem(DEMO_SESSION_RESET_PENDING_STORAGE_KEY) ===
    sessionId
  );
}

export function markStoredDemoSessionResetFailed(
  sessionId: string,
  message: string,
): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    DEMO_SESSION_RESET_FAILURE_STORAGE_KEY,
    JSON.stringify({ sessionId, message }),
  );
}

export function clearStoredDemoSessionResetFailure(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(DEMO_SESSION_RESET_FAILURE_STORAGE_KEY);
}

export function getStoredDemoSessionResetFailure(
  sessionId: string,
): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawFailure = window.localStorage.getItem(
    DEMO_SESSION_RESET_FAILURE_STORAGE_KEY,
  );
  if (!rawFailure) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawFailure) as {
      sessionId?: unknown;
      message?: unknown;
    };
    if (parsed.sessionId !== sessionId || typeof parsed.message !== "string") {
      return null;
    }
    return parsed.message;
  } catch {
    window.localStorage.removeItem(DEMO_SESSION_RESET_FAILURE_STORAGE_KEY);
    return null;
  }
}
