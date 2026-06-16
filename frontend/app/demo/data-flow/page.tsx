"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import { cn } from "@/lib/cn";
import {
  deleteDataset,
  getDatasetDataFlow,
  getDataset,
  MeshFlowApiError,
  runSemanticPreparation,
  transformDataset,
  updateSemanticColumnMappings,
  type DatasetDataFlowResponse,
  type DatasetDetailResponse,
  type DatasetSummary,
  type SemanticColumnSummary,
  type SemanticRole,
} from "@/lib/meshflowApi";

const PREP_STAGES = [
  "Raw Input",
  "Warehouse Raw",
  "Staging",
  "Intermediate",
  "Dimensional Model",
  "Data Marts",
];

const TABS = [
  "Schema Preview",
  "Warehouse Raw",
  "Transformations",
  "Dimensional Model & Data Marts",
];

const SEMANTIC_ROLE_OPTIONS: SemanticRole[] = [
  "identifier",
  "date_time",
  "measure_column",
  "metric_candidate",
  "dimension",
  "unknown",
];

type MappingDraft = {
  approved_name: string;
  approved_role: SemanticRole;
  include_in_model: boolean;
};

type StageState = "Completed" | "Not Started" | "Waiting" | "Running" | "Failed";

const ip = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

function datasetLabel(dataset: DatasetSummary): string {
  return dataset.name || dataset.id;
}

function stageState(
  stage: string,
  dataset: DatasetSummary | null,
  dataFlow: DatasetDataFlowResponse | null,
  transformRunning: boolean,
): StageState {
  if (!dataset) {
    return "Not Started";
  }

  const node = dataFlow?.nodes.find((candidate) => candidate.label === stage);
  if (node) {
    if (node.status === "completed") {
      return "Completed";
    }
    if (node.status === "running") {
      return "Running";
    }
    if (node.status === "waiting") {
      return "Waiting";
    }
    if (node.status === "failed") {
      return "Failed";
    }
    return "Not Started";
  }

  if (dataset.status === "ready_for_analysis") {
    return "Completed";
  }

  if (stage === "Raw Input" || stage === "Warehouse Raw") {
    return "Completed";
  }

  if (transformRunning) {
    return stage === "Staging" ? "Running" : "Waiting";
  }

  return "Not Started";
}

function formatNullRate(value: number): string {
  return `${Math.round(value * 10000) / 100}%`;
}

function roleLabel(role: SemanticRole): string {
  return role.replaceAll("_", " ");
}

function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function buildMappingDrafts(detail: DatasetDetailResponse): Record<string, MappingDraft> {
  const semanticByProfile = new Map(
    detail.semantic_preparation.semantic_columns.map(
      (semanticColumn) => [semanticColumn.column_profile_id, semanticColumn] as const,
    ),
  );

  const drafts: Record<string, MappingDraft> = {};
  for (const column of detail.schema_preview.columns) {
    const semanticColumn = semanticByProfile.get(column.id);
    drafts[column.id] = {
      approved_name:
        semanticColumn?.approved_name ??
        semanticColumn?.suggested_name ??
        column.normalized_column_name.toLowerCase(),
      approved_role:
        semanticColumn?.approved_role ?? semanticColumn?.semantic_role ?? "unknown",
      include_in_model: semanticColumn?.include_in_model ?? true,
    };
  }

  return drafts;
}

