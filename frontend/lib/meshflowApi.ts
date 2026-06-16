const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

export const DEMO_SESSION_HEADER = "X-Demo-Session-Id";

export type SessionStatus = "active" | "expired" | "reset";

export type DemoSessionSummary = {
  id: string;
  status: SessionStatus;
  created_at: string;
  expires_at: string;
  retention_days: number;
};

export type DemoLimits = {
  retention_days: number;
  max_demo_datasets_per_session: number;
  max_uploaded_datasets_per_session: number;
  max_upload_file_size_mb: number;
  max_total_upload_size_mb: number;
  max_successful_analysis_runs_per_session: number;
  max_dashboard_cards_per_session: number;
  preferred_charts_per_analysis: number;
  max_charts_per_analysis: number;
  dashboards_per_session: number;
  allow_demo_reset_usage: boolean;
};

export type DemoUsage = {
  successful_uploads_used: number;
  demo_dataset_used: number;
  uploaded_datasets_used: number;
  successful_analysis_runs_used: number;
  dashboard_cards_used: number;
  total_upload_mb_used: number;
};

export type DemoSessionResponse = {
  session: DemoSessionSummary;
  limits: DemoLimits;
  usage: DemoUsage;
};

export type DemoSessionResetResponse = DemoSessionResponse & {
  usage_reset: boolean;
  message: string;
};

export type DashboardSummary = {
  dashboard_count: number;
  cards: Record<string, unknown>[];
  cards_used: number;
  cards_limit: number;
};

export type HistorySummary = {
  analysis_runs: Record<string, unknown>[];
  successful_analysis_runs_used: number;
  successful_analysis_runs_limit: number;
};

export type WorkspaceSetupStatus = {
  backend: "available";
  storage: "not_checked";
  warehouse: "not_checked";
  dbt: "not_checked";
  ai: "not_checked";
};

export type DatasetStatus =
  | "schema_review"
  | "warehouse_loaded"
  | "failed"
  | "deleted";

export type DatasetSummary = {
  id: string;
  name: string;
  source_type: "uploaded_csv" | "demo_raw_retail_later";
  status: DatasetStatus;
  row_count: number;
  column_count: number;
  raw_table_name: string;
  created_at: string;
};

export type ColumnProfileSummary = {
  column_index: number;
  raw_column_name: string;
  normalized_column_name: string;
  snowflake_column_name: string;
  detected_type:
    | "date"
    | "integer"
    | "decimal"
    | "boolean"
    | "string"
    | "identifier"
    | "unknown";
  null_count: number;
  null_rate: number;
  unique_count: number | null;
  sample_values: string[];
};

export type SchemaPreview = {
  columns: ColumnProfileSummary[];
};

export type DatasetFileSummary = {
  file_name: string;
  size_bytes: number;
  storage_key: string;
  checksum_sha256: string | null;
};

export type DatasetDetailResponse = {
  dataset: DatasetSummary;
  file: DatasetFileSummary | null;
  schema_preview: SchemaPreview;
};

export type DatasetUploadResponse = {
  status: "uploaded";
  dataset: DatasetSummary;
  file: DatasetFileSummary;
  schema_preview: SchemaPreview;
  next_route: string;
};

export type WorkspaceResponse = {
  session: DemoSessionSummary;
  datasets: DatasetSummary[];
  ready_datasets: DatasetSummary[];
  active_dataset: DatasetSummary | null;
  dashboard: DashboardSummary;
  history: HistorySummary;
  limits: DemoLimits;
  setup_status: WorkspaceSetupStatus;
};

export type LimitsResponse = {
  limits: DemoLimits;
  usage: DemoUsage | null;
};

export type PreflightStatus = "ready" | "blocked" | "failed";
export type ReadinessStatus =
  | "ready"
  | "not_configured"
  | "failed"
  | "not_checked";

export type UploadFileValidation = {
  file_name: string;
  size_bytes: number;
  size_mb: number;
  extension: string;
  detected_format: string | null;
  valid: boolean;
  row_count_previewed: number;
  column_count: number;
  headers: string[];
  warnings: string[];
  errors: string[];
};

export type UploadQuotaSummary = {
  uploaded_datasets_used: number;
  uploaded_datasets_limit: number;
  total_upload_mb_used: number;
  total_upload_mb_limit: number;
  file_size_mb_limit: number;
  errors: string[];
};

