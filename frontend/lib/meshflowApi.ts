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
  | "transforming"
  | "ready_for_analysis"
  | "transform_failed"
  | "failed"
  | "deleted";

export type DatasetSummary = {
  id: string;
  name: string;
  source_type: "uploaded_csv" | "demo_raw_retail";
  status: DatasetStatus;
  row_count: number;
  column_count: number;
  raw_table_name: string;
  created_at: string;
};

export type ColumnProfileSummary = {
  id: string;
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

export type SemanticRole =
  | "identifier"
  | "date_time"
  | "measure_column"
  | "metric_candidate"
  | "dimension"
  | "unknown";

export type SemanticPreparationStatus =
  | "not_started"
  | "running"
  | "completed"
  | "failed";

export type SemanticColumnSummary = {
  id: string;
  column_profile_id: string;
  raw_column_name: string;
  suggested_name: string;
  semantic_role: SemanticRole;
  confidence: number;
  needs_review: boolean;
  reason: string;
  approved_name: string | null;
  approved_role: SemanticRole | null;
  include_in_model: boolean;
  user_edited: boolean;
  provider_name: string | null;
  provider_model: string | null;
};

export type DatasetQuestionSuggestionSummary = {
  id: string;
  question: string;
  intent: string | null;
  sort_order: number;
  provider_name: string | null;
  provider_model: string | null;
};

export type ProviderRunSummary = {
  id: string;
  task_type: string;
  provider_name: string;
  provider_model: string | null;
  status: string;
  error_code: string | null;
  error_message: string | null;
  fallback_from_provider: string | null;
  latency_ms: number | null;
  created_at: string;
};

export type ChartType = "kpi" | "line" | "bar" | "horizontal_bar" | "table";
export type ChartGenerationStatus = "not_started" | "completed" | "failed";

export type ChartFieldSpec = {
  field: string;
  label: string;
  semantic_type?: "time" | "category" | string;
  format?: "currency" | "percent" | string | null;
};

export type ChartSpec = {
  type: ChartType;
  title: string;
  source_model?: string | null;
  grain?: string | null;
  tags?: string[];
  value?: ChartFieldSpec;
  x?: ChartFieldSpec;
  y?: ChartFieldSpec;
  columns?: ChartFieldSpec[];
};

export type AnalysisRunStatus =
  | "planning"
  | "validating"
  | "running"
  | "completed"
  | "failed"
  | "reused";

export type AnalysisDecisionType =
  | "create_new"
  | "reuse_existing"
  | "needs_user_confirmation";

export type AnalysisRunSummary = {
  id: string;
  demo_session_id: string;
  dataset_id: string;
  question: string;
  normalized_question: string;
  status: AnalysisRunStatus;
  decision_type: AnalysisDecisionType;
  intent: string | null;
  source_model: string | null;
  grain: string | null;
  metrics: Record<string, unknown>[];
  dimensions: string[];
  filters: Record<string, unknown>[];
  row_count: number | null;
  error_code: string | null;
  failed_step: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type AnalysisRunDetail = AnalysisRunSummary & {
  generated_sql: string | null;
  output_schema: Record<string, unknown>[];
  preview_rows: Record<string, unknown>[];
  provider_chain: Record<string, unknown>[];
  provider_runs: ProviderRunSummary[];
};

export type AnalysisRunChartSummary = {
  id: string;
  analysis_run_id: string;
  dataset_id: string;
  chart_type: ChartType;
  title: string;
  description: string | null;
  chart_spec: ChartSpec;
  data: Record<string, unknown>[];
  source_model: string | null;
  metric_summary: string | null;
  dimension_summary: string | null;
  sort_order: number;
  created_at: string;
};

export type AnalysisRunResponse = {
  analysis_run: AnalysisRunDetail;
  charts: AnalysisRunChartSummary[];
  chart_generation_status: ChartGenerationStatus;
  chart_generation_message: string | null;
  reused: boolean;
};

export type AnalysisRunListResponse = {
  analysis_runs: AnalysisRunSummary[];
};

export type SemanticPreparationResponse = {
  status: SemanticPreparationStatus;
  message: string;
  semantic_columns: SemanticColumnSummary[];
  suggested_questions: DatasetQuestionSuggestionSummary[];
  provider_runs: ProviderRunSummary[];
  next_action: string | null;
};

export type DatasetDetailResponse = {
  dataset: DatasetSummary;
  file: DatasetFileSummary | null;
  schema_preview: SchemaPreview;
  semantic_preparation: SemanticPreparationResponse;
};

export type TransformationStatus =
  | "not_started"
  | "pending"
  | "running"
  | "completed"
  | "failed";

export type DataFlowNodeStatus =
  | "not_started"
  | "waiting"
  | "running"
  | "completed"
  | "failed";

export type DatasetTransformationRunSummary = {
  id: string;
  status: TransformationStatus;
  started_at: string;
  completed_at: string | null;
  failed_step: string | null;
  error_code: string | null;
  error_message: string | null;
  dbt_project_path: string | null;
  dbt_target_name: string | null;
  dbt_run_summary: Record<string, unknown> | null;
};

export type DbtArtifactSummary = {
  id: string;
  artifact_type: string;
  layer: string;
  name: string;
  content_redacted: string;
  file_path: string | null;
  created_at: string;
};

export type DataFlowNodeSummary = {
  id: string;
  node_type: string;
  name: string;
  label: string;
  status: DataFlowNodeStatus;
  metadata: Record<string, unknown> | null;
};

export type DataFlowEdgeSummary = {
  id: string;
  from_node_id: string;
  to_node_id: string;
  edge_type: string;
  metadata: Record<string, unknown> | null;
};

export type DatasetDataFlowResponse = {
  dataset: DatasetSummary;
  transformation: DatasetTransformationRunSummary | null;
  nodes: DataFlowNodeSummary[];
  edges: DataFlowEdgeSummary[];
  artifacts: DbtArtifactSummary[];
  models: Record<string, string[]>;
};

export type DatasetTransformResponse = {
  status: "completed";
  dataset: DatasetSummary;
  transformation_run: DatasetTransformationRunSummary;
  layers_completed: string[];
  models: Record<string, string[]>;
  next_route: string;
};

export type DatasetUploadResponse = {
  status: "uploaded" | "already_exists";
  message: string | null;
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
    method?: "GET" | "POST" | "PATCH";
    sessionId?: string | null;
    body?: BodyInit;
    json?: unknown;
  } = {},
): Promise<T> {
  const headers = new Headers();
  headers.set("Accept", "application/json");
  let requestBody = options.body;
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    requestBody = JSON.stringify(options.json);
  }
  if (options.sessionId) {
    headers.set(DEMO_SESSION_HEADER, options.sessionId);
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: requestBody,
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

  const responseBody = await readJson(response);
  if (!response.ok) {
    if (isStructuredApiError(responseBody)) {
      throw new MeshFlowApiError({
        ...responseBody,
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

  return responseBody as T;
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

export function createRawRetailDemoDataset(
  sessionId: string,
): Promise<DatasetUploadResponse> {
  return request<DatasetUploadResponse>("/datasets/demo-retail", {
    method: "POST",
    sessionId,
  });
}

export function getDataset(
  datasetId: string,
  sessionId: string,
): Promise<DatasetDetailResponse> {
  return request<DatasetDetailResponse>(`/datasets/${datasetId}`, { sessionId });
}

export function getDatasetDataFlow(
  datasetId: string,
  sessionId: string,
): Promise<DatasetDataFlowResponse> {
  return request<DatasetDataFlowResponse>(`/datasets/${datasetId}/data-flow`, {
    sessionId,
  });
}

export function transformDataset(
  datasetId: string,
  sessionId: string,
  force = false,
): Promise<DatasetTransformResponse> {
  return request<DatasetTransformResponse>(`/datasets/${datasetId}/transform`, {
    method: "POST",
    sessionId,
    json: { force },
  });
}

export function getSemanticPreparation(
  datasetId: string,
  sessionId: string,
): Promise<SemanticPreparationResponse> {
  return request<SemanticPreparationResponse>(
    `/datasets/${datasetId}/semantic-preparation`,
    { sessionId },
  );
}

export function runSemanticPreparation(
  datasetId: string,
  sessionId: string,
  force = false,
): Promise<SemanticPreparationResponse> {
  return request<SemanticPreparationResponse>(
    `/datasets/${datasetId}/semantic-preparation`,
    {
      method: "POST",
      sessionId,
      json: { force },
    },
  );
}

export function updateSemanticColumnMappings(
  datasetId: string,
  sessionId: string,
  columns: Array<{
    column_profile_id: string;
    approved_name: string;
    approved_role: SemanticRole;
    include_in_model: boolean;
  }>,
): Promise<SemanticPreparationResponse> {
  return request<SemanticPreparationResponse>(`/datasets/${datasetId}/semantic-columns`, {
    method: "PATCH",
    sessionId,
    json: { columns },
  });
}

export function createAnalysisRun(
  sessionId: string,
  input: {
    attached_dataset_id: string;
    question: string;
    force_new?: boolean;
  },
): Promise<AnalysisRunResponse> {
  return request<AnalysisRunResponse>("/analysis-runs", {
    method: "POST",
    sessionId,
    json: {
      attached_dataset_id: input.attached_dataset_id,
      question: input.question,
      force_new: input.force_new ?? false,
    },
  });
}

export function listAnalysisRuns(
  sessionId: string,
  datasetId?: string,
): Promise<AnalysisRunListResponse> {
  const query = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
  return request<AnalysisRunListResponse>(`/analysis-runs${query}`, { sessionId });
}

export function getAnalysisRun(
  sessionId: string,
  analysisRunId: string,
): Promise<AnalysisRunResponse> {
  return request<AnalysisRunResponse>(`/analysis-runs/${analysisRunId}`, {
    sessionId,
  });
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
