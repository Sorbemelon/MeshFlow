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
] as const;

type DataFlowTab = (typeof TABS)[number];

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

const RAW_RETAIL_DIMENSIONS = [
  {
    name: "dim_customer",
    grain: "one row per customer",
    keys: ["customer_id"],
    dimensions: ["customer_name", "customer_segment"],
  },
  {
    name: "dim_product",
    grain: "one row per product",
    keys: ["product_id"],
    dimensions: ["product_name", "product_category"],
  },
  {
    name: "dim_store",
    grain: "one row per store",
    keys: ["store_id"],
    dimensions: ["store_name", "store_region"],
  },
  {
    name: "dim_date",
    grain: "one row per order date",
    keys: ["order_date"],
    dimensions: ["order_month"],
  },
];

const RAW_RETAIL_MARTS = [
  {
    name: "mart_sales_performance",
    grain: "month and product category",
    metrics: ["total_revenue", "total_orders", "total_quantity", "gross_margin"],
    dimensions: ["order_month", "product_category"],
  },
  {
    name: "mart_product_performance",
    grain: "product category and product",
    metrics: ["total_revenue", "total_quantity", "gross_margin"],
    dimensions: ["product_category", "product_name"],
  },
  {
    name: "mart_customer_segments",
    grain: "customer segment",
    metrics: ["total_revenue", "total_orders", "average_order_value"],
    dimensions: ["customer_segment"],
  },
  {
    name: "mart_store_performance",
    grain: "store region and store",
    metrics: ["total_revenue", "total_orders"],
    dimensions: ["store_region", "store_name"],
  },
];

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

