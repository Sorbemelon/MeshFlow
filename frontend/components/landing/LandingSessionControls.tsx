"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  createDemoSession,
  getCurrentDemoSession,
  getLimits,
  getWorkspace,
  isSessionInvalidError,
  MeshFlowApiError,
  type DemoSessionSummary,
  type StructuredApiError,
} from "@/lib/meshflowApi";
import {
  clearStoredDemoSessionId,
  getStoredDemoSessionId,
  storeDemoSessionId,
} from "@/lib/demoSessionStorage";

type LandingSessionState =
  | "checking"
  | "no_session"
  | "active"
  | "expired"
  | "backend_unavailable";

type LandingBackendState = "checking" | "available" | "unavailable";

type LandingContextValue = {
  session: DemoSessionSummary | null;
  sessionState: LandingSessionState;
  backendState: LandingBackendState;
  error: StructuredApiError | null;
  isBusy: boolean;
  retry: () => Promise<void>;
  startSession: () => Promise<void>;
  continueSession: () => Promise<void>;
};

const LandingSessionContext = createContext<LandingContextValue | null>(null);

const iconProps = {
  width: 17,
  height: 17,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

function asApiError(error: unknown): StructuredApiError {
  if (error instanceof MeshFlowApiError) {
    return error.details;
  }

  return {
    error_code: "FRONTEND_SESSION_ERROR",
    failed_step: "frontend_session",
    message: "MeshFlow could not update the demo session state.",
    next_action: "Try again.",
  };
}

function useLandingSession() {
  const value = useContext(LandingSessionContext);
  if (!value) {
    throw new Error(
      "useLandingSession must be used inside LandingSessionProvider.",
    );
  }

  return value;
}

export function LandingSessionProvider({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();
  const [session, setSession] = useState<DemoSessionSummary | null>(null);
  const [sessionState, setSessionState] =
    useState<LandingSessionState>("checking");
  const [backendState, setBackendState] =
    useState<LandingBackendState>("checking");
  const [error, setError] = useState<StructuredApiError | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const validateStoredSession = useCallback(async () => {
    const storedSessionId = getStoredDemoSessionId();
    setBackendState("checking");
    setError(null);

    if (!storedSessionId) {
      try {
        await getLimits();
        setBackendState("available");
      } catch (caught) {
        setBackendState("unavailable");
        setError(asApiError(caught));
      }
      setSession(null);
      setSessionState("no_session");
      return;
    }

    setSessionState("checking");

    try {
      const response = await getCurrentDemoSession(storedSessionId);
      setSession(response.session);
      setSessionState("active");
      setBackendState("available");
      setError(null);
    } catch (caught) {
      const apiError = asApiError(caught);
      setError(apiError);

      if (isSessionInvalidError(caught)) {
        clearStoredDemoSessionId();
        setSession(null);
        setSessionState(
          apiError.error_code === "SESSION_EXPIRED" ? "expired" : "no_session",
        );
        setBackendState("available");
        return;
      }

      setSessionState("backend_unavailable");
      setBackendState("unavailable");
    }
  }, []);

  const startSession = useCallback(async () => {
    setIsBusy(true);
    setBackendState("checking");
    setError(null);

    try {
      const response = await createDemoSession();
      storeDemoSessionId(response.session.id);
      setSession(response.session);
      setSessionState("active");
      setBackendState("available");
      router.push("/demo/upload");
    } catch (caught) {
      setError(asApiError(caught));
      setBackendState("unavailable");
      setSessionState("backend_unavailable");
    } finally {
      setIsBusy(false);
    }
  }, [router]);

  const continueSession = useCallback(async () => {
    const storedSessionId = getStoredDemoSessionId();
    if (!storedSessionId) {
      await startSession();
      return;
    }

    setIsBusy(true);
    setBackendState("checking");
    setError(null);

    try {
      const workspace = await getWorkspace(storedSessionId);
      setSession(workspace.session);
      setSessionState("active");
      setBackendState("available");
      router.push(workspace.dashboard.cards.length > 0 ? "/demo/dashboard" : "/demo/upload");
    } catch (caught) {
      const apiError = asApiError(caught);
      setError(apiError);

      if (isSessionInvalidError(caught)) {
        clearStoredDemoSessionId();
        setSession(null);
        setSessionState(
          apiError.error_code === "SESSION_EXPIRED" ? "expired" : "no_session",
        );
        setBackendState("available");
      } else {
        setSessionState("backend_unavailable");
        setBackendState("unavailable");
      }
    } finally {
      setIsBusy(false);
    }
  }, [router, startSession]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void validateStoredSession();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [validateStoredSession]);

  const value = useMemo<LandingContextValue>(
    () => ({
      session,
      sessionState,
      backendState,
      error,
      isBusy,
      retry: validateStoredSession,
      startSession,
      continueSession,
    }),
    [
      backendState,
      continueSession,
      error,
      isBusy,
      session,
      sessionState,
      startSession,
      validateStoredSession,
    ],
  );

  return (
    <LandingSessionContext.Provider value={value}>
      {children}
    </LandingSessionContext.Provider>
  );
}

export function LandingStatusBadges() {
  const { backendState, sessionState } = useLandingSession();

  const demoBadge =
    sessionState === "active"
      ? { status: "ready" as const, label: "Active" }
      : sessionState === "checking"
        ? { status: "running" as const, label: "Checking" }
        : sessionState === "expired"
          ? { status: "failed" as const, label: "Expired" }
          : sessionState === "backend_unavailable"
            ? { status: "review" as const, label: "Session unknown" }
            : { status: "waiting" as const, label: "No session" };

  const backendBadge =
    backendState === "available"
      ? { status: "ready" as const, label: "Available" }
      : backendState === "checking"
        ? { status: "running" as const, label: "Checking" }
        : { status: "failed" as const, label: "Unavailable" };

  return (
    <>
      <span className="hidden items-center gap-1.5 rounded-full border border-shell-border bg-shell/55 px-2.5 py-1 sm:inline-flex">
        <span className="text-xs font-medium text-slate-300">Demo</span>
        <StatusBadge status={demoBadge.status} label={demoBadge.label} />
      </span>
      <span className="inline-flex items-center gap-1.5 rounded-full border border-shell-border bg-shell/55 px-2.5 py-1">
        <span className="text-xs font-medium text-slate-300">Backend</span>
        <StatusBadge status={backendBadge.status} label={backendBadge.label} />
      </span>
    </>
  );
}

export function LandingDemoAction() {
  const {
    backendState,
    continueSession,
    error,
    isBusy,
    retry,
    sessionState,
    startSession,
  } = useLandingSession();

  const label =
    isBusy || sessionState === "checking"
      ? "Checking..."
      : sessionState === "active"
        ? "Continue Session"
        : sessionState === "expired"
          ? "Start New Session"
          : backendState === "unavailable"
            ? "Retry Backend"
            : "Launch Demo";

  async function handleClick() {
    if (isBusy || sessionState === "checking") {
      return;
    }

    if (backendState === "unavailable") {
      await retry();
      return;
    }

    if (sessionState === "active") {
      await continueSession();
      return;
    }

    await startSession();
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <Button
          type="button"
          onClick={() => void handleClick()}
          disabled={isBusy || sessionState === "checking"}
        >
          <svg {...iconProps}>
            <path d="M5 5.5A2.5 2.5 0 0 1 7.5 3h4.8a2 2 0 0 1 1.4.6L19.4 9a2 2 0 0 1 .6 1.4v6.1a2.5 2.5 0 0 1-2.5 2.5h-10A2.5 2.5 0 0 1 5 16.5v-11z" />
            <path d="M13 3v5a2 2 0 0 0 2 2h5" />
            <path d="M9 14h6M12 11v6" />
          </svg>
          {label}
        </Button>
        <p className="whitespace-nowrap text-sm text-slate-400">
          No account needed · anonymous 3-day demo session
        </p>
      </div>
      {error ? (
        <p className="mt-2 max-w-xl text-xs leading-relaxed text-amber-200">
          {error.message}
        </p>
      ) : null}
    </div>
  );
}