function DataFlowContent() {
  const searchParams = useSearchParams();
  const { refresh, sessionId, workspace } = useWorkspaceSession();
  const datasets = useMemo(() => workspace?.datasets ?? [], [workspace?.datasets]);
  const [manualDatasetId, setManualDatasetId] = useState("");
  const [datasetDetail, setDatasetDetail] = useState<DatasetDetailResponse | null>(null);
  const [dataFlow, setDataFlow] = useState<DatasetDataFlowResponse | null>(null);
  const [detailState, setDetailState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [detailError, setDetailError] = useState<string | null>(null);
  const [semanticActionState, setSemanticActionState] = useState<
    "idle" | "generating" | "saving"
  >("idle");
  const [semanticActionMessage, setSemanticActionMessage] = useState<string | null>(null);
  const [transformActionState, setTransformActionState] = useState<"idle" | "running">("idle");
  const [transformMessage, setTransformMessage] = useState<string | null>(null);
  const [transformNextRoute, setTransformNextRoute] = useState<string | null>(null);
  const [deletingDatasetId, setDeletingDatasetId] = useState<string | null>(null);
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null);
  const [mappingDrafts, setMappingDrafts] = useState<Record<string, MappingDraft>>({});
  const queryDatasetId = searchParams.get("datasetId") ?? "";
  const selectedDatasetId = useMemo(() => {
    if (datasets.length === 0) {
      return "";
    }

    if (manualDatasetId && datasets.some((dataset) => dataset.id === manualDatasetId)) {
      return manualDatasetId;
    }

    if (queryDatasetId && datasets.some((dataset) => dataset.id === queryDatasetId)) {
      return queryDatasetId;
    }

    return datasets[0].id;
  }, [datasets, manualDatasetId, queryDatasetId]);

  const activeDatasetDetail =
    datasetDetail?.dataset.id === selectedDatasetId ? datasetDetail : null;
  const selectedDataset =
    activeDatasetDetail?.dataset ??
    datasets.find((dataset) => dataset.id === selectedDatasetId) ??
    null;
  const hasDataset = datasets.length > 0;
  const semanticPreparation = activeDatasetDetail?.semantic_preparation ?? null;
  const semanticStatus = semanticPreparation?.status ?? "not_started";
  const isReadyForAnalysis = selectedDataset?.status === "ready_for_analysis";
  const semanticMappingsReady =
    (activeDatasetDetail?.semantic_preparation.semantic_columns.length ?? 0) > 0;
  const canGenerateSemantic =
    Boolean(activeDatasetDetail) &&
    semanticActionState === "idle" &&
    semanticStatus === "not_started";
  const canRefreshSemantic =
    Boolean(activeDatasetDetail) &&
    semanticActionState === "idle" &&
    semanticStatus === "completed";
  const canSaveMappings = Boolean(activeDatasetDetail) && semanticActionState === "idle";
  const canTransform =
    Boolean(activeDatasetDetail) &&
    semanticMappingsReady &&
    !isReadyForAnalysis &&
    semanticActionState === "idle" &&
    transformActionState === "idle";
  const semanticByProfileId = useMemo(() => {
    const pairs =
      activeDatasetDetail?.semantic_preparation.semantic_columns.map(
        (semanticColumn) => [semanticColumn.column_profile_id, semanticColumn] as const,
      ) ?? [];
    return new Map<string, SemanticColumnSummary>(pairs);
  }, [activeDatasetDetail?.semantic_preparation.semantic_columns]);

  useEffect(() => {
    if (!sessionId || !selectedDatasetId) {
      return;
    }

    let cancelled = false;
    const activeSessionId = sessionId;
    const activeDatasetId = selectedDatasetId;

    async function loadDatasetDetail() {
      await Promise.resolve();
      if (cancelled) {
        return;
      }

      setDetailState("loading");
      setDetailError(null);
      setDataFlow(null);
      setTransformMessage(null);
      setTransformNextRoute(null);

      try {
        const [response, flowResponse] = await Promise.all([
          getDataset(activeDatasetId, activeSessionId),
          getDatasetDataFlow(activeDatasetId, activeSessionId),
        ]);
        if (cancelled) {
          return;
        }

        setDatasetDetail(response);
        setDataFlow(flowResponse);
        setMappingDrafts(buildMappingDrafts(response));
        setDetailState("ready");
      } catch (caught) {
        if (cancelled) {
          return;
        }

        setDetailState("error");
        setDetailError(
          caught instanceof MeshFlowApiError
            ? caught.details.message
            : "Schema preview could not be loaded.",
        );
      }
    }

    void loadDatasetDetail();

    return () => {
      cancelled = true;
    };
  }, [selectedDatasetId, sessionId]);

  function updateMappingDraft(columnProfileId: string, patch: Partial<MappingDraft>) {
    setMappingDrafts((current) => ({
      ...current,
      [columnProfileId]: {
        ...(current[columnProfileId] ?? {
          approved_name: "",
          approved_role: "unknown",
          include_in_model: true,
        }),
        ...patch,
      },
    }));
  }

  async function handleSemanticPreparation(force = false) {
    if (!sessionId || !selectedDatasetId || semanticActionState !== "idle") {
      return;
    }

    setSemanticActionState("generating");
    setSemanticActionMessage(null);

    try {
      const response = await runSemanticPreparation(selectedDatasetId, sessionId, force);
      if (activeDatasetDetail?.dataset.id === selectedDatasetId) {
        const nextDetail = {
          ...activeDatasetDetail,
          semantic_preparation: response,
        };
        setDatasetDetail(nextDetail);
        setMappingDrafts(buildMappingDrafts(nextDetail));
      }
      setSemanticActionMessage(response.message);
    } catch (caught) {
      setSemanticActionMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "Semantic preparation could not reach the backend.",
      );
    } finally {
      setSemanticActionState("idle");
    }
  }

  async function handleSaveMappings() {
    if (!sessionId || !selectedDatasetId || !activeDatasetDetail || semanticActionState !== "idle") {
      return;
    }

    setSemanticActionState("saving");
    setSemanticActionMessage(null);

    try {
      const response = await updateSemanticColumnMappings(
        selectedDatasetId,
        sessionId,
        activeDatasetDetail.schema_preview.columns.map((column) => ({
          column_profile_id: column.id,
          approved_name:
            mappingDrafts[column.id]?.approved_name ??
            column.normalized_column_name.toLowerCase(),
          approved_role: mappingDrafts[column.id]?.approved_role ?? "unknown",
          include_in_model: mappingDrafts[column.id]?.include_in_model ?? true,
        })),
      );
      if (activeDatasetDetail?.dataset.id === selectedDatasetId) {
        const nextDetail = {
          ...activeDatasetDetail,
          semantic_preparation: response,
        };
        setDatasetDetail(nextDetail);
        setMappingDrafts(buildMappingDrafts(nextDetail));
      }
      setSemanticActionMessage("Schema mappings saved for dbt transformation.");
    } catch (caught) {
      setSemanticActionMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "Schema mappings could not be saved.",
      );
    } finally {
      setSemanticActionState("idle");
    }
  }

  async function handleTransform() {
    if (!sessionId || !selectedDatasetId || !activeDatasetDetail || !canTransform) {
      return;
    }

    setTransformActionState("running");
    setTransformMessage(null);
    setTransformNextRoute(null);

    try {
      const response = await transformDataset(selectedDatasetId, sessionId);
      const [nextDetail, nextFlow] = await Promise.all([
        getDataset(selectedDatasetId, sessionId),
        getDatasetDataFlow(selectedDatasetId, sessionId),
        refresh(),
      ]);
      setDatasetDetail(nextDetail);
      setDataFlow(nextFlow);
      setMappingDrafts(buildMappingDrafts(nextDetail));
      setTransformNextRoute(response.next_route);
      setTransformMessage("dbt transformation completed. Data Marts are ready for later analysis.");
    } catch (caught) {
      setTransformMessage(
        caught instanceof MeshFlowApiError
          ? `${caught.details.message}${
              caught.details.next_action ? ` ${caught.details.next_action}` : ""
            }`
          : "dbt transformation could not reach the backend.",
      );
    } finally {
      setTransformActionState("idle");
    }
  }

  async function handleDeleteDataset(dataset: DatasetSummary) {
    if (!sessionId || deletingDatasetId) {
      return;
    }

    const confirmed = window.confirm(
      `Remove "${datasetLabel(
        dataset,
      )}" from active dataset management? Existing dashboard cards and history remain available, and quota usage is not restored.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingDatasetId(dataset.id);
    setDeleteMessage(null);

    try {
      const response = await deleteDataset(dataset.id, sessionId);
      setManualDatasetId((current) => (current === dataset.id ? "" : current));
      if (selectedDatasetId === dataset.id) {
        setDatasetDetail(null);
        setDataFlow(null);
        setDetailState("idle");
      }
      await refresh();
      const warningText = response.cleanup.warnings.length
        ? ` Cleanup warnings: ${response.cleanup.warnings.join(" ")}`
        : "";
      setDeleteMessage(`${response.message}${warningText}`);
    } catch (caught) {
      setDeleteMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "Dataset could not be removed from the active workspace.",
      );
    } finally {
      setDeletingDatasetId(null);
    }
  }

  return (
    <div className="px-6 py-8">
      <header className="mb-6 flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-500/12 text-blue-600">
          <svg {...ip}>
            <circle cx="6" cy="6" r="2" />
            <circle cx="18" cy="12" r="2" />
            <circle cx="6" cy="18" r="2" />
            <path d="M8 6h5a2 2 0 0 1 2 2v1.5M16 12h-5a2 2 0 0 0-2 2v1.5" />
          </svg>
        </span>
        <div>
          <h1 className="text-xl font-semibold text-ink">Data Flow</h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Prepare a dataset through the warehouse and dbt, stage by stage.
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[390px_minmax(0,1fr)]">
        <aside
          className="self-start rounded-lg border border-border bg-surface p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]"
          style={{ borderTop: "4px solid #2563eb" }}
        >
          <div>
            <h3 className="mb-2 text-xs font-semibold text-ink-muted">
              Dataset
            </h3>
            <select
              disabled={!hasDataset}
              value={selectedDatasetId}
              aria-label="Select dataset"
              onChange={(event) => setManualDatasetId(event.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2.5 text-sm text-ink disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-ink-muted"
            >
              {!hasDataset ? <option value="">No available dataset</option> : null}
              {datasets.map((dataset) => (
                <option key={dataset.id} value={dataset.id}>
                  {datasetLabel(dataset)}
                </option>
              ))}
            </select>
            {selectedDataset ? (
              <div className="mt-3 rounded-md border border-blue-200 bg-blue-50/50 px-3 py-2">
                <p className="font-mono text-xs text-blue-900">
                  {selectedDataset.raw_table_name}
                </p>
                <p className="mt-1 text-xs text-blue-800">
                  {selectedDataset.row_count} rows, {selectedDataset.column_count} columns
                </p>
              </div>
            ) : null}
            {datasets.length > 0 ? (
              <div className="mt-3 rounded-md border border-border bg-surface-muted px-3 py-2">
                <p className="text-xs font-semibold text-ink-muted">
                  Active datasets
                </p>
                <div className="mt-2 grid gap-1.5">
                  {datasets.map((dataset) => (
                    <div
                      key={dataset.id}
                      className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-md border border-border bg-surface px-2.5 py-2"
                    >
                      <span className="truncate text-xs font-medium text-ink-soft">
                        {datasetLabel(dataset)}
                      </span>
                      <button
                        type="button"
                        disabled={deletingDatasetId !== null}
                        onClick={() => void handleDeleteDataset(dataset)}
                        title="Remove dataset from the active workspace. Quota usage is not restored."
                        className="cursor-pointer rounded-md p-1.5 text-slate-500 transition-colors hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                        aria-label={`Remove ${datasetLabel(dataset)}`}
                      >
                        <svg
                          width={15}
                          height={15}
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth={1.9}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden
                        >
                          <path d="M3 6h18" />
                          <path d="M8 6V4h8v2" />
                          <path d="M19 6l-1 14H6L5 6" />
                          <path d="M10 11v5M14 11v5" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
                <p className="mt-2 text-[0.6875rem] leading-relaxed text-ink-muted">
                  Existing dashboard cards and history remain available from stored snapshots.
                </p>
              </div>
            ) : null}
            {deleteMessage ? (
              <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-800">
                {deleteMessage}
              </p>
            ) : null}
          </div>

          <div className="mt-5">
            <h3 className="mb-2 text-xs font-semibold text-ink-muted">
              Preparation status
            </h3>
            <ol className="space-y-1.5">
              {PREP_STAGES.map((stage) => {
                const state = stageState(
                  stage,
                  selectedDataset,
                  dataFlow,
                  transformActionState === "running",
                );
                const completed = state === "Completed";
                const running = state === "Running";
                const failed = state === "Failed";
                return (
                  <li
                    key={stage}
                    className="flex items-center gap-2.5 rounded-md border border-border bg-surface px-3 py-2"
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "h-2 w-2 shrink-0 rounded-full",
                        completed
                          ? "bg-status-success"
                          : running
                            ? "bg-status-running"
                            : failed
                              ? "bg-status-danger"
                              : "bg-status-neutral/35",
                      )}
                    />
                    <span className="whitespace-nowrap text-sm text-ink-soft">
                      {stage}
                    </span>
                    <span className="ml-auto whitespace-nowrap text-xs text-ink-muted">
                      {state}
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>
        </aside>

        <section className="min-w-0">
          <div
            role="tablist"
            aria-label="Data Flow views"
            className="mb-4 flex flex-wrap gap-0 border-b border-border"
          >
            {TABS.map((tab, i) => {
              const active = i === 0;
              return (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  disabled={!hasDataset || !active}
                  aria-selected={active}
                  title={
                    active
                      ? "Schema preview is available after upload."
                      : "dbt transformation evidence appears after Transform succeeds."
                  }
                  className={cn(
                    "-mb-px border-b-2 px-3.5 py-2.5 text-sm font-medium transition-colors duration-150",
                    active
                      ? "border-primary text-ink"
                      : "border-transparent text-ink-muted",
                    "disabled:cursor-not-allowed disabled:opacity-50",
                  )}
                >
                  {tab}
                </button>
              );
            })}
          </div>

          {!hasDataset ? (
            <EmptyState
              title="No dataset to prepare yet"
              description="Upload a CSV. After S3 upload and Snowflake Raw load succeed, the schema preview appears here."
              ctaLabel="Upload Dataset"
              ctaHref="/demo/upload"
              className="border-blue-200 bg-blue-50/40"
              icon={
                <svg {...ip}>
                  <path d="M12 16V4M7 9l5-5 5 5" />
                  <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
                </svg>
              }
            />
          ) : (
            <div className="rounded-lg border border-blue-200 bg-surface p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-ink">
                    Schema Preview
                  </h2>
                  <p className="mt-1 text-sm text-ink-muted">
                    Real deterministic profile from the raw CSV loaded into Snowflake Warehouse Raw.
                  </p>
                </div>
                <StatusBadge
                  status={
                    transformActionState === "running"
                      ? "running"
                      : isReadyForAnalysis
                        ? "ready"
                        : selectedDataset?.status === "transform_failed"
                          ? "failed"
                          : "review"
                  }
                  label={
                    transformActionState === "running"
                      ? "Transforming"
                      : isReadyForAnalysis
                        ? "Ready for analysis"
                        : selectedDataset?.status === "transform_failed"
                          ? "Transform failed"
                          : "Schema review"
                  }
                />
              </div>

              {detailState === "loading" ? (
                <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
                  Loading schema preview...
                </div>
              ) : null}

              {detailState === "error" ? (
                <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {detailError}
                </div>
              ) : null}

              {activeDatasetDetail ? (
                <>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-md border border-border bg-surface-muted px-3 py-2">
                      <p className="text-xs text-ink-muted">Rows</p>
                      <p className="font-mono text-sm text-ink">
                        {activeDatasetDetail.dataset.row_count}
                      </p>
                    </div>
                    <div className="rounded-md border border-border bg-surface-muted px-3 py-2">
                      <p className="text-xs text-ink-muted">Columns</p>
                      <p className="font-mono text-sm text-ink">
                        {activeDatasetDetail.dataset.column_count}
                      </p>
                    </div>
                    <div className="rounded-md border border-border bg-surface-muted px-3 py-2">
                      <p className="text-xs text-ink-muted">Status</p>
                      <p className="font-mono text-sm text-ink">
                        {activeDatasetDetail.dataset.status}
                      </p>
                    </div>
                  </div>

                  {semanticPreparation ? (
                    <div
                      className={cn(
                        "mt-4 rounded-md border px-3 py-3",
                        semanticStatus === "completed"
                          ? "border-indigo-200 bg-indigo-50/45"
                          : semanticStatus === "failed"
                            ? "border-red-200 bg-red-50"
                            : "border-border bg-surface-muted",
                      )}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-semibold text-ink">
                              Semantic preparation
                            </p>
                            <StatusBadge
                              status={
                                semanticActionState === "generating"
                                  ? "running"
                                  : semanticStatus === "completed"
                                    ? "ai"
                                    : semanticStatus === "failed"
                                      ? "failed"
                                      : "waiting"
                              }
                              label={
                                semanticActionState === "generating"
                                  ? "Generating"
                                  : semanticStatus === "completed"
                                    ? "Suggestions ready"
                                    : semanticStatus === "failed"
                                      ? "Unavailable"
                                      : "Not started"
                              }
                            />
                          </div>
                          <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                            {semanticActionMessage ?? semanticPreparation.message}
                          </p>
                          {semanticPreparation.next_action ? (
                            <p className="mt-1 text-xs text-ink-muted">
                              {semanticPreparation.next_action}
                            </p>
                          ) : null}
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {canGenerateSemantic ? (
                            <Button
                              size="sm"
                              onClick={() => void handleSemanticPreparation(false)}
                              title="Ask the configured AI provider ladder for semantic suggestions."
                            >
                              Generate AI Suggestions
                            </Button>
                          ) : null}
                          {semanticStatus === "failed" && semanticActionState === "idle" ? (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => void handleSemanticPreparation(true)}
                              title="Retry the provider ladder. No fallback suggestions are invented."
                            >
                              Retry
                            </Button>
                          ) : null}
                          {canRefreshSemantic ? (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => void handleSemanticPreparation(true)}
                              title="Refresh suggestions with the configured AI provider ladder."
                            >
                              Refresh AI Suggestions
                            </Button>
                          ) : null}
                        </div>
                      </div>

                      {semanticPreparation.provider_runs.length > 0 ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {semanticPreparation.provider_runs.slice(-4).map((run) => (
                            <span
                              key={run.id}
                              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-[0.6875rem] font-medium text-ink-muted"
                            >
                              {run.provider_name}
                              <span className="font-mono text-ink">
                                {run.status}
                              </span>
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  <div className="mt-4 overflow-x-auto rounded-md border border-border">
                    <table className="min-w-[1180px] divide-y divide-border text-left text-sm">
                      <thead className="bg-surface-muted text-xs font-semibold text-ink-muted">
                        <tr>
                          <th className="px-3 py-2">Raw column</th>
                          <th className="px-3 py-2">Detected type</th>
                          <th className="px-3 py-2">Null rate</th>
                          <th className="px-3 py-2">Suggested name</th>
                          <th className="px-3 py-2">Semantic role</th>
                          <th className="px-3 py-2">Confidence</th>
                          <th className="px-3 py-2">Review</th>
                          <th className="px-3 py-2">Approved mapping</th>
                          <th className="px-3 py-2">Samples</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border bg-surface">
                        {activeDatasetDetail.schema_preview.columns.map((column) => {
                          const semanticColumn = semanticByProfileId.get(column.id);
                          const draft = mappingDrafts[column.id];
                          return (
                            <tr
                              key={column.id}
                              className={cn(
                                semanticColumn?.needs_review ? "bg-amber-50/35" : "",
                              )}
                            >
                              <td className="px-3 py-2">
                                <p className="font-mono text-xs text-ink">
                                  {column.raw_column_name}
                                </p>
                                <p className="mt-0.5 font-mono text-[0.6875rem] text-ink-muted">
                                  {column.snowflake_column_name}
                                </p>
                              </td>
                              <td className="px-3 py-2">
                                <span className="rounded-full bg-primary-tint px-2 py-0.5 text-xs font-semibold text-primary">
                                  {column.detected_type}
                                </span>
                              </td>
                              <td className="px-3 py-2 font-mono text-xs text-ink-soft">
                                {formatNullRate(column.null_rate)}
                              </td>
                              <td className="px-3 py-2">
                                {semanticColumn ? (
                                  <div>
                                    <p className="font-mono text-xs text-ink">
                                      {semanticColumn.suggested_name}
                                    </p>
                                    <p className="mt-1 max-w-[240px] text-xs leading-relaxed text-ink-muted">
                                      {semanticColumn.reason}
                                    </p>
                                  </div>
                                ) : (
                                  <span className="text-xs text-ink-muted">
                                    Not generated
                                  </span>
                                )}
                              </td>
                              <td className="px-3 py-2">
                                {semanticColumn ? (
                                  <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                                    {roleLabel(semanticColumn.semantic_role)}
                                  </span>
                                ) : (
                                  <span className="text-xs text-ink-muted">Unknown</span>
                                )}
                              </td>
                              <td className="px-3 py-2 font-mono text-xs text-ink-soft">
                                {semanticColumn
                                  ? formatConfidence(semanticColumn.confidence)
                                  : "n/a"}
                              </td>
                              <td className="px-3 py-2">
                                {semanticColumn?.needs_review ? (
                                  <StatusBadge status="review" label="Needs review" />
                                ) : semanticColumn ? (
                                  <StatusBadge status="ready" label="Confident" />
                                ) : (
                                  <StatusBadge status="waiting" label="Pending" />
                                )}
                              </td>
                              <td className="min-w-[260px] px-3 py-2">
                                <div className="grid gap-2">
                                  <input
                                    value={draft?.approved_name ?? ""}
                                    aria-label={`Approved name for ${column.raw_column_name}`}
                                    onChange={(event) =>
                                      updateMappingDraft(column.id, {
                                        approved_name: event.target.value,
                                      })
                                    }
                                    className="w-full rounded-md border border-border bg-surface px-2.5 py-1.5 font-mono text-xs text-ink"
                                  />
                                  <div className="flex items-center gap-2">
                                    <select
                                      value={draft?.approved_role ?? "unknown"}
                                      aria-label={`Approved role for ${column.raw_column_name}`}
                                      onChange={(event) =>
                                        updateMappingDraft(column.id, {
                                          approved_role: event.target.value as SemanticRole,
                                        })
                                      }
                                      className="min-w-0 flex-1 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-ink"
                                    >
                                      {SEMANTIC_ROLE_OPTIONS.map((role) => (
                                        <option key={role} value={role}>
                                          {roleLabel(role)}
                                        </option>
                                      ))}
                                    </select>
                                    <label className="inline-flex items-center gap-1.5 text-xs text-ink-muted">
                                      <input
                                        type="checkbox"
                                        checked={draft?.include_in_model ?? true}
                                        onChange={(event) =>
                                          updateMappingDraft(column.id, {
                                            include_in_model: event.target.checked,
                                          })
                                        }
                                      />
                                      Include
                                    </label>
                                  </div>
                                </div>
                              </td>
                              <td className="max-w-[260px] px-3 py-2 font-mono text-xs text-ink-muted">
                                {column.sample_values.length > 0
                                  ? column.sample_values.join(", ")
                                  : "No non-null sample"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-surface-muted px-3 py-2">
                    <p className="text-xs text-ink-muted">
                      Transform runs dbt against Snowflake. No dataset is marked ready unless
                      dbt completes successfully.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={!canSaveMappings}
                        onClick={() => void handleSaveMappings()}
                        title="Save reviewed names and roles for dbt transformation."
                      >
                        {semanticActionState === "saving" ? "Saving..." : "Save mappings"}
                      </Button>
                      {isReadyForAnalysis && transformNextRoute ? (
                        <Button size="sm" href={transformNextRoute}>
                          Open Dashboard
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          disabled={!canTransform}
                          onClick={() => void handleTransform()}
                          title={
                            semanticMappingsReady
                              ? "Run dbt on Snowflake to build Staging, Intermediate, Dimensional Model, and Data Marts."
                              : "Generate or save semantic mappings before running dbt."
                          }
                        >
                          {transformActionState === "running" ? "Transforming..." : "Transform"}
                        </Button>
                      )}
                    </div>
                  </div>

                  {transformMessage ? (
                    <div
                      className={cn(
                        "mt-3 rounded-md border px-3 py-2 text-sm",
                        isReadyForAnalysis
                          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                          : "border-amber-200 bg-amber-50 text-amber-800",
                      )}
                    >
                      {transformMessage}
                    </div>
                  ) : null}

                  {dataFlow?.models && Object.keys(dataFlow.models).length > 0 ? (
                    <div className="mt-3 rounded-md border border-blue-200 bg-blue-50/35 px-3 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-ink">
                          dbt transformation evidence
                        </p>
                        {dataFlow.transformation ? (
                          <StatusBadge
                            status={
                              dataFlow.transformation.status === "completed"
                                ? "ready"
                                : dataFlow.transformation.status === "failed"
                                  ? "failed"
                                  : "running"
                            }
                            label={dataFlow.transformation.status.replaceAll("_", " ")}
                          />
                        ) : null}
                      </div>
                      <div className="mt-3 grid gap-2 md:grid-cols-2">
                        {Object.entries(dataFlow.models).map(([layer, models]) => (
                          <div
                            key={layer}
                            className="rounded-md border border-blue-100 bg-surface px-3 py-2"
                          >
                            <p className="text-xs font-semibold uppercase tracking-normal text-blue-700">
                              {layer.replaceAll("_", " ")}
                            </p>
                            <p className="mt-1 font-mono text-xs leading-relaxed text-ink-soft">
                              {models.length ? models.join(", ") : "No models recorded"}
                            </p>
                          </div>
                        ))}
                      </div>
                      {dataFlow.artifacts.length > 0 ? (
                        <p className="mt-3 text-xs text-ink-muted">
                          {dataFlow.artifacts.length} redacted dbt artifacts stored for review.
                        </p>
                      ) : null}
                    </div>
                  ) : null}

                  {semanticPreparation?.suggested_questions.length ? (
                    <div className="mt-3 rounded-md border border-indigo-200 bg-indigo-50/40 px-3 py-3">
                      <p className="text-sm font-semibold text-ink">
                        Prepared question suggestions
                      </p>
                      <ul className="mt-2 grid gap-2">
                        {semanticPreparation.suggested_questions.map((question) => (
                          <li
                            key={question.id}
                            className="rounded-md border border-indigo-100 bg-surface px-3 py-2 text-xs text-ink-soft"
                          >
                            {question.question}
                            {question.intent ? (
                              <span className="ml-2 font-mono text-[0.6875rem] text-indigo-600">
                                {question.intent}
                              </span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </>
              ) : null}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default function DataFlowPage() {
  return (
    <Suspense
      fallback={
        <div className="px-6 py-8 text-sm text-ink-muted">
          Loading Data Flow...
        </div>
      }
    >
      <DataFlowContent />
    </Suspense>
  );
}
