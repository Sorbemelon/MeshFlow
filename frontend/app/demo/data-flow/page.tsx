"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import { cn } from "@/lib/cn";
import {
  getDataset,
  MeshFlowApiError,
  type DatasetDetailResponse,
  type DatasetSummary,
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

function stageState(stage: string, dataset: DatasetSummary | null): "Completed" | "Not Started" {
  if (!dataset) {
    return "Not Started";
  }

  if (stage === "Raw Input" || stage === "Warehouse Raw") {
    return "Completed";
  }

  return "Not Started";
}

function formatNullRate(value: number): string {
  return `${Math.round(value * 10000) / 100}%`;
}

function DataFlowContent() {
  const searchParams = useSearchParams();
  const { sessionId, workspace } = useWorkspaceSession();
  const datasets = useMemo(() => workspace?.datasets ?? [], [workspace?.datasets]);
  const [manualDatasetId, setManualDatasetId] = useState("");
  const [datasetDetail, setDatasetDetail] = useState<DatasetDetailResponse | null>(null);
  const [detailState, setDetailState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [detailError, setDetailError] = useState<string | null>(null);
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

      try {
        const response = await getDataset(activeDatasetId, activeSessionId);
        if (cancelled) {
          return;
        }

        setDatasetDetail(response);
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
          </div>

          <div className="mt-5">
            <h3 className="mb-2 text-xs font-semibold text-ink-muted">
              Preparation status
            </h3>
            <ol className="space-y-1.5">
              {PREP_STAGES.map((stage) => {
                const state = stageState(stage, selectedDataset);
                const completed = state === "Completed";
                return (
                  <li
                    key={stage}
                    className="flex items-center gap-2.5 rounded-md border border-border bg-surface px-3 py-2"
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "h-2 w-2 shrink-0 rounded-full",
                        completed ? "bg-status-success" : "bg-status-neutral/35",
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
                      : "Transformation starts in the next phase."
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
                    Real deterministic profile from the uploaded CSV loaded into Snowflake Warehouse Raw.
                  </p>
                </div>
                <StatusBadge status="review" label="Schema review" />
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

                  <div className="mt-4 overflow-x-auto rounded-md border border-border">
                    <table className="min-w-full divide-y divide-border text-left text-sm">
                      <thead className="bg-surface-muted text-xs font-semibold text-ink-muted">
                        <tr>
                          <th className="px-3 py-2">Raw column</th>
                          <th className="px-3 py-2">Snowflake column</th>
                          <th className="px-3 py-2">Detected type</th>
                          <th className="px-3 py-2">Null rate</th>
                          <th className="px-3 py-2">Samples</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border bg-surface">
                        {activeDatasetDetail.schema_preview.columns.map((column) => (
                          <tr key={column.snowflake_column_name}>
                            <td className="px-3 py-2 font-mono text-xs text-ink">
                              {column.raw_column_name}
                            </td>
                            <td className="px-3 py-2 font-mono text-xs text-ink-soft">
                              {column.snowflake_column_name}
                            </td>
                            <td className="px-3 py-2">
                              <span className="rounded-full bg-primary-tint px-2 py-0.5 text-xs font-semibold text-primary">
                                {column.detected_type}
                              </span>
                            </td>
                            <td className="px-3 py-2 font-mono text-xs text-ink-soft">
                              {formatNullRate(column.null_rate)}
                            </td>
                            <td className="max-w-[280px] px-3 py-2 font-mono text-xs text-ink-muted">
                              {column.sample_values.length > 0
                                ? column.sample_values.join(", ")
                                : "No non-null sample"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <p className="mt-3 rounded-md border border-border bg-surface-muted px-3 py-2 text-xs text-ink-muted">
                    Transformation starts in the next phase. Staging, Intermediate,
                    Dimensional Model, and Data Marts remain Not Started.
                  </p>
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