function semanticConfidenceLabel(semanticColumn: SemanticColumnSummary | undefined): string {
  if (!semanticColumn) {
    return "Not AI-scored";
  }
  if (semanticColumn.user_edited) {
    return "Manual";
  }
  if (!semanticColumn.provider_name || semanticColumn.confidence <= 0) {
    return "Not AI-scored";
  }
  return formatConfidence(semanticColumn.confidence);
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

function dataFlowTabDescription(tab: DataFlowTab): string {
  if (tab === "Warehouse Raw") {
    return "Warehouse Raw table and profiled columns from the live Snowflake load.";
  }
  if (tab === "Transformations") {
    return "dbt staging and intermediate model evidence from the latest transform run.";
  }
  if (tab === "Dimensional Model & Data Marts") {
    return "Dimensional model and Data Mart outputs recorded after dbt succeeds.";
  }

  return "Real deterministic profile from the raw CSV loaded into Snowflake Warehouse Raw.";
}

function modelLayerLabel(layer: string): string {
  return layer.replaceAll("_", " ");
}

function hasModel(models: Record<string, string[]>, modelName: string): boolean {
  return Object.values(models).some((names) => names.includes(modelName));
}

function InlineSpinner() {
  return (
    <svg
      width={14}
      height={14}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      aria-hidden
      className="animate-spin"
    >
      <path d="M16 5.5A7 7 0 1 0 17 10" />
      <path d="M16 3v3h-3" />
    </svg>
  );
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
  const [activeTab, setActiveTab] = useState<DataFlowTab>(TABS[0]);
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
  const mappingDraftsReady =
    Boolean(activeDatasetDetail) &&
    activeDatasetDetail?.schema_preview.columns.every((column) => {
      const draft = mappingDrafts[column.id];
      return Boolean(draft?.approved_name.trim());
    });
  const semanticMappingsReady =
    (activeDatasetDetail?.semantic_preparation.semantic_columns.length ?? 0) > 0;
  const canGenerateSemantic =
    Boolean(activeDatasetDetail) &&
    semanticActionState === "idle" &&
    semanticStatus === "not_started";
  const canSaveMappings =
    Boolean(activeDatasetDetail) &&
    !isReadyForAnalysis &&
    semanticActionState === "idle" &&
    mappingDraftsReady;
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
  const transformationModels = dataFlow?.models ?? {};
  const hasTransformationModels = Object.keys(transformationModels).length > 0;
  const hasDimensionalEvidence = Boolean(
    transformationModels.dimensional_model?.length ||
      transformationModels.data_marts?.length ||
      isReadyForAnalysis,
  );
  const isRawRetailDemo =
    activeDatasetDetail?.dataset.name === "Raw Retail Transactions Demo" ||
    activeDatasetDetail?.dataset.source_type === "demo_raw_retail";
  const includedMappings = useMemo(
    () =>
      activeDatasetDetail?.schema_preview.columns
        .map((column) => ({
          raw: column.raw_column_name,
          field: mappingDrafts[column.id]?.approved_name ?? column.normalized_column_name,
          role: mappingDrafts[column.id]?.approved_role ?? "unknown",
          include: mappingDrafts[column.id]?.include_in_model ?? true,
        }))
        .filter((mapping) => mapping.include) ?? [],
    [activeDatasetDetail?.schema_preview.columns, mappingDrafts],
  );
  const tabAvailability = useMemo<Record<DataFlowTab, { enabled: boolean; reason: string }>>(
    () => ({
      "Schema Preview": {
        enabled: hasDataset,
        reason: "Available after a dataset is loaded.",
      },
      "Warehouse Raw": {
        enabled: Boolean(activeDatasetDetail) && semanticMappingsReady,
        reason: semanticMappingsReady
          ? "Warehouse Raw is available after schema review is saved."
          : "Save schema mappings before opening Warehouse Raw evidence.",
      },
      Transformations: {
        enabled:
          transformActionState === "running" ||
          Boolean(dataFlow?.transformation) ||
          hasTransformationModels ||
          selectedDataset?.status === "transform_failed" ||
          isReadyForAnalysis,
        reason: "Available after a transform starts, completes, or fails.",
      },
      "Dimensional Model & Data Marts": {
        enabled: hasDimensionalEvidence,
        reason: "Available after dbt records Dimensional Model or Data Mart evidence.",
      },
    }),
    [
      activeDatasetDetail,
      dataFlow?.transformation,
      hasDataset,
      hasDimensionalEvidence,
      hasTransformationModels,
      isReadyForAnalysis,
      selectedDataset?.status,
      semanticMappingsReady,
      transformActionState,
    ],
  );
  const visibleActiveTab: DataFlowTab = tabAvailability[activeTab].enabled
    ? activeTab
    : "Schema Preview";

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
            {hasDataset ? (
              <details className="group rounded-md border border-border bg-surface">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2.5 text-sm font-medium text-ink marker:hidden">
                  <span className="truncate">
                    {selectedDataset ? datasetLabel(selectedDataset) : "Select dataset"}
                  </span>
                  <svg
                    width={16}
                    height={16}
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.8}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden
                    className="text-ink-muted transition-transform group-open:rotate-180"
                  >
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                </summary>
                <div className="border-t border-border bg-surface-muted p-1.5">
                  {datasets.map((dataset) => {
                    const active = dataset.id === selectedDatasetId;
                    return (
                      <div
                        key={dataset.id}
                        className={cn(
                          "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-1 rounded-md",
                          active ? "bg-blue-50" : "bg-transparent",
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => setManualDatasetId(dataset.id)}
                          className={cn(
                            "min-w-0 cursor-pointer rounded-md px-2.5 py-2 text-left text-xs font-medium transition-colors hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                            active ? "text-blue-800" : "text-ink-soft",
                          )}
                        >
                          <span className="block truncate">{datasetLabel(dataset)}</span>
                        </button>
                        <button
                          type="button"
                          disabled={deletingDatasetId !== null}
                          onClick={(event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            void handleDeleteDataset(dataset);
                          }}
                          title="Remove dataset from active workspace. Quota usage is not restored."
                          className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-red-50 hover:text-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                          aria-label={`Remove ${datasetLabel(dataset)} from active workspace`}
                        >
                          <svg
                            width={17}
                            height={17}
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
                    );
                  })}
                </div>
              </details>
            ) : (
              <div className="rounded-md border border-border bg-surface-muted px-3 py-2.5 text-sm text-ink-muted">
                No available dataset
              </div>
            )}
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
            {TABS.map((tab) => {
              const active = tab === visibleActiveTab;
              const availability = tabAvailability[tab];
              return (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  disabled={!availability.enabled}
                  aria-selected={active}
                  onClick={() => {
                    if (availability.enabled) {
                      setActiveTab(tab);
                    }
                  }}
                  title={
                    availability.enabled ? dataFlowTabDescription(tab) : availability.reason
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
                    {visibleActiveTab}
                  </h2>
                  <p className="mt-1 text-sm text-ink-muted">
                    {dataFlowTabDescription(visibleActiveTab)}
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

                  {visibleActiveTab === "Warehouse Raw" ? (
                    <div className="mt-4 rounded-md border border-blue-200 bg-blue-50/35 px-3 py-3">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-md border border-blue-100 bg-surface px-3 py-2">
                          <p className="text-xs font-semibold text-blue-700">
                            Raw table
                          </p>
                          <p className="mt-1 break-all font-mono text-xs text-ink-soft">
                            {activeDatasetDetail.dataset.raw_table_name}
                          </p>
                        </div>
                        <div className="rounded-md border border-blue-100 bg-surface px-3 py-2">
                          <p className="text-xs font-semibold text-blue-700">
                            Load result
                          </p>
                          <p className="mt-1 font-mono text-xs text-ink-soft">
                            {activeDatasetDetail.dataset.row_count} rows /{" "}
                            {activeDatasetDetail.dataset.column_count} columns
                          </p>
                        </div>
                      </div>
                      <div className="mt-3 overflow-x-auto rounded-md border border-blue-100">
                        <table className="min-w-[720px] divide-y divide-border text-left text-sm">
                          <thead className="bg-surface-muted text-xs font-semibold text-ink-muted">
                            <tr>
                              <th className="px-3 py-2">Raw column</th>
                              <th className="px-3 py-2">Snowflake column</th>
                              <th className="px-3 py-2">Detected type</th>
                              <th className="px-3 py-2">Example values</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border bg-surface">
                            {activeDatasetDetail.schema_preview.columns.map((column) => (
                              <tr key={column.id}>
                                <td className="px-3 py-2 font-mono text-xs text-ink">
                                  {column.raw_column_name}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-ink-soft">
                                  {column.snowflake_column_name}
                                </td>
                                <td className="px-3 py-2 text-xs text-ink-soft">
                                  {column.detected_type}
                                </td>
                                <td className="max-w-[300px] px-3 py-2 font-mono text-xs text-ink-muted">
                                  {column.sample_values.length
                                    ? column.sample_values.join(", ")
                                    : "No non-null sample"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : null}

                  {visibleActiveTab === "Transformations" ? (
                    <div className="mt-4 rounded-md border border-blue-200 bg-blue-50/35 px-3 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-ink">
                          Transformation evidence
                        </p>
                        {dataFlow?.transformation ? (
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
                      <div className="mt-3 grid gap-2 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
                        <div className="rounded-md border border-blue-100 bg-surface px-3 py-2">
                          <p className="text-xs font-semibold text-blue-700">
                            Included raw columns
                          </p>
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {includedMappings.length ? (
                              includedMappings.slice(0, 18).map((mapping) => (
                                <span
                                  key={`${mapping.raw}-${mapping.field}`}
                                  className="rounded-full border border-slate-200 bg-surface-muted px-2 py-1 text-[0.6875rem] font-medium text-ink-soft"
                                >
                                  {mapping.raw} → {mapping.field}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-ink-muted">
                                No included mappings saved yet.
                              </span>
                            )}
                          </div>
                          {includedMappings.length > 18 ? (
                            <p className="mt-2 text-xs text-ink-muted">
                              +{includedMappings.length - 18} more included columns.
                            </p>
                          ) : null}
                        </div>
                        <div className="rounded-md border border-blue-100 bg-surface px-3 py-2">
                          <p className="text-xs font-semibold text-blue-700">
                            Semantic roles used
                          </p>
                          <div className="mt-2 grid gap-1.5">
                            {includedMappings.slice(0, 8).map((mapping) => (
                              <div
                                key={`${mapping.raw}-${mapping.role}`}
                                className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 text-xs"
                              >
                                <span className="truncate font-mono text-ink-soft">
                                  {mapping.field}
                                </span>
                                <span className="rounded-full bg-indigo-50 px-2 py-0.5 font-semibold text-indigo-700">
                                  {roleLabel(mapping.role)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="mt-3 rounded-md border border-blue-100 bg-surface px-3 py-2">
                        <p className="text-xs font-semibold text-blue-700">
                          Source raw table
                        </p>
                        <p className="mt-1 break-all font-mono text-xs text-ink-soft">
                          {activeDatasetDetail.dataset.raw_table_name}
                        </p>
                      </div>

                      <div className="mt-3 grid gap-2 md:grid-cols-4">
                        {["staging", "intermediate", "dimensional_model", "data_marts"].map((layer) => (
                          <div
                            key={layer}
                            className="rounded-md border border-blue-100 bg-surface px-3 py-2"
                          >
                            <p className="text-xs font-semibold uppercase tracking-normal text-blue-700">
                              {modelLayerLabel(layer)}
                            </p>
                            <p className="mt-1 font-mono text-xs leading-relaxed text-ink-soft">
                              {transformationModels[layer]?.length
                                ? transformationModels[layer].join(", ")
                                : "No models recorded yet"}
                            </p>
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-2 rounded-md border border-blue-100 bg-surface px-3 py-2 text-xs text-ink-soft">
                        <span className="font-medium">Raw selected columns</span>
                        <span className="font-semibold text-blue-500">→</span>
                        <span className="font-medium">Staging model</span>
                        <span className="font-semibold text-blue-500">→</span>
                        <span className="font-medium">Intermediate model</span>
                        <span className="font-semibold text-blue-500">→</span>
                        <span className="font-medium">Dimensional Model</span>
                        <span className="font-semibold text-blue-500">→</span>
                        <span className="font-medium">Data Marts</span>
                      </div>
                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        {dataFlow?.nodes.map((node) => (
                          <div
                            key={node.id}
                            className="flex items-center justify-between rounded-md border border-blue-100 bg-surface px-3 py-2"
                          >
                            <span className="text-xs font-medium text-ink-soft">
                              {node.label}
                            </span>
                            <span className="font-mono text-xs text-ink-muted">
                              {node.status.replaceAll("_", " ")}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {visibleActiveTab === "Dimensional Model & Data Marts" ? (
                    <div className="mt-4 rounded-md border border-blue-200 bg-blue-50/35 px-3 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-sm font-semibold text-ink">
                            Dimensional model and Data Marts
                          </p>
                          <p className="mt-1 text-xs text-ink-muted">
                            Star-schema-style dimensional model recorded from the dbt run.
                          </p>
                        </div>
                        {isReadyForAnalysis ? (
                          <StatusBadge status="ready" label="Ready for analysis" />
                        ) : (
                          <StatusBadge status="waiting" label="Not ready" />
                        )}
                      </div>

                      {isRawRetailDemo ? (
                        <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(220px,0.65fr)_minmax(0,1fr)]">
                          <div className="grid gap-2">
                            <p className="text-xs font-semibold text-blue-700">
                              Dimensions
                            </p>
                            {RAW_RETAIL_DIMENSIONS.map((dimension) => (
                              <div
                                key={dimension.name}
                                className={cn(
                                  "rounded-md border px-3 py-2",
                                  hasModel(transformationModels, dimension.name)
                                    ? "border-blue-100 bg-surface"
                                    : "border-slate-200 bg-surface-muted opacity-75",
                                )}
                              >
                                <p className="font-mono text-xs font-semibold text-ink">
                                  {dimension.name}
                                </p>
                                <p className="mt-1 text-xs text-ink-muted">
                                  Grain: {dimension.grain}
                                </p>
                                <p className="mt-1 text-xs text-ink-muted">
                                  Keys: {dimension.keys.join(", ")}
                                </p>
                                <p className="mt-1 text-xs text-ink-muted">
                                  Columns: {dimension.dimensions.join(", ")}
                                </p>
                              </div>
                            ))}
                          </div>

                          <div className="flex items-center">
                            <div className="w-full rounded-md border border-indigo-200 bg-white px-4 py-4 text-center shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
                              <p className="text-xs font-semibold uppercase tracking-normal text-indigo-700">
                                Fact table
                              </p>
                              <p className="mt-1 font-mono text-sm font-semibold text-ink">
                                fact_sales
                              </p>
                              <p className="mt-2 text-xs text-ink-muted">
                                Grain: one row per order line
                              </p>
                              <p className="mt-1 text-xs text-ink-muted">
                                Keys: order_id, order_line_id, customer_id, product_id, store_id, order_date
                              </p>
                              <p className="mt-1 text-xs text-ink-muted">
                                Metrics: quantity, revenue, cost, gross_margin
                              </p>
                            </div>
                          </div>

                          <div className="grid gap-2">
                            <p className="text-xs font-semibold text-blue-700">
                              Data Marts
                            </p>
                            {RAW_RETAIL_MARTS.map((mart) => (
                              <div
                                key={mart.name}
                                className={cn(
                                  "rounded-md border px-3 py-2",
                                  hasModel(transformationModels, mart.name)
                                    ? "border-blue-100 bg-surface"
                                    : "border-slate-200 bg-surface-muted opacity-75",
                                )}
                              >
                                <p className="font-mono text-xs font-semibold text-ink">
                                  {mart.name}
                                </p>
                                <p className="mt-1 text-xs text-ink-muted">
                                  Grain: {mart.grain}
                                </p>
                                <p className="mt-1 text-xs text-ink-muted">
                                  Metrics: {mart.metrics.join(", ")}
                                </p>
                                <p className="mt-1 text-xs text-ink-muted">
                                  Dimensions: {mart.dimensions.join(", ")}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="mt-3 grid gap-2 md:grid-cols-2">
                          {["dimensional_model", "data_marts"].map((layer) => (
                            <div
                              key={layer}
                              className="rounded-md border border-blue-100 bg-surface px-3 py-2"
                            >
                              <p className="text-xs font-semibold uppercase tracking-normal text-blue-700">
                                {modelLayerLabel(layer)}
                              </p>
                              <p className="mt-1 font-mono text-xs leading-relaxed text-ink-soft">
                                {transformationModels[layer]?.length
                                  ? transformationModels[layer].join(", ")
                                  : "No models recorded yet"}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                      {dataFlow?.artifacts.length ? (
                        <p className="mt-3 text-xs text-ink-muted">
                          {dataFlow.artifacts.length} redacted dbt artifacts are available in
                          backend evidence for this transform run.
                        </p>
                      ) : null}
                    </div>
                  ) : null}

                  {visibleActiveTab === "Schema Preview" && semanticPreparation ? (
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
                          {semanticActionState === "generating" ? (
                            <Button size="sm" disabled>
                              <InlineSpinner />
                              Generating AI Suggestions...
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

                  {visibleActiveTab === "Schema Preview" ? (
                    <>
                  <div
                    className="mt-4 max-w-full overflow-x-auto overscroll-x-contain rounded-md border border-border"
                  >
                    <table className="w-full min-w-[960px] table-fixed divide-y divide-border text-left text-sm lg:min-w-[1040px]">
                      <caption className="sr-only">
                        Schema preview mappings. Scroll horizontally on small screens to review all columns.
                      </caption>
                      <thead className="bg-surface-muted text-xs font-semibold text-ink-muted">
                        <tr>
                          <th className="sticky left-0 z-20 w-16 bg-surface-muted px-3 py-2 text-center shadow-[1px_0_0_#e2e8f0]">
                            Use
                          </th>
                          <th className="w-40 px-3 py-2">Source column</th>
                          <th className="w-28 px-3 py-2">Detected type</th>
                          <th className="w-24 px-3 py-2">Null rate</th>
                          <th className="w-52 px-3 py-2">Suggested name</th>
                          <th className="w-36 px-3 py-2">Semantic role</th>
                          <th className="w-28 px-3 py-2">Confidence</th>
                          <th className="w-32 px-3 py-2">Review</th>
                          <th className="w-56 px-3 py-2">Model field</th>
                          <th className="w-56 px-3 py-2">Example values</th>
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
                              <td className="sticky left-0 z-10 bg-inherit px-3 py-2 text-center shadow-[1px_0_0_#e2e8f0]">
                                <input
                                  type="checkbox"
                                  checked={draft?.include_in_model ?? true}
                                  disabled={isReadyForAnalysis}
                                  onChange={(event) =>
                                    updateMappingDraft(column.id, {
                                      include_in_model: event.target.checked,
                                    })
                                  }
                                  aria-label={`Use ${column.raw_column_name} in model`}
                                  className="h-4 w-4 rounded border-border text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed"
                                />
                              </td>
                              <td className="px-3 py-2">
                                <p className="break-words font-mono text-xs leading-relaxed text-ink">
                                  {column.raw_column_name}
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
                                    <p className="break-words font-mono text-xs text-ink">
                                      {semanticColumn.suggested_name}
                                    </p>
                                    <p className="mt-1 text-xs leading-relaxed text-ink-muted">
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
                                {semanticConfidenceLabel(semanticColumn)}
                              </td>
                              <td className="px-3 py-2">
                                {semanticColumn?.needs_review ? (
                                  <StatusBadge status="review" label="Needs review" />
                                ) : semanticColumn?.user_edited ? (
                                  <StatusBadge status="review" label="User edited" />
                                ) : semanticColumn ? (
                                  <StatusBadge status="ready" label="Confident" />
                                ) : (
                                  <StatusBadge status="waiting" label="Pending" />
                                )}
                              </td>
                              <td className="px-3 py-2">
                                <div className="grid gap-2">
                                  <input
                                    value={draft?.approved_name ?? ""}
                                    aria-label={`Approved name for ${column.raw_column_name}`}
                                    disabled={isReadyForAnalysis}
                                    onChange={(event) =>
                                      updateMappingDraft(column.id, {
                                        approved_name: event.target.value,
                                      })
                                    }
                                    className="w-full rounded-md border border-border bg-surface px-2.5 py-1.5 font-mono text-xs text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary"
                                  />
                                  <div className="flex items-center gap-2">
                                    <select
                                      value={draft?.approved_role ?? "unknown"}
                                      aria-label={`Approved role for ${column.raw_column_name}`}
                                      disabled={isReadyForAnalysis}
                                      onChange={(event) =>
                                        updateMappingDraft(column.id, {
                                          approved_role: event.target.value as SemanticRole,
                                        })
                                      }
                                      className="min-w-0 flex-1 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary"
                                    >
                                      {SEMANTIC_ROLE_OPTIONS.map((role) => (
                                        <option key={role} value={role}>
                                          {roleLabel(role)}
                                        </option>
                                      ))}
                                    </select>
                                  </div>
                                </div>
                              </td>
                              <td className="px-3 py-2 font-mono text-xs leading-relaxed text-ink-muted">
                                <span className="block max-h-16 overflow-y-auto whitespace-normal break-words">
                                  {column.sample_values.length > 0
                                    ? column.sample_values.join(", ")
                                    : "No non-null sample"}
                                </span>
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
                        {semanticActionState === "saving" ? <InlineSpinner /> : null}
                        {semanticActionState === "saving" ? "Saving..." : "Save mappings"}
                      </Button>
                      {isReadyForAnalysis ? (
                        <Button size="sm" href={transformNextRoute ?? "/demo/dashboard"}>
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
                          {transformActionState === "running" ? <InlineSpinner /> : null}
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
                    </>
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