export type ReadinessCheck = {
  status: ReadinessStatus;
  message: string;
  next_action: string | null;
};

export type UploadPreflightResponse = {
  status: PreflightStatus;
  can_upload: boolean;
  file: UploadFileValidation;
  quota: UploadQuotaSummary;
  readiness: {
    s3: ReadinessCheck;
    snowflake: ReadinessCheck;
  };
  message: string;
};

export type StructuredApiError = {
  status?: "failed";
  error_code: string;
  failed_step?: string | null;
  message: string;
  next_action?: string | null;
  statusCode?: number;
};

export class MeshFlowApiError extends Error {
  readonly details: StructuredApiError;

  constructor(details: StructuredApiError) {
    super(details.message);
    this.name = "MeshFlowApiError";
    this.details = details;
  }
}

function apiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(
    /\/+$/,
    "",
  );
}

function isStructuredApiError(value: unknown): value is StructuredApiError {
  return (
    typeof value === "object" &&
    value !== null &&
    "error_code" in value &&
    "message" in value
  );
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

async function request<T>(
  path: string,
  options: {
    method?: "GET" | "POST";
    sessionId?: string | null;
    body?: BodyInit;
  } = {},
): Promise<T> {
  const headers = new Headers();
  headers.set("Accept", "application/json");
  if (options.sessionId) {
    headers.set(DEMO_SESSION_HEADER, options.sessionId);
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body,
      cache: "no-store",
    });
  } catch {
    throw new MeshFlowApiError({
      error_code: "BACKEND_UNAVAILABLE",
      failed_step: "backend",
      message: "Backend is unavailable. Start the FastAPI backend and try again.",
      next_action: "Start the backend server, then retry.",
      statusCode: 0,
    });
  }

  const body = await readJson(response);
  if (!response.ok) {
    if (isStructuredApiError(body)) {
      throw new MeshFlowApiError({
        ...body,
        statusCode: response.status,
      });
    }

    throw new MeshFlowApiError({
      error_code: "BACKEND_REQUEST_FAILED",
      failed_step: "backend",
      message: "MeshFlow could not complete the backend request.",
      next_action: "Check the backend response and retry.",
      statusCode: response.status,
    });
  }

  return body as T;
}

export function createDemoSession(): Promise<DemoSessionResponse> {
  return request<DemoSessionResponse>("/demo-sessions", { method: "POST" });
}

export function getCurrentDemoSession(
  sessionId: string,
): Promise<DemoSessionResponse> {
  return request<DemoSessionResponse>("/demo-sessions/current", { sessionId });
}

export function resetDemoSession(
  sessionId: string,
): Promise<DemoSessionResetResponse> {
  return request<DemoSessionResetResponse>("/demo-sessions/reset", {
    method: "POST",
    sessionId,
  });
}

export function getWorkspace(sessionId: string): Promise<WorkspaceResponse> {
  return request<WorkspaceResponse>("/workspace", { sessionId });
}

export function getLimits(sessionId?: string | null): Promise<LimitsResponse> {
  return request<LimitsResponse>("/limits", { sessionId });
}

export function uploadPreflight(
  file: File,
  sessionId: string,
): Promise<UploadPreflightResponse> {
  const formData = new FormData();
  formData.set("file", file);

  return request<UploadPreflightResponse>("/datasets/upload/preflight", {
    method: "POST",
    sessionId,
    body: formData,
  });
}

export function uploadDataset(
  file: File,
  sessionId: string,
): Promise<DatasetUploadResponse> {
  const formData = new FormData();
  formData.set("file", file);

  return request<DatasetUploadResponse>("/datasets/upload", {
    method: "POST",
    sessionId,
    body: formData,
  });
}

export function getDataset(
  datasetId: string,
  sessionId: string,
): Promise<DatasetDetailResponse> {
  return request<DatasetDetailResponse>(`/datasets/${datasetId}`, { sessionId });
}

export function isSessionInvalidError(error: unknown): boolean {
  if (!(error instanceof MeshFlowApiError)) {
    return false;
  }

  return (
    error.details.error_code === "SESSION_EXPIRED" ||
    error.details.error_code === "SESSION_NOT_FOUND"
  );
}
