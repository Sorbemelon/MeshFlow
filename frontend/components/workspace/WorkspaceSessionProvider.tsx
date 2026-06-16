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
import {
  createDemoSession,
  getLimits,
  getWorkspace,
  isSessionInvalidError,
  MeshFlowApiError,
  resetDemoSession,
  type DemoLimits,
  type DemoSessionResetResponse,
  type DemoUsage,
  type StructuredApiError,
  type WorkspaceResponse,
} from "@/lib/meshflowApi";
import {
  clearStoredDemoSessionId,
  getStoredDemoSessionId,
  storeDemoSessionId,
} from "@/lib/demoSessionStorage";

export type WorkspaceSessionStatus =
  | "checking"
  | "no_session"
  | "active"
  | "expired"
  | "backend_unavailable"
  | "error";

export type BackendStatus = "checking" | "available" | "unavailable";

type WorkspaceSessionContextValue = {
  sessionId: string | null;
  workspace: WorkspaceResponse | null;
  limits: DemoLimits | null;
  usage: DemoUsage | null;
  sessionStatus: WorkspaceSessionStatus;
  backendStatus: BackendStatus;
  error: StructuredApiError | null;
  resetMessage: string | null;
  isResetting: boolean;
  refresh: () => Promise<void>;
  startSession: () => Promise<WorkspaceResponse | null>;
  resetSession: () => Promise<DemoSessionResetResponse | null>;
  clearSession: () => void;
};

const WorkspaceSessionContext =
  createContext<WorkspaceSessionContextValue | null>(null);

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

export function WorkspaceSessionProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null);
  const [limits, setLimits] = useState<DemoLimits | null>(null);
  const [usage, setUsage] = useState<DemoUsage | null>(null);
  const [sessionStatus, setSessionStatus] =
    useState<WorkspaceSessionStatus>("checking");
  const [backendStatus, setBackendStatus] =
    useState<BackendStatus>("checking");
  const [error, setError] = useState<StructuredApiError | null>(null);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);

  const clearSession = useCallback(() => {
    clearStoredDemoSessionId();
    setSessionId(null);
    setWorkspace(null);
    setUsage(null);
    setSessionStatus("no_session");
  }, []);

  const applyError = useCallback(
    (caught: unknown) => {
      const apiError = asApiError(caught);
      setError(apiError);

      if (isSessionInvalidError(caught)) {
        clearSession();
        setSessionStatus(
          apiError.error_code === "SESSION_EXPIRED" ? "expired" : "no_session",
        );
        setBackendStatus("available");
        return;
      }

      if (apiError.error_code === "BACKEND_UNAVAILABLE") {
        setBackendStatus("unavailable");
        setSessionStatus(sessionId ? "backend_unavailable" : "no_session");
        return;
      }

      setBackendStatus("available");
      setSessionStatus("error");
    },
    [clearSession, sessionId],
  );

  const checkPublicLimits = useCallback(async () => {
    setBackendStatus("checking");

    try {
      const response = await getLimits();
      setLimits(response.limits);
      setUsage(null);
      setError(null);
      setBackendStatus("available");
      setSessionStatus("no_session");
    } catch (caught) {
      const apiError = asApiError(caught);
      setError(apiError);
      setBackendStatus("unavailable");
      setSessionStatus("no_session");
    }
  }, []);

  const loadWorkspace = useCallback(
    async (nextSessionId: string): Promise<WorkspaceResponse | null> => {
      setSessionStatus("checking");
      setBackendStatus("checking");

      try {
        const [nextWorkspace, nextLimits] = await Promise.all([
          getWorkspace(nextSessionId),
          getLimits(nextSessionId),
        ]);
        setSessionId(nextSessionId);
        setWorkspace(nextWorkspace);
        setLimits(nextLimits.limits);
        setUsage(nextLimits.usage);
        setError(null);
        setBackendStatus("available");
        setSessionStatus("active");
        return nextWorkspace;
      } catch (caught) {
        applyError(caught);
        return null;
      }
    },
    [applyError],
  );

  const refresh = useCallback(async () => {
    const activeSessionId = sessionId ?? getStoredDemoSessionId();
    if (!activeSessionId) {
      await checkPublicLimits();
      return;
    }

    await loadWorkspace(activeSessionId);
  }, [checkPublicLimits, loadWorkspace, sessionId]);

  const startSession = useCallback(async () => {
    setSessionStatus("checking");
    setBackendStatus("checking");
    setResetMessage(null);

    try {
      const response = await createDemoSession();
      storeDemoSessionId(response.session.id);
      setSessionId(response.session.id);
      setLimits(response.limits);
      setUsage(response.usage);
      return await loadWorkspace(response.session.id);
    } catch (caught) {
      applyError(caught);
      return null;
    }
  }, [applyError, loadWorkspace]);

  const resetSession = useCallback(async () => {
    const activeSessionId = sessionId ?? getStoredDemoSessionId();
    if (!activeSessionId) {
      setSessionStatus("no_session");
      return null;
    }

    setIsResetting(true);
    setResetMessage(null);

    try {
      const response = await resetDemoSession(activeSessionId);
      setLimits(response.limits);
      setUsage(response.usage);
      setResetMessage(response.message);
      await loadWorkspace(activeSessionId);
      return response;
    } catch (caught) {
      applyError(caught);
      return null;
    } finally {
      setIsResetting(false);
    }
  }, [applyError, loadWorkspace, sessionId]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      const storedSessionId = getStoredDemoSessionId();
      if (!storedSessionId) {
        void checkPublicLimits();
        return;
      }

      setSessionId(storedSessionId);
      void loadWorkspace(storedSessionId);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [checkPublicLimits, loadWorkspace]);

  const value = useMemo<WorkspaceSessionContextValue>(
    () => ({
      sessionId,
      workspace,
      limits,
      usage,
      sessionStatus,
      backendStatus,
      error,
      resetMessage,
      isResetting,
      refresh,
      startSession,
      resetSession,
      clearSession,
    }),
    [
      backendStatus,
      clearSession,
      error,
      isResetting,
      limits,
      refresh,
      resetMessage,
      resetSession,
      sessionId,
      sessionStatus,
      startSession,
      usage,
      workspace,
    ],
  );

  return (
    <WorkspaceSessionContext.Provider value={value}>
      {children}
    </WorkspaceSessionContext.Provider>
  );
}

export function useWorkspaceSession(): WorkspaceSessionContextValue {
  const value = useContext(WorkspaceSessionContext);
  if (!value) {
    throw new Error(
      "useWorkspaceSession must be used inside WorkspaceSessionProvider.",
    );
  }

  return value;
}
