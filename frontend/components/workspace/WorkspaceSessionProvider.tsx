"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import {
  createDemoSession,
  createRawRetailDemoDataset,
  deleteDataset,
  getLimits,
  getWorkspace,
  isSessionInvalidError,
  MeshFlowApiError,
  resetDemoSession,
  uploadDataset,
  uploadPreflight,
  warmBackend,
  type DemoLimits,
  type DemoSessionResetResponse,
  type DemoUsage,
  type DatasetDeleteResponse,
  type DatasetSummary,
  type DatasetUploadResponse,
  type StructuredApiError,
  type UploadPreflightResponse,
  type WorkspaceResponse,
} from "@/lib/meshflowApi";
import {
  clearStoredDemoSessionResetFailure,
  clearStoredDemoSessionReset,
  clearStoredDemoSessionResetPending,
  clearStoredDemoSessionId,
  getStoredDemoSessionId,
  markStoredDemoSessionResetFailed,
  markStoredDemoSessionResetPending,
  markStoredDemoSessionReset,
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

export type DatasetUploadOperation = {
  kind: "csv" | "demo_dataset";
  status: "checking" | "uploading" | "preparing_demo" | "completed" | "failed";
  message: string;
  fileName?: string;
  fileSizeMb?: number;
  preflight?: UploadPreflightResponse | null;
  result?: DatasetUploadResponse | null;
  error?: StructuredApiError | null;
  updatedAt: number;
};

export type DatasetDeleteOperation = {
  datasetId: string;
  datasetName: string;
  status: "deleting" | "deleted" | "failed";
  message: string;
  response?: DatasetDeleteResponse | null;
  error?: StructuredApiError | null;
  updatedAt: number;
};

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
  isAnyProcessRunning: boolean;
  activeProcessLabel: string | null;
  datasetUploadOperation: DatasetUploadOperation | null;
  datasetDeleteOperation: DatasetDeleteOperation | null;
  refresh: () => Promise<void>;
  startSession: () => Promise<WorkspaceResponse | null>;
  resetSession: () => Promise<DemoSessionResetResponse | null>;
  startCsvDatasetUpload: (file: File) => Promise<DatasetUploadResponse | null>;
  startDemoDatasetUpload: () => Promise<DatasetUploadResponse | null>;
  clearDatasetUploadOperation: () => void;
  startDatasetDelete: (
    dataset: Pick<DatasetSummary, "id" | "name">,
  ) => Promise<DatasetDeleteResponse | null>;
  clearDatasetDeleteOperation: () => void;
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

function isRecoverableResetError(error: StructuredApiError): boolean {
  return (
    error.error_code === "BACKEND_UNAVAILABLE" ||
    error.error_code === "BACKEND_WAKEUP_TIMEOUT" ||
    error.statusCode === 0
  );
}

export function WorkspaceSessionProvider({
  children,
}: {
  children: ReactNode;
}) {
  const pathname = usePathname();
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
  const [datasetUploadOperation, setDatasetUploadOperation] =
    useState<DatasetUploadOperation | null>(null);
  const [datasetDeleteOperation, setDatasetDeleteOperation] =
    useState<DatasetDeleteOperation | null>(null);
  const datasetUploadInFlightRef = useRef(false);
  const datasetDeleteInFlightRef = useRef(false);
  const routeRefreshRef = useRef<string | null>(null);

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
      await warmBackend();
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
    async (
      nextSessionId: string,
      options: { silent?: boolean; skipWarmup?: boolean; warmup?: boolean } = {},
    ): Promise<WorkspaceResponse | null> => {
      if (!options.silent) {
        setSessionStatus("checking");
        setBackendStatus("checking");
      } else if (options.warmup) {
        setBackendStatus("checking");
      }

      try {
        if (options.warmup || (!options.silent && !options.skipWarmup)) {
          await warmBackend();
        }
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
      await warmBackend();
      const response = await createDemoSession();
      storeDemoSessionId(response.session.id);
      setSessionId(response.session.id);
      setLimits(response.limits);
      setUsage(response.usage);
      return await loadWorkspace(response.session.id, { skipWarmup: true });
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
    markStoredDemoSessionResetPending(activeSessionId);
    clearStoredDemoSessionResetFailure();
    setSessionId(activeSessionId);
    setWorkspace(null);
    setSessionStatus("active");

    try {
      await warmBackend();
      const response = await resetDemoSession(activeSessionId);
      markStoredDemoSessionReset(activeSessionId);
      setLimits(response.limits);
      setUsage(response.usage);
      setResetMessage(null);
      setBackendStatus("available");
      setSessionStatus("active");
      return response;
    } catch (caught) {
      const apiError = asApiError(caught);
      const recoverableResetError = isRecoverableResetError(apiError);
      if (recoverableResetError) {
        markStoredDemoSessionResetPending(activeSessionId);
      } else {
        clearStoredDemoSessionReset();
        clearStoredDemoSessionResetPending();
        markStoredDemoSessionResetFailed(activeSessionId, apiError.message);
      }
      setError(apiError);
      setBackendStatus(
        apiError.error_code === "BACKEND_UNAVAILABLE" ? "unavailable" : "available",
      );
      setSessionStatus(
        apiError.error_code === "BACKEND_UNAVAILABLE" ? "backend_unavailable" : "error",
      );
      return null;
    } finally {
      setIsResetting(false);
    }
  }, [sessionId]);

  const clearDatasetUploadOperation = useCallback(() => {
    setDatasetUploadOperation((current) => {
      if (
        datasetUploadInFlightRef.current &&
        current?.status !== "completed" &&
        current?.status !== "failed"
      ) {
        return current;
      }
      return null;
    });
  }, []);

  const startCsvDatasetUpload = useCallback(
    async (file: File): Promise<DatasetUploadResponse | null> => {
      const activeSessionId = sessionId ?? getStoredDemoSessionId();
      if (!activeSessionId) {
        setDatasetUploadOperation({
          kind: "csv",
          status: "failed",
          fileName: file.name,
          fileSizeMb: Math.round((file.size / (1024 * 1024)) * 100) / 100,
          message: "No active demo session is available for upload.",
          error: {
            error_code: "SESSION_ID_REQUIRED",
            failed_step: "upload_session",
            message: "No active demo session is available for upload.",
            next_action: "Launch or continue a demo session, then choose the CSV again.",
          },
          updatedAt: Date.now(),
        });
        return null;
      }

      if (datasetUploadInFlightRef.current) {
        return null;
      }

      const fileSizeMb = Math.round((file.size / (1024 * 1024)) * 100) / 100;
      datasetUploadInFlightRef.current = true;
      setDatasetUploadOperation({
        kind: "csv",
        status: "checking",
        fileName: file.name,
        fileSizeMb,
        message: "Checking file, quota, S3, and Snowflake readiness.",
        updatedAt: Date.now(),
      });

      try {
        const preflight = await uploadPreflight(file, activeSessionId);
        if (!preflight.can_upload) {
          setDatasetUploadOperation({
            kind: "csv",
            status: "failed",
            fileName: file.name,
            fileSizeMb,
            preflight,
            message: preflight.message,
            error: {
              error_code: "UPLOAD_PREFLIGHT_BLOCKED",
              failed_step: "upload_preflight",
              message: preflight.message,
              next_action: "Choose another CSV or fix the readiness blocker, then retry.",
            },
            updatedAt: Date.now(),
          });
          return null;
        }

        setDatasetUploadOperation({
          kind: "csv",
          status: "uploading",
          fileName: file.name,
          fileSizeMb,
          preflight,
          message: "Uploading to S3 and loading Snowflake Warehouse Raw.",
          updatedAt: Date.now(),
        });

        const response = await uploadDataset(file, activeSessionId);
        setDatasetUploadOperation({
          kind: "csv",
          status: "completed",
          fileName: file.name,
          fileSizeMb,
          preflight,
          result: response,
          message: response.message ?? "Upload completed. Opening Data Flow.",
          updatedAt: Date.now(),
        });
        await loadWorkspace(activeSessionId, { silent: true });
        return response;
      } catch (caught) {
        const apiError = asApiError(caught);
        setDatasetUploadOperation({
          kind: "csv",
          status: "failed",
          fileName: file.name,
          fileSizeMb,
          message: apiError.message,
          error: apiError,
          updatedAt: Date.now(),
        });
        if (isSessionInvalidError(caught)) {
          applyError(caught);
        }
        return null;
      } finally {
        datasetUploadInFlightRef.current = false;
      }
    },
    [applyError, loadWorkspace, sessionId],
  );

  const startDemoDatasetUpload = useCallback(async (): Promise<DatasetUploadResponse | null> => {
    const activeSessionId = sessionId ?? getStoredDemoSessionId();
    if (!activeSessionId) {
      setDatasetUploadOperation({
        kind: "demo_dataset",
        status: "failed",
        message: "No active demo session is available for the demo dataset.",
        error: {
          error_code: "SESSION_ID_REQUIRED",
          failed_step: "demo_dataset_session",
          message: "No active demo session is available for the demo dataset.",
          next_action: "Launch or continue a demo session, then try again.",
        },
        updatedAt: Date.now(),
      });
      return null;
    }

    if (datasetUploadInFlightRef.current) {
      return null;
    }

    datasetUploadInFlightRef.current = true;
    setDatasetUploadOperation({
      kind: "demo_dataset",
      status: "preparing_demo",
      message: "Preparing the demo dataset in S3 and Snowflake Warehouse Raw.",
      updatedAt: Date.now(),
    });

    try {
      const response = await createRawRetailDemoDataset(activeSessionId);
      setDatasetUploadOperation({
        kind: "demo_dataset",
        status: "completed",
        result: response,
        message: response.message ?? "Demo dataset prepared. Opening Data Flow.",
        updatedAt: Date.now(),
      });
      await loadWorkspace(activeSessionId, { silent: true });
      return response;
    } catch (caught) {
      const apiError = asApiError(caught);
      setDatasetUploadOperation({
        kind: "demo_dataset",
        status: "failed",
        message: apiError.message,
        error: apiError,
        updatedAt: Date.now(),
      });
      if (isSessionInvalidError(caught)) {
        applyError(caught);
      }
      return null;
    } finally {
      datasetUploadInFlightRef.current = false;
    }
  }, [applyError, loadWorkspace, sessionId]);

  const clearDatasetDeleteOperation = useCallback(() => {
    setDatasetDeleteOperation((current) => {
      if (datasetDeleteInFlightRef.current && current?.status === "deleting") {
        return current;
      }
      return null;
    });
  }, []);

  const startDatasetDelete = useCallback(
    async (
      dataset: Pick<DatasetSummary, "id" | "name">,
    ): Promise<DatasetDeleteResponse | null> => {
      const activeSessionId = sessionId ?? getStoredDemoSessionId();
      if (!activeSessionId) {
        setDatasetDeleteOperation({
          datasetId: dataset.id,
          datasetName: dataset.name,
          status: "failed",
          message: "No active demo session is available for dataset removal.",
          error: {
            error_code: "SESSION_ID_REQUIRED",
            failed_step: "dataset_delete_session",
            message: "No active demo session is available for dataset removal.",
            next_action: "Launch or continue a demo session, then try again.",
          },
          updatedAt: Date.now(),
        });
        return null;
      }

      if (datasetDeleteInFlightRef.current) {
        return null;
      }

      datasetDeleteInFlightRef.current = true;
      setDatasetDeleteOperation({
        datasetId: dataset.id,
        datasetName: dataset.name,
        status: "deleting",
        message:
          "Removing this dataset from active workspace. Dashboard and history snapshots will remain available.",
        updatedAt: Date.now(),
      });

      try {
        const response = await deleteDataset(dataset.id, activeSessionId);
        const warningText = response.cleanup.warnings.length
          ? ` Cleanup warnings: ${response.cleanup.warnings.join(" ")}`
          : "";
        await loadWorkspace(activeSessionId, { silent: true });
        setDatasetDeleteOperation({
          datasetId: dataset.id,
          datasetName: dataset.name,
          status: "deleted",
          message: `${response.message}${warningText}`,
          response,
          updatedAt: Date.now(),
        });
        return response;
      } catch (caught) {
        const apiError = asApiError(caught);
        setDatasetDeleteOperation({
          datasetId: dataset.id,
          datasetName: dataset.name,
          status: "failed",
          message: apiError.message,
          error: apiError,
          updatedAt: Date.now(),
        });
        if (isSessionInvalidError(caught)) {
          applyError(caught);
        }
        return null;
      } finally {
        datasetDeleteInFlightRef.current = false;
      }
    },
    [applyError, loadWorkspace, sessionId],
  );

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

  useEffect(() => {
    if (!sessionId || !pathname) {
      return;
    }

    const routeKey = `${sessionId}:${pathname}`;
    if (routeRefreshRef.current === routeKey) {
      return;
    }

    routeRefreshRef.current = routeKey;
    const timeoutId = window.setTimeout(() => {
      void loadWorkspace(sessionId, { silent: true, warmup: true });
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [loadWorkspace, pathname, sessionId]);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    const hasRunningTransform =
      workspace?.datasets.some((dataset) => dataset.status === "transforming") ?? false;
    if (!hasRunningTransform) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void loadWorkspace(sessionId, { silent: true });
    }, 2500);

    return () => window.clearInterval(intervalId);
  }, [loadWorkspace, sessionId, workspace?.datasets]);

  useEffect(() => {
    if (datasetDeleteOperation?.status !== "deleted") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setDatasetDeleteOperation((current) =>
        current?.status === "deleted" &&
        current.datasetId === datasetDeleteOperation.datasetId &&
        current.updatedAt === datasetDeleteOperation.updatedAt
          ? null
          : current,
      );
    }, 4500);

    return () => window.clearTimeout(timeoutId);
  }, [datasetDeleteOperation]);

  const runningUpload =
    datasetUploadOperation?.status === "checking" ||
    datasetUploadOperation?.status === "uploading" ||
    datasetUploadOperation?.status === "preparing_demo";
  const runningDelete = datasetDeleteOperation?.status === "deleting";
  const runningTransform =
    workspace?.datasets.some((dataset) => dataset.status === "transforming") ?? false;
  const activeProcessLabel = isResetting
    ? "Resetting demo workspace"
    : runningUpload
      ? datasetUploadOperation?.kind === "csv"
        ? "Checking or uploading CSV"
        : "Preparing demo dataset"
      : runningDelete
        ? "Removing dataset"
        : runningTransform
          ? "Transforming dataset"
          : null;
  const isAnyProcessRunning = activeProcessLabel !== null;

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
      isAnyProcessRunning,
      activeProcessLabel,
      datasetUploadOperation,
      datasetDeleteOperation,
      refresh,
      startSession,
      resetSession,
      startCsvDatasetUpload,
      startDemoDatasetUpload,
      clearDatasetUploadOperation,
      startDatasetDelete,
      clearDatasetDeleteOperation,
      clearSession,
    }),
    [
      activeProcessLabel,
      backendStatus,
      clearSession,
      clearDatasetDeleteOperation,
      clearDatasetUploadOperation,
      datasetDeleteOperation,
      datasetUploadOperation,
      error,
      isAnyProcessRunning,
      isResetting,
      limits,
      refresh,
      resetMessage,
      resetSession,
      sessionId,
      sessionStatus,
      startCsvDatasetUpload,
      startDatasetDelete,
      startDemoDatasetUpload,
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
