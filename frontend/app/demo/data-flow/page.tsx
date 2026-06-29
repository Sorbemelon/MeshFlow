"use client";

import {
  Fragment,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
  type RefObject,
} from "react";
import { useSearchParams } from "next/navigation";
import { BackendWaitNotice } from "@/components/ui/BackendWaitNotice";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge, type Status } from "@/components/ui/StatusBadge";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import { cn } from "@/lib/cn";
import { displayDatasetName } from "@/lib/datasetNames";
import {
  getDatasetDataFlow,
  getDataset,
  getSemanticPreparation,
  MeshFlowApiError,
  runSemanticPreparation,
  transformDataset,
  updateSemanticColumnMappings,
  warmBackend,
  type DataFlowNodeStatus,
  type DatasetDataFlowResponse,
  type DatasetDetailResponse,
  type DatasetModelMetadata,
  type DatasetSummary,
  type SemanticColumnSummary,
  type SemanticPreparationResponse,
  type SemanticRole,
} from "@/lib/meshflowApi";

const PREP_STAGES = [
  "Raw Input",
  "Warehouse Raw",
  "Semantic Preparation",
  "AI Modeling Plan",
  "Staging",
  "Intermediate",
  "Dimensional Model",
  "Data Marts",
] as const;

const DATA_FLOW_CACHE_TTL_MS = 120_000;
const TRANSIENT_LOADING_RETRY_MS = 1_500;

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

type DatasetDeleteNotice = {
  status: "deleting" | "deleted" | "failed";
  datasetName: string;
  message: string;
  warnings?: string[];
  errorCode?: string | null;
};

type TransformationMapping = {
  raw: string;
  field: string;
  role: SemanticRole;
  detectedType: string;
  include: boolean;
};

type TransformationFlowStep = {
  inputLabel: string;
  input: string;
  operations: string[];
  outputLabel: string;
  output: string;
  details?: string[];
};

type TransformationFlowGroup = {
  title: string;
  description: string;
  steps: TransformationFlowStep[];
};

type ConnectorLine = {
  id: string;
  points: string;
  color: string;
  strokeWidth: number;
};

type StarDimensionCard = {
  name: string;
  grain?: string;
  keys?: string[];
  dimensions?: string[];
};

type StarMartCard = {
  name: string;
  grain?: string;
  metrics?: string[];
  dimensions?: string[];
  relatedDimensions?: string[];
};

type MartDimensionLink = {
  martName: string;
  dimensionName: string;
  color: string;
};

type StageState = "Completed" | "Not Started" | "Waiting" | "Running" | "Failed";
type PrepStage = (typeof PREP_STAGES)[number];

type DataFlowCacheEntry = {
  detail: DatasetDetailResponse | null;
  dataFlow: DatasetDataFlowResponse | null;
  updatedAt: number;
};

const dataFlowCache = new Map<string, DataFlowCacheEntry>();

function dataFlowCacheKey(sessionId: string, datasetId: string): string {
  return `${sessionId}:${datasetId}`;
}

function getCachedDataFlow(sessionId: string, datasetId: string): DataFlowCacheEntry | null {
  const cached = dataFlowCache.get(dataFlowCacheKey(sessionId, datasetId));
  if (!cached) {
    return null;
  }
  if (Date.now() - cached.updatedAt > DATA_FLOW_CACHE_TTL_MS) {
    dataFlowCache.delete(dataFlowCacheKey(sessionId, datasetId));
    return null;
  }
  return cached;
}

function updateCachedDataFlow(
  sessionId: string,
  datasetId: string,
  patch: Partial<Pick<DataFlowCacheEntry, "detail" | "dataFlow">>,
) {
  const key = dataFlowCacheKey(sessionId, datasetId);
  const current = dataFlowCache.get(key) ?? {
    detail: null,
    dataFlow: null,
    updatedAt: 0,
  };
  dataFlowCache.set(key, {
    ...current,
    ...patch,
    updatedAt: Date.now(),
  });
}

function clearCachedDataFlow(sessionId: string, datasetId: string) {
  dataFlowCache.delete(dataFlowCacheKey(sessionId, datasetId));
}

function waitForTransientLoading() {
  return new Promise((resolve) => {
    window.setTimeout(resolve, TRANSIENT_LOADING_RETRY_MS);
  });
}

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

const MART_WIRE_COLORS = [
  "#2563eb",
  "#7c3aed",
  "#059669",
  "#d97706",
  "#dc2626",
  "#0891b2",
  "#be123c",
  "#4f46e5",
];

const MODEL_TOKEN_STOPWORDS = new Set([
  "dim",
  "fact",
  "mart",
  "data",
  "performance",
  "summary",
  "analysis",
  "analytics",
  "total",
]);

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
  return displayDatasetName(dataset.name, dataset.id);
}

function stageState({
  stage,
  dataset,
  dataFlow,
  transformRunning,
  semanticStatus,
  semanticMappingsReady,
  semanticRunning,
  modelMetadata,
}: {
  stage: PrepStage;
  dataset: DatasetSummary | null;
  dataFlow: DatasetDataFlowResponse | null;
  transformRunning: boolean;
  semanticStatus: DatasetDetailResponse["semantic_preparation"]["status"];
  semanticMappingsReady: boolean;
  semanticRunning: boolean;
  modelMetadata: DatasetModelMetadata | null;
}): StageState {
  if (!dataset) {
    return "Not Started";
  }

  if (stage === "Semantic Preparation") {
    if (semanticRunning || semanticStatus === "running") {
      return "Running";
    }
    if (semanticStatus === "failed") {
      return "Failed";
    }
    return semanticStatus === "completed" || semanticMappingsReady
      ? "Completed"
      : "Not Started";
  }

  if (stage === "AI Modeling Plan") {
    const hasLaterTransformEvidence = Boolean(
      dataFlow?.transformation ||
        dataFlow?.nodes.some(
          (candidate) =>
            ["Staging", "Intermediate", "Dimensional Model", "Data Marts"].includes(
              candidate.label,
            ) && candidate.status !== "not_started",
        ),
    );
    if (
      modelMetadata ||
      dataset.status === "ready_for_analysis" ||
      hasLaterTransformEvidence ||
      (transformRunning && semanticMappingsReady)
    ) {
      return "Completed";
    }
    if (dataset.status === "transform_failed") {
      return "Failed";
    }
    if (transformRunning) {
      return semanticMappingsReady ? "Running" : "Waiting";
    }
    return "Not Started";
  }

  if (dataset.status === "ready_for_analysis") {
    return "Completed";
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
    if (transformRunning) {
      return stage === "Staging" ? "Running" : "Waiting";
    }
    return "Not Started";
  }

  if (stage === "Raw Input" || stage === "Warehouse Raw") {
    return "Completed";
  }

  if (transformRunning) {
    return stage === "Staging" ? "Running" : "Waiting";
  }

  return "Not Started";
}

function statusForStageState(state: StageState): { status: Status; label: string } {
  if (state === "Completed") {
    return { status: "ready", label: "Completed" };
  }
  if (state === "Running") {
    return { status: "running", label: "Running" };
  }
  if (state === "Waiting") {
    return { status: "waiting", label: "Waiting" };
  }
  if (state === "Failed") {
    return { status: "failed", label: "Failed" };
  }
  return { status: "waiting", label: "Not Started" };
}

function formatNullRate(value: number): string {
  return `${Math.round(value * 10000) / 100}%`;
}

function roleLabel(role: SemanticRole): string {
  if (role === "identifier") {
    return "ID";
  }
  if (role === "date_time") {
    return "Date/time";
  }
  if (role === "measure_column") {
    return "Measurement";
  }
  if (role === "metric_candidate") {
    return "Metric";
  }
  if (role === "dimension") {
    return "Dimension";
  }
  return "Unknown";
}

function formatRawPreviewValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "NULL";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function warehouseRawDisplayName(datasetName: string): string {
  const normalizedName =
    displayDatasetName(datasetName)
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "DATASET";
  return normalizedName.startsWith("RAW")
    ? normalizedName
    : `RAW_${normalizedName}`;
}

function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function semanticConfidenceLabel(semanticColumn: SemanticColumnSummary | undefined): string {
  if (!semanticColumn) {
    return "N/A";
  }
  if (semanticColumn.user_edited) {
    return "Manual";
  }
  if (!semanticColumn.provider_name || semanticColumn.confidence <= 0) {
    return "N/A";
  }
  return formatConfidence(semanticColumn.confidence);
}

function semanticReviewLabel(semanticColumn: SemanticColumnSummary | undefined): string {
  if (semanticColumn?.needs_review) {
    return "Review";
  }
  if (semanticColumn?.user_edited) {
    return "Edit";
  }
  if (semanticColumn) {
    return "OK";
  }
  return "Wait";
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
  if (layer === "staging") {
    return "Staging model";
  }
  if (layer === "intermediate") {
    return "Intermediate model";
  }
  if (layer === "dimensional_model") {
    return "Dimensional Model";
  }
  if (layer === "data_marts") {
    return "Data Marts";
  }
  return layer.replaceAll("_", " ");
}

function DataFlowStatusChip({ status }: { status: DataFlowNodeStatus }) {
  return (
    <span
      className={cn(
        "min-w-0 rounded-full px-1.5 py-0.5 text-center text-[0.625rem] font-semibold leading-tight",
        status === "completed"
          ? "bg-emerald-50 text-emerald-700"
          : status === "running"
            ? "bg-blue-50 text-blue-700"
            : status === "failed"
              ? "bg-red-50 text-red-700"
              : status === "waiting"
                ? "bg-amber-50 text-amber-700"
                : "bg-slate-100 text-slate-600",
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

function ModelLayerCard({
  layer,
  models,
  className,
  contentClassName,
  status,
}: {
  layer: string;
  models?: string[];
  className?: string;
  contentClassName?: string;
  status?: DataFlowNodeStatus;
}) {
  const names = models ?? [];
  const listModels = layer === "dimensional_model" || layer === "data_marts";
  const bodyTextClass = cn(
    "mt-1 min-w-0 whitespace-normal break-all font-mono text-xs leading-relaxed text-ink-soft",
    contentClassName,
  );

  return (
    <div className={cn("flex min-h-[6rem] min-w-0 self-stretch overflow-hidden rounded-md border border-blue-100 bg-surface px-3 py-2", className)}>
      <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex min-w-0 items-start justify-between gap-2">
        <p className="min-w-0 break-words text-xs font-semibold uppercase tracking-normal text-blue-700">
          {modelLayerLabel(layer)}
        </p>
        {status ? <DataFlowStatusChip status={status} /> : null}
      </div>
      {names.length ? (
        listModels ? (
          <ul className={cn("grid gap-1", bodyTextClass)}>
            {names.map((name) => (
              <li key={name} className="min-w-0 whitespace-normal break-all">
                {name}
              </li>
            ))}
          </ul>
        ) : (
          <p className={bodyTextClass}>
            {names.join(", ")}
          </p>
        )
      ) : (
        <p className={bodyTextClass}>
          No models recorded yet
        </p>
      )}
      </div>
    </div>
  );
}

function OverviewArrow() {
  return (
    <span
      aria-hidden
      className="flex h-4 shrink-0 items-center justify-center text-blue-500 lg:h-auto lg:-mx-1"
    >
      <svg
        className="lg:hidden"
        width={20}
        height={20}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={3.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="m8 10 4 4 4-4" />
      </svg>
      <svg
        className="hidden lg:block"
        width={22}
        height={22}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={3.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="m10 8 4 4-4 4" />
      </svg>
    </span>
  );
}

function hasModel(models: Record<string, string[]>, modelName: string): boolean {
  return Object.values(models).some((names) => names.includes(modelName));
}

function modelTokens(...values: Array<string | string[] | undefined>): Set<string> {
  const text = values
    .flatMap((value) => (Array.isArray(value) ? value : value ? [value] : []))
    .join("_")
    .toLowerCase();

  return new Set(
    text
      .replace(/[^a-z0-9]+/g, "_")
      .split("_")
      .map((token) => token.trim())
      .filter((token) => token.length > 1 && !MODEL_TOKEN_STOPWORDS.has(token)),
  );
}

function hasTokenOverlap(left: Set<string>, right: Set<string>): boolean {
  for (const token of left) {
    if (right.has(token)) {
      return true;
    }
  }
  return false;
}

function matchingDimensionsForMart(
  mart: StarMartCard,
  dimensions: StarDimensionCard[],
): StarDimensionCard[] {
  if (!dimensions.length) {
    return [];
  }

  const explicitMartFields = new Set((mart.dimensions ?? []).map((field) => field.toLowerCase()));
  const explicitMatches = dimensions.filter((dimension) => {
    const dimensionFields = [
      ...(dimension.keys ?? []),
      ...(dimension.dimensions ?? []),
      dimension.name,
    ].map((field) => field.toLowerCase());
    return dimensionFields.some((field) => explicitMartFields.has(field));
  });

  if (explicitMatches.length) {
    return explicitMatches;
  }

  const martTokens = modelTokens(mart.name, mart.dimensions);
  const tokenMatches = dimensions.filter((dimension) =>
    hasTokenOverlap(martTokens, modelTokens(dimension.name, dimension.keys, dimension.dimensions)),
  );

  if (tokenMatches.length) {
    return tokenMatches;
  }

  return [];
}

function distributedAnchorY(
  rect: DOMRect,
  containerRect: DOMRect,
  index: number,
  count: number,
): number {
  if (count <= 1) {
    return rect.top + rect.height / 2 - containerRect.top;
  }

  const inset = Math.min(14, Math.max(8, rect.height * 0.2));
  const availableHeight = Math.max(1, rect.height - inset * 2);
  return rect.top + inset + availableHeight * ((index + 1) / (count + 1)) - containerRect.top;
}

function distributedLaneOffset(index: number, count: number, maxOffset: number): number {
  if (count <= 1) {
    return 0;
  }

  const centeredIndex = index - (count - 1) / 2;
  const step = Math.min(7, Math.max(3, maxOffset / Math.max(count, 1)));
  return Math.max(-maxOffset, Math.min(maxOffset, centeredIndex * step));
}

function StarSchemaWires({
  containerRef,
  factRef,
  dimensionKeys,
  dimensionRefs,
  martKeys,
  martRefs,
  martDimensionLinks,
}: {
  containerRef: RefObject<HTMLDivElement | null>;
  factRef: RefObject<HTMLDivElement | null>;
  dimensionKeys: string[];
  dimensionRefs: MutableRefObject<Record<string, HTMLDivElement | null>>;
  martKeys: string[];
  martRefs: MutableRefObject<Record<string, HTMLDivElement | null>>;
  martDimensionLinks: MartDimensionLink[];
}) {
  const [geometry, setGeometry] = useState<{
    width: number;
    height: number;
    lines: ConnectorLine[];
  }>({ width: 0, height: 0, lines: [] });

  const updateGeometry = useCallback(() => {
    const container = containerRef.current;
    const factCard = factRef.current;

    if (!container || !factCard) {
      setGeometry((current) =>
        current.lines.length ? { width: 0, height: 0, lines: [] } : current,
      );
      return;
    }

    const containerRect = container.getBoundingClientRect();
    const factRect = factCard.getBoundingClientRect();
    const factStartX = factRect.right - containerRect.left;
    const factStartY = factRect.top + factRect.height / 2 - containerRect.top;

    const factLines = dimensionKeys.flatMap((key) => {
      const dimensionCard = dimensionRefs.current[key];
      if (!dimensionCard) {
        return [];
      }

      const dimensionRect = dimensionCard.getBoundingClientRect();
      const endX = dimensionRect.left - containerRect.left;
      const endY = dimensionRect.top + dimensionRect.height / 2 - containerRect.top;
      const elbowX = factStartX + Math.max(16, (endX - factStartX) * 0.48);

      return [
        {
          id: `fact-${key}`,
          color: "#0f172a",
          strokeWidth: 0.85,
          points: [
            `${factStartX.toFixed(1)},${factStartY.toFixed(1)}`,
            `${elbowX.toFixed(1)},${factStartY.toFixed(1)}`,
            `${elbowX.toFixed(1)},${endY.toFixed(1)}`,
            `${endX.toFixed(1)},${endY.toFixed(1)}`,
          ].join(" "),
        },
      ];
    });

    const linksByDimension = new Map<string, MartDimensionLink[]>();
    martDimensionLinks.forEach((link) => {
      linksByDimension.set(link.dimensionName, [
        ...(linksByDimension.get(link.dimensionName) ?? []),
        link,
      ]);
    });

    const martLines = martDimensionLinks.flatMap((link) => {
      const martCard = martRefs.current[link.martName];
      const dimensionCard = dimensionRefs.current[link.dimensionName];
      if (!martCard || !dimensionCard) {
        return [];
      }

      const martRect = martCard.getBoundingClientRect();
      const dimensionRect = dimensionCard.getBoundingClientRect();
      const dimensionLinks = linksByDimension.get(link.dimensionName) ?? [link];
      const dimensionLinkIndex = Math.max(
        0,
        dimensionLinks.findIndex(
          (item) => item.martName === link.martName && item.color === link.color,
        ),
      );
      const startX = dimensionRect.right - containerRect.left;
      const startY = distributedAnchorY(
        dimensionRect,
        containerRect,
        dimensionLinkIndex,
        dimensionLinks.length,
      );
      const endX = martRect.left - containerRect.left;
      const endY = martRect.top + martRect.height / 2 - containerRect.top;
      const span = Math.max(16, endX - startX);
      const martLaneIndex = Math.max(0, martKeys.indexOf(link.martName));
      const elbowX =
        startX +
        span * 0.5 +
        distributedLaneOffset(martLaneIndex, Math.max(1, martKeys.length), span * 0.24);

      return [
        {
          id: `mart-${link.martName}-${link.dimensionName}`,
          color: link.color,
          strokeWidth: 1.1,
          points: [
            `${startX.toFixed(1)},${startY.toFixed(1)}`,
            `${elbowX.toFixed(1)},${startY.toFixed(1)}`,
            `${elbowX.toFixed(1)},${endY.toFixed(1)}`,
            `${endX.toFixed(1)},${endY.toFixed(1)}`,
          ].join(" "),
        },
      ];
    });

    const lines = [...factLines, ...martLines];

    const width = Math.max(1, containerRect.width);
    const height = Math.max(1, containerRect.height);
    const signature = `${width.toFixed(1)}:${height.toFixed(1)}:${lines
      .map((line) => `${line.id}:${line.color}:${line.strokeWidth}:${line.points}`)
      .join("|")}`;

    setGeometry((current) => {
      const currentSignature = `${current.width.toFixed(1)}:${current.height.toFixed(1)}:${current.lines
        .map((line) => `${line.id}:${line.color}:${line.strokeWidth}:${line.points}`)
        .join("|")}`;
      return currentSignature === signature ? current : { width, height, lines };
    });
  }, [
    containerRef,
    dimensionKeys,
    dimensionRefs,
    factRef,
    martDimensionLinks,
    martKeys,
    martRefs,
  ]);

  useEffect(() => {
    const container = containerRef.current;
    const factCard = factRef.current;
    const dimensionCards = dimensionKeys
      .map((key) => dimensionRefs.current[key])
      .filter((node): node is HTMLDivElement => Boolean(node));
    const martCards = martKeys
      .map((key) => martRefs.current[key])
      .filter((node): node is HTMLDivElement => Boolean(node));

    const frame = window.requestAnimationFrame(updateGeometry);
    window.addEventListener("resize", updateGeometry);

    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(() => updateGeometry());

    if (observer) {
      if (container) observer.observe(container);
      if (factCard) observer.observe(factCard);
      dimensionCards.forEach((card) => observer.observe(card));
      martCards.forEach((card) => observer.observe(card));
    }

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", updateGeometry);
      observer?.disconnect();
    };
  }, [
    containerRef,
    dimensionKeys,
    dimensionRefs,
    factRef,
    martKeys,
    martRefs,
    updateGeometry,
  ]);

  if (!geometry.lines.length) {
    return null;
  }

  return (
    <svg
      aria-hidden
      className="pointer-events-none absolute inset-0 z-0 hidden h-full w-full text-ink xl:block"
      preserveAspectRatio="none"
      viewBox={`0 0 ${geometry.width} ${geometry.height}`}
    >
      {geometry.lines.map((line) => (
        <polyline
          key={line.id}
          fill="none"
          points={line.points}
          stroke={line.color}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={line.strokeWidth}
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}

function typeHandlingForMapping(mapping: TransformationMapping): string {
  if (
    mapping.role === "measure_column" ||
    mapping.role === "metric_candidate" ||
    mapping.detectedType === "integer" ||
    mapping.detectedType === "decimal"
  ) {
    return "Numeric cast";
  }
  if (mapping.role === "date_time" || mapping.detectedType === "date") {
    return "Date cast";
  }
  return "Text clean";
}

function stagingOperationsForMapping(mapping: TransformationMapping): string[] {
  const operations = [typeHandlingForMapping(mapping)];
  operations.push(mapping.raw === mapping.field ? "Select column" : "Rename to model field");
  return operations;
}

function intermediateOperationsForRole(role: SemanticRole): string[] {
  if (role === "measure_column" || role === "metric_candidate") {
    return ["Prepare metric field", "Keep for analysis"];
  }
  if (role === "date_time") {
    return ["Prepare date grain", "Keep for time grouping"];
  }
  if (role === "identifier") {
    return ["Preserve key", "Keep for relationships"];
  }
  if (role === "dimension") {
    return ["Prepare dimension", "Keep for grouping"];
  }
  return ["Pass through"];
}

function mappingContextDetails(mapping: TransformationMapping): string[] {
  const role = roleLabel(mapping.role);
  const roleDetail = mapping.role === "identifier" ? `key: ${role}` : `role: ${role}`;
  return [roleDetail, `type: ${mapping.detectedType}`];
}

function roleContextDetail(role: SemanticRole): string {
  const label = roleLabel(role);
  return role === "identifier" ? `key: ${label}` : `role: ${label}`;
}

function genericModelGrain(modelName: string, layer: "dimension" | "mart"): string {
  if (layer === "dimension") {
    return modelName.startsWith("dim_")
      ? `one row per ${modelName.replace(/^dim_/, "").replaceAll("_", " ")}`
      : "dimension-level entity";
  }

  return "analysis-ready aggregate";
}

function sortCardsByName<T extends { name: string }>(cards: T[]): T[] {
  return [...cards].sort((left, right) =>
    left.name.localeCompare(right.name, undefined, { sensitivity: "base" }),
  );
}

function FlowArrow() {
  return (
    <span
      aria-hidden
      className="hidden h-full min-h-10 items-center justify-center md:flex"
    >
      <span className="relative h-6 w-full">
        <span className="absolute left-0 right-1 top-1/2 h-1 -translate-y-1/2 rounded-full bg-blue-500" />
        <span className="absolute right-0 top-1/2 h-3 w-3 -translate-y-1/2 rotate-45 rounded-[2px] border-r-[3px] border-t-[3px] border-blue-500" />
      </span>
    </span>
  );
}

function FlowCell({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "input" | "output";
}) {
  const valueItems = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const toneClasses =
    tone === "input"
      ? {
          box: "border-orange-200 bg-orange-50",
          label: "text-orange-700",
          value: "text-orange-950",
        }
      : tone === "output"
        ? {
            box: "border-emerald-200 bg-emerald-50",
            label: "text-emerald-700",
            value: "text-emerald-950",
          }
        : {
            box: "border-slate-200 bg-surface-muted",
            label: "text-ink-muted",
            value: "text-ink-soft",
          };

  return (
    <div className={cn("flex h-full min-w-0 flex-col rounded-md border px-2.5 py-1.5", toneClasses.box)}>
      <p className={cn("text-[0.625rem] font-semibold", toneClasses.label)}>{label}</p>
      {valueItems.length > 1 ? (
        <ul className={cn("mt-1 grid gap-0.5 font-mono text-[0.6875rem] leading-snug", toneClasses.value)}>
          {valueItems.map((item) => (
            <li key={`${label}-${item}`} className="break-words">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p
          className={cn("mt-1 whitespace-normal break-words font-mono text-[0.6875rem] leading-snug", toneClasses.value)}
          title={value}
        >
          {value}
        </p>
      )}
    </div>
  );
}

function FlowMetaCard({ details }: { details?: string[] }) {
  if (!details?.length) {
    return <div className="hidden md:block" />;
  }

  return (
    <div className="flex h-full min-w-0 flex-col rounded-md bg-blue-50 px-2 py-1.5">
      <p className="text-[0.625rem] font-semibold text-blue-700">Context</p>
      <div className="mt-1 grid gap-0.5">
        {details.map((detail) => (
          <p
            key={detail}
            className="whitespace-normal break-words text-[0.625rem] font-medium leading-snug text-blue-900"
            title={detail}
          >
            {detail}
          </p>
        ))}
      </div>
    </div>
  );
}

function ProcessCell({ operations }: { operations: string[] }) {
  return (
    <div className="flex h-full min-w-0 flex-col rounded-md border border-violet-200 bg-violet-50/70 px-2 py-1.5">
      <p className="text-[0.625rem] font-semibold text-violet-700">Operation</p>
      <ol className="mt-1 grid gap-0.5">
        {operations.map((operation, index) => (
          <li
            key={`${operation}-${index}`}
            className="grid grid-cols-[1rem_minmax(0,1fr)] gap-1 text-[0.6875rem] leading-tight text-violet-900"
          >
            <span className="font-mono text-violet-500">{index + 1}</span>
            <span className="whitespace-normal break-words" title={operation}>
              {operation}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function TransformationFlowGroupCard({
  group,
  defaultOpen = false,
}: {
  group: TransformationFlowGroup;
  defaultOpen?: boolean;
}) {
  return (
    <details
      open={defaultOpen}
      className="group overflow-hidden rounded-md border border-blue-100 bg-surface"
    >
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 border-b border-blue-100 bg-blue-50/35 px-2.5 py-2 marker:hidden">
        <span>
          <span className="block text-xs font-semibold text-blue-700">
            {group.title}
          </span>
          <span className="mt-1 block text-xs text-ink-muted">
            {group.description}
          </span>
        </span>
        <span
          aria-hidden
          className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-blue-700 transition-transform duration-150 group-open:rotate-180"
        >
          <svg
            width={14}
            height={14}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </span>
      </summary>
      <div className="grid gap-1.5 p-2">
        {group.steps.length ? (
          group.steps.map((step) => (
            <div
              key={`${group.title}-${step.input}-${step.output}`}
              className="grid gap-1.5 rounded-md bg-white px-1.5 py-1.5 md:grid-cols-[minmax(7rem,0.7fr)_minmax(12rem,1.35fr)_1.5rem_minmax(12rem,1.15fr)_1.5rem_minmax(10rem,1fr)] md:items-stretch"
            >
              <FlowMetaCard details={step.details} />
              <FlowCell label={step.inputLabel} value={step.input} tone="input" />
              <FlowArrow />
              <ProcessCell operations={step.operations} />
              <FlowArrow />
              <FlowCell
                label={step.outputLabel}
                value={step.input === step.output ? "Same as input" : step.output}
                tone="output"
              />
            </div>
          ))
        ) : (
          <p className="px-3 py-3 text-xs text-ink-muted">
            No transformation evidence recorded yet.
          </p>
        )}
      </div>
    </details>
  );
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
  const {
    activeProcessLabel,
    datasetDeleteOperation,
    isAnyProcessRunning,
    refresh,
    sessionId,
    startDatasetDelete,
    workspace,
  } = useWorkspaceSession();
  const deletedDatasetIds = useMemo(() => {
    const ids = new Set<string>();
    if (
      datasetDeleteOperation?.status === "deleting" ||
      datasetDeleteOperation?.status === "deleted"
    ) {
      ids.add(datasetDeleteOperation.datasetId);
    }
    return ids;
  }, [datasetDeleteOperation]);
  const datasets = useMemo(
    () =>
      (workspace?.datasets ?? []).filter((dataset) => !deletedDatasetIds.has(dataset.id)),
    [deletedDatasetIds, workspace?.datasets],
  );
  const [manualDatasetId, setManualDatasetId] = useState("");
  const [datasetDetail, setDatasetDetail] = useState<DatasetDetailResponse | null>(null);
  const [dataFlow, setDataFlow] = useState<DatasetDataFlowResponse | null>(null);
  const [dataFlowState, setDataFlowState] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [dataFlowError, setDataFlowError] = useState<string | null>(null);
  const [detailState, setDetailState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [detailError, setDetailError] = useState<string | null>(null);
  const [semanticActionState, setSemanticActionState] = useState<
    "idle" | "generating" | "saving"
  >("idle");
  const [semanticActionDatasetId, setSemanticActionDatasetId] = useState<string | null>(null);
  const [semanticActionMessage, setSemanticActionMessage] = useState<string | null>(null);
  const [transformActionState, setTransformActionState] = useState<"idle" | "running">("idle");
  const [transformActionDatasetId, setTransformActionDatasetId] = useState<string | null>(null);
  const [transformMessage, setTransformMessage] = useState<string | null>(null);
  const [transformNextRoute, setTransformNextRoute] = useState<string | null>(null);
  const deletingDatasetId =
    datasetDeleteOperation?.status === "deleting" ? datasetDeleteOperation.datasetId : null;
  const deleteNotice: DatasetDeleteNotice | null = datasetDeleteOperation
    ? {
        status: datasetDeleteOperation.status,
        datasetName: displayDatasetName(
          datasetDeleteOperation.datasetName,
          datasetDeleteOperation.datasetId,
        ),
        message: datasetDeleteOperation.message,
        warnings: datasetDeleteOperation.response?.cleanup.warnings,
        errorCode: datasetDeleteOperation.error?.error_code ?? null,
      }
    : null;
  const [mappingDrafts, setMappingDrafts] = useState<Record<string, MappingDraft>>({});
  const [activeTab, setActiveTab] = useState<DataFlowTab>(TABS[0]);
  const dataFlowRequestRef = useRef(0);
  const transformRequestRef = useRef(0);
  const semanticAutoRequestRef = useRef<string | null>(null);
  const selectedDatasetIdRef = useRef("");
  const refreshWorkspaceRef = useRef(refresh);
  const statusRailRef = useRef<HTMLOListElement | null>(null);
  const starDiagramRef = useRef<HTMLDivElement | null>(null);
  const factCardRef = useRef<HTMLDivElement | null>(null);
  const dimensionCardRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const martCardRefs = useRef<Record<string, HTMLDivElement | null>>({});
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
  const activeSemanticActionState =
    semanticActionDatasetId === selectedDatasetId ? semanticActionState : "idle";
  const activeSemanticActionMessage =
    semanticActionDatasetId === selectedDatasetId ? semanticActionMessage : null;
  const activeTransformActionState =
    transformActionDatasetId === selectedDatasetId ? transformActionState : "idle";
  const activeTransformNextRoute =
    transformActionDatasetId === selectedDatasetId ? transformNextRoute : null;

  useEffect(() => {
    selectedDatasetIdRef.current = selectedDatasetId;
  }, [selectedDatasetId]);

  useEffect(() => {
    refreshWorkspaceRef.current = refresh;
  }, [refresh]);

  const activeDatasetDetail =
    datasetDetail?.dataset.id === selectedDatasetId ? datasetDetail : null;
  const activeDataFlow = dataFlow?.dataset.id === selectedDatasetId ? dataFlow : null;
  const selectedDataset =
    activeDatasetDetail?.dataset ??
    datasets.find((dataset) => dataset.id === selectedDatasetId) ??
    null;
  const hasDataset = datasets.length > 0;
  const semanticPreparation = activeDatasetDetail?.semantic_preparation ?? null;
  const semanticStatus = semanticPreparation?.status ?? "not_started";
  const activeSemanticGenerating =
    activeSemanticActionState === "generating" || semanticStatus === "running";
  const activeSemanticBusy =
    activeSemanticActionState !== "idle" || activeSemanticGenerating;
  const backendTransformRunning =
    selectedDataset?.status === "transforming" ||
    activeDataFlow?.transformation?.status === "running";
  const activeTransformRunning =
    activeTransformActionState === "running" || backendTransformRunning;
  const activeTransformMessage =
    transformActionDatasetId === selectedDatasetId
      ? transformMessage
      : backendTransformRunning
        ? "dbt transformation is still running. MeshFlow is polling warehouse/dbt evidence."
        : null;
  const dataFlowProcessRunning =
    isAnyProcessRunning || activeSemanticBusy || activeTransformRunning;
  const dataFlowProcessLabel =
    activeSemanticBusy
      ? activeSemanticActionState === "saving"
        ? "Saving schema mappings"
        : "Generating semantic preparation"
      : activeTransformRunning
        ? "Transforming dataset"
        : activeProcessLabel;
  const isReadyForAnalysis = selectedDataset?.status === "ready_for_analysis";
  const selectedDatasetIsDeleting =
    Boolean(deletingDatasetId) && deletingDatasetId === selectedDatasetId;
  const mappingDraftsReady =
    Boolean(activeDatasetDetail) &&
    activeDatasetDetail?.schema_preview.columns.every((column) => {
      const draft = mappingDrafts[column.id];
      return Boolean(draft?.approved_name.trim());
    });
  const semanticMappingsReady =
    (activeDatasetDetail?.semantic_preparation.semantic_columns.length ?? 0) > 0;
  const canSaveMappings =
    Boolean(activeDatasetDetail) &&
    !isReadyForAnalysis &&
    !selectedDatasetIsDeleting &&
    !dataFlowProcessRunning &&
    mappingDraftsReady;
  const canTransform =
    Boolean(activeDatasetDetail) &&
    semanticMappingsReady &&
    !isReadyForAnalysis &&
    !selectedDatasetIsDeleting &&
    !dataFlowProcessRunning;
  const semanticByProfileId = useMemo(() => {
    const pairs =
      activeDatasetDetail?.semantic_preparation.semantic_columns.map(
        (semanticColumn) => [semanticColumn.column_profile_id, semanticColumn] as const,
      ) ?? [];
    return new Map<string, SemanticColumnSummary>(pairs);
  }, [activeDatasetDetail?.semantic_preparation.semantic_columns]);
  const transformationModels = useMemo(
    () => activeDataFlow?.models ?? {},
    [activeDataFlow?.models],
  );
  const modelMetadata: DatasetModelMetadata | null = activeDataFlow?.model_metadata ?? null;
  const semanticStageState = stageState({
    stage: "Semantic Preparation",
    dataset: selectedDataset,
    dataFlow: activeDataFlow,
    transformRunning: activeTransformRunning,
    semanticStatus,
    semanticMappingsReady,
    semanticRunning: activeSemanticGenerating,
    modelMetadata,
  });
  const dataFlowStatusByNodeType = useMemo(
    () =>
      new Map(
        (activeDataFlow?.nodes ?? []).map((node) => [node.node_type, node.status] as const),
      ),
    [activeDataFlow?.nodes],
  );
  const hasTransformationModels = Object.keys(transformationModels).length > 0;
  const hasDimensionalEvidence = Boolean(
    transformationModels.dimensional_model?.length ||
      transformationModels.data_marts?.length ||
      isReadyForAnalysis,
  );
  const isRawRetailDemo =
    activeDatasetDetail?.dataset.name === "Raw Retail Transactions Demo" ||
    activeDatasetDetail?.dataset.source_type === "demo_raw_retail";
  const starFactName = useMemo(() => {
    if (modelMetadata?.fact.name) {
      return modelMetadata.fact.name;
    }
    if (isRawRetailDemo) {
      return "fact_sales";
    }

    return (
      transformationModels.dimensional_model?.find((model) => model.startsWith("fact_")) ??
      transformationModels.dimensional_model?.[0] ??
      "Dimensional model"
    );
  }, [isRawRetailDemo, modelMetadata, transformationModels.dimensional_model]);
  const starFactGrain =
    modelMetadata?.fact.grain ?? (isRawRetailDemo ? "one row per order line" : "modeled fact output");
  const starFactKeys =
    modelMetadata?.fact.keys ??
    (isRawRetailDemo
      ? ["order_id", "order_line_id", "customer_id", "product_id", "store_id", "order_date"]
      : []);
  const starFactMetrics =
    modelMetadata?.fact.metrics ??
    (isRawRetailDemo ? ["quantity", "revenue", "cost", "gross_margin"] : []);
  const starDimensions = useMemo<StarDimensionCard[]>(() => {
    if (modelMetadata?.dimensions.length) {
      return sortCardsByName(
        modelMetadata.dimensions.map((dimension) => ({
          name: dimension.name,
          grain: dimension.grain,
          keys: [dimension.key_column],
          dimensions: dimension.columns.filter((column) => column !== dimension.key_column),
        })),
      );
    }
    if (isRawRetailDemo) {
      return sortCardsByName(RAW_RETAIL_DIMENSIONS);
    }

    const models = transformationModels.dimensional_model ?? [];
    const dimensionModels = models.filter((model) => model !== starFactName);

    return sortCardsByName(
      dimensionModels.map((model) => ({
        name: model,
        grain: genericModelGrain(model, "dimension"),
      })),
    );
  }, [isRawRetailDemo, modelMetadata, starFactName, transformationModels.dimensional_model]);
  const starDimensionKeys = useMemo(
    () => starDimensions.map((dimension) => dimension.name),
    [starDimensions],
  );
  const starMarts = useMemo<StarMartCard[]>(() => {
    if (modelMetadata?.marts.length) {
      return sortCardsByName(
        modelMetadata.marts.map((mart) => ({
          name: mart.name,
          grain: mart.grain,
          metrics: mart.metrics,
          dimensions: mart.dimensions,
          relatedDimensions: mart.related_dimensions,
        })),
      );
    }
    if (isRawRetailDemo) {
      return sortCardsByName(RAW_RETAIL_MARTS);
    }

    return sortCardsByName(
      (transformationModels.data_marts ?? []).map((model) => ({
        name: model,
        grain: genericModelGrain(model, "mart"),
      })),
    );
  }, [isRawRetailDemo, modelMetadata, transformationModels.data_marts]);
  const starMartKeys = useMemo(() => starMarts.map((mart) => mart.name), [starMarts]);
  const starMartDimensionLinks = useMemo<MartDimensionLink[]>(
    () => {
      if (modelMetadata?.relationships.length) {
        const martIndexByName = new Map(
          starMarts.map((mart, index) => [mart.name, index] as const),
        );
        const dimensionNames = new Set(starDimensions.map((dimension) => dimension.name));
        const metadataLinks = modelMetadata.relationships
          .filter(
            (relationship) =>
              relationship.relationship_type === "mart_to_dimension" &&
              martIndexByName.has(relationship.from_model) &&
              dimensionNames.has(relationship.to_model),
          )
          .map((relationship) => {
            const martIndex = martIndexByName.get(relationship.from_model) ?? 0;
            return {
              martName: relationship.from_model,
              dimensionName: relationship.to_model,
              color: MART_WIRE_COLORS[martIndex % MART_WIRE_COLORS.length],
            };
          });
        if (metadataLinks.length) {
          return metadataLinks;
        }
      }

      return starMarts.flatMap((mart, martIndex) => {
        const matchedDimensions = matchingDimensionsForMart(mart, starDimensions);
        const fallbackDimension =
          starDimensions.length > 0
            ? starDimensions[martIndex % starDimensions.length]
            : undefined;
        const targetDimensions = matchedDimensions.length
          ? matchedDimensions
          : fallbackDimension
            ? [fallbackDimension]
            : [];

        return targetDimensions.map((dimension) => ({
          martName: mart.name,
          dimensionName: dimension.name,
          color: MART_WIRE_COLORS[martIndex % MART_WIRE_COLORS.length],
        }));
      });
    },
    [modelMetadata, starDimensions, starMarts],
  );
  useEffect(() => {
    const nextKeys = new Set(starDimensionKeys);
    Object.keys(dimensionCardRefs.current).forEach((key) => {
      if (!nextKeys.has(key)) {
        delete dimensionCardRefs.current[key];
      }
    });
  }, [starDimensionKeys]);
  useEffect(() => {
    const nextKeys = new Set(starMartKeys);
    Object.keys(martCardRefs.current).forEach((key) => {
      if (!nextKeys.has(key)) {
        delete martCardRefs.current[key];
      }
    });
  }, [starMartKeys]);
  const includedMappings = useMemo(
    () =>
      activeDatasetDetail?.schema_preview.columns
        .map((column) => ({
          raw: column.raw_column_name,
          field: mappingDrafts[column.id]?.approved_name ?? column.normalized_column_name,
          role: (mappingDrafts[column.id]?.approved_role ?? "unknown") as SemanticRole,
          detectedType: column.detected_type,
          include: mappingDrafts[column.id]?.include_in_model ?? true,
        }))
        .filter((mapping) => mapping.include) ?? [],
    [activeDatasetDetail?.schema_preview.columns, mappingDrafts],
  );
  const transformationFlowGroups = useMemo<TransformationFlowGroup[]>(() => {
    const stagingModels = transformationModels.staging ?? [];
    const intermediateModels = transformationModels.intermediate ?? [];
    const dimensionalModels = transformationModels.dimensional_model ?? [];
    const martModels = transformationModels.data_marts ?? [];

    const stagingSteps = includedMappings.map((mapping) => ({
      inputLabel: "Raw column",
      input: mapping.raw,
      operations: stagingOperationsForMapping(mapping),
      outputLabel: "Staging field",
      output: mapping.field,
      details: mappingContextDetails(mapping),
    }));

    const intermediateSteps = includedMappings.map((mapping) => ({
      inputLabel: "Staging field",
      input: mapping.field,
      operations: intermediateOperationsForRole(mapping.role),
      outputLabel: "Intermediate field",
      output: mapping.field,
      details: [roleContextDetail(mapping.role)],
    }));

    const dimensionalSteps = modelMetadata
      ? [
          {
            inputLabel: "Prepared fields",
            input: [
              ...modelMetadata.fact.keys,
              ...modelMetadata.fact.degenerate_dimensions,
              ...modelMetadata.fact.date_columns,
              ...modelMetadata.fact.metrics,
            ].join(", "),
            operations: [
              "Keep validated fact grain",
              "Select relationship keys",
              "Materialize fact table",
            ],
            outputLabel: "Fact table",
            output: modelMetadata.fact.name,
            details: [
              `grain: ${modelMetadata.fact.grain}`,
              `keys: ${modelMetadata.fact.keys.join(", ") || "not recorded"}`,
              `metrics: ${modelMetadata.fact.metrics.join(", ") || "not recorded"}`,
            ],
          },
          ...modelMetadata.dimensions.map((dimension) => ({
            inputLabel: "Prepared fields",
            input: dimension.columns.join(", "),
            operations: [
              "Select key and attributes",
              "Deduplicate entity rows",
              "Materialize dimension",
            ],
            outputLabel: "Dimension table",
            output: dimension.name,
            details: [`grain: ${dimension.grain}`, `key: ${dimension.key_column}`],
          })),
        ]
      : isRawRetailDemo
      ? [
          {
            inputLabel: "Prepared fields",
            input: "order line grain, keys, revenue, cost, quantity",
            operations: [
              "Separate relationship keys",
              "Keep order-line grain",
              "Calculate margin metrics",
            ],
            outputLabel: "Fact table",
            output: "fact_sales",
            details: [
              "grain: one row per order line",
              "keys: customer, product, store, date",
              "metrics: revenue, cost, margin",
            ],
          },
          ...RAW_RETAIL_DIMENSIONS.map((dimension) => ({
            inputLabel: "Prepared fields",
            input: [...dimension.keys, ...dimension.dimensions].join(", "),
            operations: [
              "Select descriptive attributes",
              "Deduplicate rows",
              "Preserve dimension key",
            ],
            outputLabel: "Dimension table",
            output: dimension.name,
            details: [`grain: ${dimension.grain}`, `keys: ${dimension.keys.join(", ")}`],
          })),
        ]
      : (dimensionalModels.length ? dimensionalModels : ["No dimensional models recorded"]).map(
          (model) => ({
            inputLabel: "Prepared mappings",
            input: `${includedMappings.length} included fields`,
            operations:
              model === "No dimensional models recorded"
                ? ["Wait for dbt transformation evidence"]
                : ["Validate model shape", "Materialize dimensional model"],
            outputLabel: "Dimensional output",
            output: model,
          }),
        );

    const martSteps = modelMetadata?.marts.length
      ? modelMetadata.marts.map((mart) => ({
          inputLabel: "Dimensional input",
          input: [
            modelMetadata.fact.name,
            ...(mart.related_dimensions.length ? mart.related_dimensions : []),
          ].join(", "),
          operations: [
            mart.related_dimensions.length
              ? `Join dimensions: ${mart.related_dimensions.join(", ")}`
              : "Use fact-level grouping fields",
            `Group by: ${mart.dimensions.join(", ")}`,
            `Aggregate metrics: ${mart.metrics.join(", ")}`,
          ],
          outputLabel: "Data Mart",
          output: mart.name,
          details: [`grain: ${mart.grain}`, `dimensions: ${mart.dimensions.join(", ")}`],
        }))
      : isRawRetailDemo
      ? RAW_RETAIL_MARTS.map((mart) => ({
          inputLabel: "Dimensional input",
          input: "fact_sales and dimensions",
          operations: [
            "Join fact and dimensions",
            `Aggregate metrics: ${mart.metrics.join(", ")}`,
            "Set analysis grain",
          ],
          outputLabel: "Data Mart",
          output: mart.name,
          details: [`grain: ${mart.grain}`, `dimensions: ${mart.dimensions.join(", ")}`],
        }))
      : (martModels.length ? martModels : ["No marts recorded"]).map((model) => ({
          inputLabel: "Dimensional input",
          input: dimensionalModels.join(", ") || "Dimensional model",
          operations:
            model === "No marts recorded"
              ? ["Wait for dbt transformation evidence"]
              : ["Select analysis fields", "Expose mart for questions"],
          outputLabel: "Data Mart",
          output: model,
        }));

    return [
      {
        title: "Staging transformation",
        description: `Builds ${stagingModels.join(", ") || "the staging model"} from selected raw columns.`,
        steps: stagingSteps,
      },
      {
        title: "Intermediate transformation",
        description: `Builds ${intermediateModels.join(", ") || "the intermediate model"} for cleaning, casting, and enrichment.`,
        steps: intermediateSteps,
      },
      {
        title: "Dimensional model transformation",
        description: "Splits prepared fields into fact and dimension outputs.",
        steps: dimensionalSteps,
      },
      {
        title: "Data Mart transformation",
        description: "Shows how dimensional outputs become analysis-ready mart evidence.",
        steps: martSteps,
      },
    ];
  }, [includedMappings, isRawRetailDemo, modelMetadata, transformationModels]);
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
          activeTransformRunning ||
          Boolean(activeDataFlow?.transformation) ||
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
      activeDataFlow?.transformation,
      hasDataset,
      hasDimensionalEvidence,
      hasTransformationModels,
      isReadyForAnalysis,
      selectedDataset?.status,
      semanticMappingsReady,
      activeTransformRunning,
    ],
  );
  const visibleActiveTab: DataFlowTab = tabAvailability[activeTab].enabled
    ? activeTab
    : "Schema Preview";
  const datasetStatusBadge =
    activeTransformRunning
      ? { status: "running" as const, label: "Transforming" }
      : isReadyForAnalysis
        ? { status: "ready" as const, label: "Ready for analysis" }
        : selectedDataset?.status === "transform_failed"
          ? { status: "failed" as const, label: "Transform failed" }
          : { status: "review" as const, label: "Schema review" };
  const statusRailNeedsDataFlow = Boolean(
    selectedDataset &&
      (activeTransformRunning ||
        selectedDataset.status === "transforming" ||
        selectedDataset.status === "ready_for_analysis" ||
        selectedDataset.status === "transform_failed"),
  );
  const visibleTabNeedsDataFlow =
    visibleActiveTab !== "Schema Preview" || statusRailNeedsDataFlow;

  const loadDataFlowForDataset = useCallback(
    async (
      datasetId: string,
      activeSessionId: string,
      options: { refreshing?: boolean; force?: boolean } = {},
    ) => {
      const cached =
        !options.refreshing && !options.force
          ? getCachedDataFlow(activeSessionId, datasetId)
          : null;
      if (cached?.dataFlow) {
        setDataFlow(cached.dataFlow);
        setDataFlowState("ready");
        setDataFlowError(null);
        return cached.dataFlow;
      }

      const requestId = dataFlowRequestRef.current + 1;
      dataFlowRequestRef.current = requestId;
      if (!options.refreshing) {
        setDataFlowState("loading");
      }
      setDataFlowError(null);

      try {
        if (!options.refreshing) {
          await warmBackend();
        }
        let flowResponse: DatasetDataFlowResponse;
        try {
          flowResponse = await getDatasetDataFlow(datasetId, activeSessionId);
        } catch (firstError) {
          if (options.refreshing) {
            throw firstError;
          }
          await waitForTransientLoading();
          flowResponse = await getDatasetDataFlow(datasetId, activeSessionId);
        }
        if (
          dataFlowRequestRef.current !== requestId ||
          selectedDatasetIdRef.current !== datasetId
        ) {
          return null;
        }

        setDataFlow(flowResponse);
        setDataFlowState("ready");
        updateCachedDataFlow(activeSessionId, datasetId, { dataFlow: flowResponse });
        return flowResponse;
      } catch (caught) {
        if (
          dataFlowRequestRef.current !== requestId ||
          selectedDatasetIdRef.current !== datasetId
        ) {
          return null;
        }

        if (options.refreshing) {
          return null;
        }

        setDataFlowState("error");
        setDataFlowError(
          caught instanceof MeshFlowApiError
            ? caught.details.message
            : "Data Flow evidence could not be loaded.",
        );
        return null;
      }
    },
    [],
  );

  const applySemanticPreparationResponse = useCallback(
    (response: SemanticPreparationResponse, datasetId: string) => {
      setSemanticActionDatasetId(datasetId);
      setDatasetDetail((current) => {
        if (!current || current.dataset.id !== datasetId) {
          return current;
        }
        const nextDetail = {
          ...current,
          semantic_preparation: response,
        };
        setMappingDrafts(buildMappingDrafts(nextDetail));
        if (sessionId) {
          updateCachedDataFlow(sessionId, datasetId, { detail: nextDetail });
        }
        return nextDetail;
      });
      setSemanticActionMessage(response.message);
      if (response.status !== "running") {
        setSemanticActionState("idle");
      }
    },
    [sessionId],
  );

  useEffect(() => {
    if (!sessionId || !selectedDatasetId) {
      const timeoutId = window.setTimeout(() => {
        setDatasetDetail(null);
        setDataFlow(null);
        setDataFlowState("idle");
        setDataFlowError(null);
        setDetailState("idle");
        setDetailError(null);
      }, 0);
      return () => window.clearTimeout(timeoutId);
    }

    let cancelled = false;
    const activeSessionId = sessionId;
    const activeDatasetId = selectedDatasetId;

    async function loadDatasetDetail() {
      await Promise.resolve();
      if (cancelled) {
        return;
      }

      const cached = getCachedDataFlow(activeSessionId, activeDatasetId);
      if (cached?.detail) {
        setDatasetDetail(cached.detail);
        setMappingDrafts(buildMappingDrafts(cached.detail));
        setActiveTab(
          cached.detail.dataset.status === "ready_for_analysis"
            ? "Dimensional Model & Data Marts"
            : "Schema Preview",
        );
        setDetailState("ready");
        setDetailError(null);
      }
      if (cached?.dataFlow) {
        setDataFlow(cached.dataFlow);
        setDataFlowState("ready");
        setDataFlowError(null);
      }
      if (
        cached?.detail &&
        cached.detail.semantic_preparation.status !== "running" &&
        cached.detail.dataset.status !== "transforming" &&
        selectedDataset?.status !== "transforming"
      ) {
        return;
      }

      if (!cached?.detail) {
        setDetailState("loading");
      }
      setDetailError(null);
      if (!cached?.dataFlow) {
        dataFlowRequestRef.current += 1;
        setDataFlow(null);
        setDataFlowState("idle");
        setDataFlowError(null);
      }
      setTransformMessage(null);
      setTransformNextRoute(null);

      try {
        let response: DatasetDetailResponse;
        try {
          response = await getDataset(activeDatasetId, activeSessionId);
        } catch {
          await waitForTransientLoading();
          response = await getDataset(activeDatasetId, activeSessionId);
        }
        if (cancelled) {
          return;
        }

        setDatasetDetail(response);
        setMappingDrafts(buildMappingDrafts(response));
        updateCachedDataFlow(activeSessionId, activeDatasetId, { detail: response });
        setActiveTab(
          response.dataset.status === "ready_for_analysis"
            ? "Dimensional Model & Data Marts"
            : "Schema Preview",
        );
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
  }, [selectedDataset?.status, selectedDatasetId, sessionId]);

  useEffect(() => {
    if (
      !sessionId ||
      !selectedDatasetId ||
      !activeDatasetDetail ||
      !visibleTabNeedsDataFlow ||
      activeDataFlow ||
      dataFlowState !== "idle"
    ) {
      return;
    }

    let cancelled = false;
    async function loadVisibleTabDataFlow() {
      await Promise.resolve();
      if (cancelled || !sessionId || !selectedDatasetId) {
        return;
      }
      await loadDataFlowForDataset(selectedDatasetId, sessionId);
    }

    void loadVisibleTabDataFlow();

    return () => {
      cancelled = true;
    };
  }, [
    activeDataFlow,
    activeDatasetDetail,
    dataFlowState,
    loadDataFlowForDataset,
    selectedDatasetId,
    sessionId,
    visibleTabNeedsDataFlow,
  ]);

  useEffect(() => {
    if (!sessionId || !selectedDatasetId || !activeTransformRunning) {
      return;
    }

    let cancelled = false;
    let inFlight = false;
    const pollDatasetId = selectedDatasetId;
    const pollSessionId = sessionId;

    async function pollTransformProgress() {
      if (inFlight) {
        return;
      }
      inFlight = true;
      try {
        const flowResponse = await loadDataFlowForDataset(pollDatasetId, pollSessionId, {
          refreshing: true,
        });
        const transformationStatus = flowResponse?.transformation?.status ?? null;
        if (cancelled) {
          return;
        }

        if (transformationStatus === "running") {
          setTransformActionDatasetId(pollDatasetId);
          setTransformActionState("running");
          setTransformMessage(
            "dbt transformation is still running. MeshFlow is polling warehouse/dbt evidence.",
          );
          return;
        }

        if (transformationStatus === "completed" || transformationStatus === "failed") {
          const nextDetail = await getDataset(pollDatasetId, pollSessionId);
          if (cancelled || selectedDatasetIdRef.current !== pollDatasetId) {
            return;
          }

          setDatasetDetail(nextDetail);
          setMappingDrafts(buildMappingDrafts(nextDetail));
          updateCachedDataFlow(pollSessionId, pollDatasetId, { detail: nextDetail });
          setTransformActionDatasetId(pollDatasetId);
          setTransformActionState("idle");
          setTransformMessage(
            transformationStatus === "completed"
              ? "dbt transformation completed. Data Marts are ready for later analysis."
              : flowResponse?.transformation?.error_message ??
                  "dbt transformation failed. Review the failed step, then retry.",
          );
          if (transformationStatus === "completed") {
            setActiveTab("Dimensional Model & Data Marts");
          }
          void refreshWorkspaceRef.current();
        }
      } finally {
        inFlight = false;
      }
    }

    void pollTransformProgress();
    const intervalId = window.setInterval(() => {
      if (!cancelled) {
        void pollTransformProgress();
      }
    }, 1500);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [activeTransformRunning, loadDataFlowForDataset, selectedDatasetId, sessionId]);

  useEffect(() => {
    if (
      !sessionId ||
      !selectedDatasetId ||
      !activeDatasetDetail ||
      isAnyProcessRunning ||
      selectedDatasetIsDeleting ||
      isReadyForAnalysis ||
      semanticStatus !== "not_started" ||
      activeSemanticActionState !== "idle"
    ) {
      return;
    }

    const requestKey = selectedDatasetId;
    if (semanticAutoRequestRef.current === requestKey) {
      return;
    }
    semanticAutoRequestRef.current = requestKey;

    let cancelled = false;
    async function autoGenerateSemanticPreparation() {
      await Promise.resolve();
      if (
        cancelled ||
        !sessionId ||
        !selectedDatasetId ||
        !activeDatasetDetail ||
        selectedDatasetIsDeleting
      ) {
        return;
      }

      setSemanticActionDatasetId(selectedDatasetId);
      setSemanticActionState("generating");
      setSemanticActionMessage("Generating AI mapping suggestions automatically.");
      let startedRunning = false;

      try {
        const response = await runSemanticPreparation(selectedDatasetId, sessionId, false);
        if (cancelled || activeDatasetDetail.dataset.id !== selectedDatasetId) {
          return;
        }

        startedRunning = response.status === "running";
        applySemanticPreparationResponse(response, selectedDatasetId);
      } catch (caught) {
        if (cancelled) {
          return;
        }

        setSemanticActionMessage(
          caught instanceof MeshFlowApiError
            ? caught.details.message
            : "Semantic preparation could not reach the backend.",
        );
      } finally {
        if (!cancelled && !startedRunning) {
          setSemanticActionState("idle");
        }
      }
    }

    void autoGenerateSemanticPreparation();

    return () => {
      cancelled = true;
    };
  }, [
    activeDatasetDetail,
    activeSemanticActionState,
    applySemanticPreparationResponse,
    isAnyProcessRunning,
    isReadyForAnalysis,
    selectedDatasetId,
    selectedDatasetIsDeleting,
    semanticStatus,
    sessionId,
  ]);

  useEffect(() => {
    if (
      !sessionId ||
      !selectedDatasetId ||
      !activeDatasetDetail ||
      semanticStatus !== "running"
    ) {
      return;
    }

    let cancelled = false;
    let inFlight = false;
    const pollDatasetId = selectedDatasetId;
    const pollSessionId = sessionId;

    async function pollSemanticPreparation() {
      if (inFlight) {
        return;
      }
      inFlight = true;
      try {
        const response = await getSemanticPreparation(pollDatasetId, pollSessionId);
        if (cancelled) {
          return;
        }
        applySemanticPreparationResponse(response, pollDatasetId);
        if (response.status === "running") {
          setSemanticActionDatasetId(pollDatasetId);
          setSemanticActionState("generating");
        }
      } catch (caught) {
        if (cancelled) {
          return;
        }
        setSemanticActionMessage(
          caught instanceof MeshFlowApiError
            ? caught.details.message
            : "Semantic preparation status could not be refreshed.",
        );
        setSemanticActionDatasetId(pollDatasetId);
      } finally {
        inFlight = false;
      }
    }

    void pollSemanticPreparation();
    const intervalId = window.setInterval(() => {
      void pollSemanticPreparation();
    }, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [
    activeDatasetDetail,
    applySemanticPreparationResponse,
    selectedDatasetId,
    semanticStatus,
    sessionId,
  ]);

  useEffect(() => {
    if (
      !sessionId ||
      !selectedDatasetId ||
      !activeDatasetDetail ||
      semanticStatus === "running" ||
      activeSemanticActionState !== "generating"
    ) {
      return;
    }

    let cancelled = false;
    const pollDatasetId = selectedDatasetId;
    const pollSessionId = sessionId;

    const timeoutId = window.setTimeout(() => {
      async function confirmSemanticPreparationStatus() {
        try {
          const response = await getSemanticPreparation(pollDatasetId, pollSessionId);
          if (cancelled) {
            return;
          }
          applySemanticPreparationResponse(response, pollDatasetId);
        } catch (caught) {
          if (cancelled) {
            return;
          }
          setSemanticActionMessage(
            caught instanceof MeshFlowApiError
              ? caught.details.message
              : "Semantic preparation status could not be refreshed.",
          );
          setSemanticActionDatasetId(pollDatasetId);
        }
      }

      void confirmSemanticPreparationStatus();
    }, 2000);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [
    activeDatasetDetail,
    activeSemanticActionState,
    applySemanticPreparationResponse,
    selectedDatasetId,
    semanticStatus,
    sessionId,
  ]);

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

  async function handleRetrySemanticPreparation() {
    if (
      !sessionId ||
      !selectedDatasetId ||
      !activeDatasetDetail ||
      selectedDatasetIsDeleting ||
      dataFlowProcessRunning
    ) {
      return;
    }

    semanticAutoRequestRef.current = selectedDatasetId;
    setSemanticActionDatasetId(selectedDatasetId);
    setSemanticActionState("generating");
    setSemanticActionMessage("Retrying AI mapping suggestions.");
    try {
      const response = await runSemanticPreparation(selectedDatasetId, sessionId, true);
      applySemanticPreparationResponse(response, selectedDatasetId);
      if (response.status === "running") {
        setSemanticActionState("generating");
      }
    } catch (caught) {
      setSemanticActionMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "Semantic preparation could not reach the backend.",
      );
      setSemanticActionDatasetId(selectedDatasetId);
      setSemanticActionState("idle");
    }
  }

  async function handleSaveMappings() {
    if (
      !sessionId ||
      !selectedDatasetId ||
      !activeDatasetDetail ||
      selectedDatasetIsDeleting ||
      !canSaveMappings
    ) {
      return;
    }

    setSemanticActionDatasetId(selectedDatasetId);
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
        updateCachedDataFlow(sessionId, selectedDatasetId, { detail: nextDetail });
      }
      setSemanticActionMessage("Schema mappings saved for dbt transformation.");
    } catch (caught) {
      setSemanticActionMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "Schema mappings could not be saved.",
      );
      setSemanticActionDatasetId(selectedDatasetId);
    } finally {
      setSemanticActionState("idle");
    }
  }

  async function handleTransform() {
    if (!sessionId || !selectedDatasetId || !activeDatasetDetail || !canTransform) {
      return;
    }

    const transformDatasetId = selectedDatasetId;
    const transformSessionId = sessionId;
    const requestId = transformRequestRef.current + 1;
    transformRequestRef.current = requestId;
    setTransformActionDatasetId(transformDatasetId);
    setTransformActionState("running");
    setTransformMessage(null);
    setTransformNextRoute(null);
    window.requestAnimationFrame(() => {
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    });

    try {
      const response = await transformDataset(transformDatasetId, transformSessionId);
      const [nextDetail] = await Promise.all([
        getDataset(transformDatasetId, transformSessionId),
        refresh(),
      ]);
      if (transformRequestRef.current !== requestId) {
        return;
      }

      if (selectedDatasetIdRef.current === transformDatasetId) {
        setDatasetDetail(nextDetail);
        setMappingDrafts(buildMappingDrafts(nextDetail));
        updateCachedDataFlow(transformSessionId, transformDatasetId, {
          detail: nextDetail,
        });
        setActiveTab("Dimensional Model & Data Marts");
        void loadDataFlowForDataset(transformDatasetId, transformSessionId, {
          force: true,
        });
      }
      setTransformActionDatasetId(transformDatasetId);
      setTransformNextRoute(response.next_route);
      setTransformMessage("dbt transformation completed. Data Marts are ready for later analysis.");
    } catch (caught) {
      if (transformRequestRef.current !== requestId) {
        return;
      }

      setTransformActionDatasetId(transformDatasetId);
      setTransformMessage(
        caught instanceof MeshFlowApiError
          ? `${caught.details.message}${
              caught.details.next_action ? ` ${caught.details.next_action}` : ""
            }`
          : "dbt transformation could not reach the backend.",
      );
    } finally {
      if (transformRequestRef.current === requestId) {
        setTransformActionState("idle");
      }
    }
  }

  async function handleDeleteDataset(dataset: DatasetSummary) {
    if (!sessionId || dataFlowProcessRunning) {
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

    const response = await startDatasetDelete(dataset);
    if (response) {
      clearCachedDataFlow(sessionId, dataset.id);
      setManualDatasetId((current) => (current === dataset.id ? "" : current));
      if (selectedDatasetId === dataset.id) {
        setDatasetDetail(null);
        setDataFlow(null);
        setDataFlowState("idle");
        setDataFlowError(null);
        setDetailState("idle");
      }
      void refresh();
    } else {
      setManualDatasetId((current) => (current === dataset.id ? "" : current));
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
                          disabled={dataFlowProcessRunning}
                          onClick={() => setManualDatasetId(dataset.id)}
                          className={cn(
                            "min-w-0 cursor-pointer rounded-md px-2.5 py-2 text-left text-xs font-medium transition-colors hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-60",
                            active ? "text-blue-800" : "text-ink-soft",
                          )}
                          title={
                            dataFlowProcessRunning
                              ? `Wait for the current process to finish: ${dataFlowProcessLabel}.`
                              : undefined
                          }
                        >
                          <span className="block truncate">{datasetLabel(dataset)}</span>
                        </button>
                        <button
                          type="button"
                          disabled={dataFlowProcessRunning}
                          onClick={(event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            void handleDeleteDataset(dataset);
                          }}
                          title={
                            deletingDatasetId === dataset.id
                              ? "Removing dataset..."
                              : dataFlowProcessRunning
                                ? `Wait for the current process to finish: ${dataFlowProcessLabel}.`
                              : "Remove dataset from active workspace. Quota usage is not restored."
                          }
                          className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-red-50 hover:text-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                          aria-label={
                            deletingDatasetId === dataset.id
                              ? `Removing ${datasetLabel(dataset)} from active workspace`
                              : `Remove ${datasetLabel(dataset)} from active workspace`
                          }
                        >
                          {deletingDatasetId === dataset.id ? (
                            <InlineSpinner />
                          ) : (
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
                          )}
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
            {deleteNotice ? (
              <div
                className={cn(
                  "mt-3 rounded-md border px-3 py-2.5 text-xs leading-relaxed",
                  deleteNotice.status === "deleted"
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : deleteNotice.status === "failed"
                      ? "border-red-200 bg-red-50 text-red-800"
                      : "border-blue-200 bg-blue-50 text-blue-800",
                )}
                role={deleteNotice.status === "failed" ? "alert" : "status"}
                aria-live={deleteNotice.status === "failed" ? "assertive" : "polite"}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge
                    status={
                      deleteNotice.status === "deleted"
                        ? "ready"
                        : deleteNotice.status === "failed"
                          ? "failed"
                          : "running"
                    }
                    label={
                      deleteNotice.status === "deleted"
                        ? "Removed"
                        : deleteNotice.status === "failed"
                          ? "Delete failed"
                          : "Removing"
                    }
                  />
                  <span className="font-medium text-current">
                    {deleteNotice.datasetName}
                  </span>
                  {deleteNotice.errorCode ? (
                    <span className="rounded-full bg-red-100 px-2 py-0.5 font-mono text-[0.6875rem] font-semibold text-red-700">
                      {deleteNotice.errorCode}
                    </span>
                  ) : null}
                </div>
                <p className="mt-1.5">{deleteNotice.message}</p>
              </div>
            ) : null}
          </div>

          <div className="mt-5">
            <h3 className="mb-2 text-xs font-semibold text-ink-muted">
              Preparation Status
            </h3>
            <ol ref={statusRailRef} className="scroll-mt-4 space-y-1.5">
              {PREP_STAGES.map((stage) => {
                const state = stageState({
                  stage,
                  dataset: selectedDataset,
                  dataFlow: activeDataFlow,
                  transformRunning: activeTransformRunning,
                  semanticStatus,
                  semanticMappingsReady,
                  semanticRunning: activeSemanticGenerating,
                  modelMetadata,
                });
                const badge = statusForStageState(state);
                const completed = state === "Completed";
                const running = state === "Running";
                const failed = state === "Failed";
                const activelyWaiting =
                  state === "Waiting" && activeTransformRunning;
                return (
                  <li
                    key={stage}
                    className="flex items-center gap-2.5 rounded-md border border-border bg-surface px-3 py-2"
                  >
                    {running || activelyWaiting ? (
                      <span
                        aria-hidden
                        className="flex h-3.5 w-3.5 shrink-0 items-center justify-center text-status-running"
                      >
                        <InlineSpinner />
                      </span>
                    ) : (
                      <span
                        aria-hidden
                        className={cn(
                          "h-2 w-2 shrink-0 rounded-full",
                          completed
                            ? "bg-status-success"
                            : failed
                              ? "bg-status-danger"
                              : "bg-status-neutral/35",
                        )}
                      />
                    )}
                    <span className="whitespace-nowrap text-sm text-ink-soft">
                      {stage}
                    </span>
                    <StatusBadge
                      status={badge.status}
                      label={badge.label}
                      showIcon={false}
                      className="ml-auto"
                    />
                  </li>
                );
              })}
            </ol>
            {selectedDataset ? (
              <div className="mt-3 flex items-center justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2">
                <span className="text-sm font-medium text-ink-soft">
                  Dataset status
                </span>
                <StatusBadge
                  status={datasetStatusBadge.status}
                  label={datasetStatusBadge.label}
                />
              </div>
            ) : null}
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
                  disabled={!availability.enabled || dataFlowProcessRunning}
                  aria-selected={active}
                  onClick={() => {
                    if (availability.enabled && !dataFlowProcessRunning) {
                      setActiveTab(tab);
                    }
                  }}
                  title={
                    dataFlowProcessRunning
                      ? `Wait for the current process to finish: ${dataFlowProcessLabel}.`
                      : availability.enabled
                        ? dataFlowTabDescription(tab)
                        : availability.reason
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
              </div>

              {detailState === "loading" ? (
                <BackendWaitNotice active context="data_flow" className="mt-4" />
              ) : null}

              {detailState === "error" ? (
                <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {detailError}
                </div>
              ) : null}

              {activeDatasetDetail ? (
                <>
                  {visibleActiveTab === "Schema Preview" ? (
                    <div className="mt-4 grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)]">
                      <div className="rounded-md border border-border bg-surface-muted px-3 py-2 lg:min-h-[6.25rem]">
                        <p className="text-xs font-medium text-ink-muted">Raw data</p>
                        <div className="mt-2 grid grid-cols-2 gap-2">
                          <div>
                            <p className="text-[0.6875rem] text-ink-muted">Rows</p>
                            <p className="font-mono text-sm text-ink">
                              {activeDatasetDetail.dataset.row_count}
                            </p>
                          </div>
                          <div>
                            <p className="text-[0.6875rem] text-ink-muted">Columns</p>
                            <p className="font-mono text-sm text-ink">
                              {activeDatasetDetail.dataset.column_count}
                            </p>
                          </div>
                        </div>
                      </div>
                      {semanticPreparation ? (
                        <div
                          className={cn(
                            "rounded-md border px-3 py-3",
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
                                  status={statusForStageState(semanticStageState).status}
                                  label={statusForStageState(semanticStageState).label}
                                />
                              </div>
                              <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                                {activeSemanticActionMessage ?? semanticPreparation.message}
                              </p>
                              {semanticPreparation.next_action ? (
                                <p className="mt-1 text-xs text-ink-muted">
                                  {semanticPreparation.next_action}
                                </p>
                              ) : null}
                            </div>

                            <div className="flex min-w-[11rem] justify-start lg:justify-end">
                              {activeSemanticGenerating ? (
                                <span className="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-xs font-medium text-blue-800">
                                  <InlineSpinner />
                                  Generating suggestions...
                                </span>
                              ) : semanticStatus === "not_started" ? (
                                <span className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-ink-muted">
                                  Starts automatically after upload.
                                </span>
                              ) : semanticStatus === "failed" ? (
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs text-red-700">
                                    Edit mappings manually or retry.
                                  </span>
                                  <Button
                                    size="sm"
                                    variant="secondary"
                                    disabled={dataFlowProcessRunning}
                                    onClick={() => void handleRetrySemanticPreparation()}
                                    title={
                                      selectedDatasetIsDeleting
                                        ? "Wait until dataset removal finishes before retrying semantic preparation."
                                        : dataFlowProcessRunning
                                          ? `Wait for the current process to finish: ${dataFlowProcessLabel}.`
                                        : "Retry the async AI provider ladder. No fallback suggestions are invented."
                                    }
                                  >
                                    Retry
                                  </Button>
                                </div>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  {visibleActiveTab === "Warehouse Raw" ? (
                    <div className="mt-4 rounded-md border border-blue-200 bg-blue-50/35 px-3 py-3">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-md border border-blue-100 bg-surface px-3 py-2">
                          <p className="text-xs font-semibold text-blue-700">
                            Raw table
                          </p>
                          <p
                            className="mt-1 break-all font-mono text-xs text-ink-soft"
                            title={activeDatasetDetail.dataset.raw_table_name}
                          >
                            {warehouseRawDisplayName(activeDatasetDetail.dataset.name)}
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
                      <div className="mt-3">
                        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                          <p className="text-xs font-semibold text-blue-700">
                            First 10 raw rows
                          </p>
                          {activeDataFlow?.raw_preview ? (
                            <span className="font-mono text-[0.6875rem] text-ink-muted">
                              {activeDataFlow.raw_preview.status === "completed"
                                ? `${activeDataFlow.raw_preview.row_count_previewed} previewed`
                                : activeDataFlow.raw_preview.status.replaceAll("_", " ")}
                            </span>
                          ) : null}
                        </div>
                        {dataFlowState === "loading" && !activeDataFlow ? (
                          <BackendWaitNotice
                            active
                            context="data_flow"
                            className="text-xs"
                          />
                        ) : dataFlowState === "error" && !activeDataFlow ? (
                          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                            {dataFlowError ?? "Warehouse Raw preview could not be loaded."}
                          </div>
                        ) : activeDataFlow?.raw_preview?.status === "completed" &&
                        activeDataFlow.raw_preview.rows.length > 0 ? (
                          <div className="max-w-full overflow-x-auto overscroll-x-contain rounded-md border border-border">
                            <table className="min-w-max divide-y divide-border text-left text-xs">
                              <caption className="sr-only">
                                First 10 rows from the Snowflake Warehouse Raw table.
                              </caption>
                              <thead className="bg-surface-muted text-xs font-semibold text-ink-muted">
                                <tr>
                                  {activeDataFlow.raw_preview.columns.map((columnName) => (
                                    <th
                                      key={columnName}
                                      className="whitespace-nowrap px-2 py-2"
                                    >
                                      {columnName}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-border bg-surface">
                                {activeDataFlow.raw_preview.rows.map((row, rowIndex) => (
                                  <tr key={`raw-preview-row-${rowIndex}`}>
                                    {activeDataFlow.raw_preview.columns.map((columnName) => {
                                      const value = row[columnName];
                                      const formatted = formatRawPreviewValue(value);
                                      return (
                                        <td
                                          key={`${rowIndex}-${columnName}`}
                                          className={cn(
                                            "max-w-40 truncate whitespace-nowrap px-2 py-2 font-mono text-[0.6875rem] leading-tight",
                                            value === null || value === undefined
                                              ? "text-ink-muted"
                                              : "text-ink-soft",
                                          )}
                                          title={formatted}
                                        >
                                          {formatted}
                                        </td>
                                      );
                                    })}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs text-ink-muted">
                            {activeDataFlow?.raw_preview?.message ??
                              "Raw row preview is not available yet."}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : null}

                  {visibleActiveTab === "Transformations" ? (
                    <>
                    <div className="mt-4 rounded-md border border-blue-200 bg-blue-50/35 px-3 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-sm font-semibold text-ink">
                            Transformation overview
                          </p>
                          <p className="mt-1 text-xs text-ink-muted">
                            Scan the source table, dbt model layers, and current status for this dataset.
                          </p>
                        </div>
                        {activeDataFlow?.transformation ? (
                          <StatusBadge
                            status={
                              activeDataFlow.transformation.status === "completed"
                                ? "ready"
                                : activeDataFlow.transformation.status === "failed"
                                  ? "failed"
                                  : "running"
                            }
                            label={activeDataFlow.transformation.status.replaceAll("_", " ")}
                          />
                        ) : null}
                      </div>
                      {dataFlowState === "loading" && !activeDataFlow ? (
                        <BackendWaitNotice
                          active
                          context="data_flow"
                          className="mt-3 text-xs"
                        />
                      ) : null}
                      {dataFlowState === "error" && !activeDataFlow ? (
                        <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                          {dataFlowError ?? "Transformation evidence could not be loaded."}
                        </div>
                      ) : null}
                      <div className="mt-3 flex min-w-0 flex-col gap-0.5 lg:flex-row lg:items-stretch">
                        <div className="flex min-h-[6rem] min-w-0 self-stretch overflow-hidden rounded-md border border-blue-100 bg-surface px-3 py-2 lg:flex-1">
                          <div className="flex min-w-0 flex-1 flex-col">
                            <div className="flex min-w-0 items-start justify-between gap-2">
                              <p className="min-w-0 break-words text-xs font-semibold text-blue-700">
                                Source raw table
                              </p>
                              {dataFlowStatusByNodeType.get("warehouse_raw") ? (
                                <DataFlowStatusChip
                                  status={dataFlowStatusByNodeType.get("warehouse_raw")!}
                                />
                              ) : null}
                            </div>
                            <p
                              className="mt-1 min-w-0 whitespace-normal break-all font-mono text-[0.6875rem] leading-snug text-ink-soft"
                              title={activeDatasetDetail.dataset.raw_table_name}
                            >
                              {warehouseRawDisplayName(activeDatasetDetail.dataset.name)}
                            </p>
                          </div>
                        </div>
                        {["staging", "intermediate", "dimensional_model", "data_marts"].map((layer) => (
                          <Fragment key={layer}>
                            <OverviewArrow />
                            <ModelLayerCard
                              layer={layer}
                              models={transformationModels[layer]}
                              className="lg:flex-1"
                              contentClassName="text-[0.6875rem] leading-snug"
                              status={dataFlowStatusByNodeType.get(
                                layer === "data_marts" ? "data_mart" : layer,
                              )}
                            />
                          </Fragment>
                        ))}
                      </div>
                    </div>

                    <div className="mt-4 rounded-md border border-blue-200 bg-blue-50/35 px-3 py-3">
                      <div className="flex flex-wrap items-end justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold text-ink">
                              Transformation evidence
                            </p>
                            <p className="mt-1 text-xs text-ink-muted">
                              Inspect how selected inputs move through each dbt operation into modeled outputs.
                            </p>
                          </div>
                        </div>
                        <div className="mt-3 grid gap-3">
                          {transformationFlowGroups.map((group) => (
                            <TransformationFlowGroupCard
                              key={group.title}
                              group={group}
                              defaultOpen={group.title === "Data Mart transformation"}
                            />
                          ))}
                        </div>
                      </div>
                    </>
                  ) : null}

                  {visibleActiveTab === "Dimensional Model & Data Marts" ? (
                    <div className="mt-4 rounded-md border border-blue-200 bg-blue-50/35 px-3 py-3">
                      <div
                        ref={starDiagramRef}
                        className="relative grid gap-3 xl:grid-cols-[19rem_18rem_minmax(19rem,1fr)] xl:gap-6"
                      >
                        <StarSchemaWires
                          containerRef={starDiagramRef}
                          dimensionKeys={starDimensionKeys}
                          dimensionRefs={dimensionCardRefs}
                          factRef={factCardRef}
                          martDimensionLinks={starMartDimensionLinks}
                          martKeys={starMartKeys}
                          martRefs={martCardRefs}
                        />
                        <div className="relative z-10 grid w-[19rem] justify-items-stretch gap-2">
                          <p className="w-full max-w-[18rem] text-center text-sm font-semibold text-indigo-700">
                            Fact table
                          </p>
                          <div
                            ref={factCardRef}
                            className="w-full max-w-[18rem] self-start rounded-md border border-indigo-200 bg-white px-3 py-2 text-left shadow-[0_1px_2px_rgba(15,23,42,0.04)]"
                          >
                            <p className="mt-1 break-words font-mono text-sm font-semibold text-ink">
                              {starFactName}
                            </p>
                            <p className="mt-2 text-xs text-ink">
                              <span className="font-semibold">Grain:</span> {starFactGrain}
                            </p>
                            {starFactKeys.length || starFactMetrics.length ? (
                              <>
                                {starFactKeys.length ? (
                                  <p className="mt-1 text-xs text-ink">
                                    <span className="font-semibold">Keys:</span>{" "}
                                    {starFactKeys.join(", ")}
                                  </p>
                                ) : null}
                                {starFactMetrics.length ? (
                                  <p className="mt-1 text-xs text-ink">
                                    <span className="font-semibold">Metrics:</span>{" "}
                                    {starFactMetrics.join(", ")}
                                  </p>
                                ) : null}
                              </>
                            ) : (
                              <p className="mt-1 text-xs text-ink">
                                <span className="font-semibold">Source:</span> backend-owned dimensional model
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="relative z-10 grid w-[18rem] justify-items-stretch gap-2">
                          <p className="w-full text-center text-sm font-semibold text-blue-700">
                            Dimensions
                          </p>
                          {starDimensions.length ? (
                            starDimensions.map((dimension) => (
                              <div key={dimension.name} className="w-full">
                                <div
                                  ref={(node) => {
                                    dimensionCardRefs.current[dimension.name] = node;
                                  }}
                                  className={cn(
                                    "w-full rounded-md border px-3 py-2",
                                    hasModel(transformationModels, dimension.name)
                                      ? "border-blue-100 bg-surface"
                                      : "border-slate-200 bg-surface-muted opacity-75",
                                  )}
                                >
                                  <p className="break-words font-mono text-xs font-semibold text-ink">
                                    {dimension.name}
                                  </p>
                                  {dimension.grain ? (
                                    <p className="mt-1 text-xs text-ink">
                                      <span className="font-semibold">Grain:</span>{" "}
                                      {dimension.grain}
                                    </p>
                                  ) : null}
                                  {dimension.keys?.length ? (
                                    <p className="mt-1 text-xs text-ink">
                                      <span className="font-semibold">Keys:</span>{" "}
                                      {dimension.keys.join(", ")}
                                    </p>
                                  ) : null}
                                  {dimension.dimensions?.length ? (
                                    <p className="mt-1 text-xs text-ink">
                                      <span className="font-semibold">Columns:</span>{" "}
                                      {dimension.dimensions.join(", ")}
                                    </p>
                                  ) : null}
                                </div>
                              </div>
                            ))
                          ) : (
                            <div className="w-full rounded-md border border-slate-200 bg-surface-muted px-3 py-2 text-xs text-ink-muted">
                              No separate dimension tables recorded for this dataset yet.
                            </div>
                          )}
                        </div>

                        <div className="relative z-10 grid justify-items-end gap-2">
                          <p className="w-full max-w-[19rem] text-center text-sm font-semibold text-emerald-600">
                            Data Marts
                          </p>
                          {starMarts.length ? (
                            starMarts.map((mart) => (
                              <div
                                key={mart.name}
                                ref={(node) => {
                                  martCardRefs.current[mart.name] = node;
                                }}
                                className={cn(
                                  "w-full max-w-[19rem] rounded-md border px-3 py-2",
                                  hasModel(transformationModels, mart.name)
                                    ? "border-blue-100 bg-surface"
                                    : "border-slate-200 bg-surface-muted opacity-75",
                                )}
                              >
                                <p className="break-words font-mono text-xs font-semibold text-ink">
                                  {mart.name}
                                </p>
                                {mart.grain ? (
                                  <p className="mt-1 text-xs text-ink">
                                    <span className="font-semibold">Grain:</span>{" "}
                                    {mart.grain}
                                  </p>
                                ) : null}
                                {mart.metrics?.length ? (
                                  <p className="mt-1 text-xs text-ink">
                                    <span className="font-semibold">Metrics:</span>{" "}
                                    {mart.metrics.join(", ")}
                                  </p>
                                ) : null}
                                {mart.dimensions?.length ? (
                                  <p className="mt-1 text-xs text-ink">
                                    <span className="font-semibold">Dimensions:</span>{" "}
                                    {mart.dimensions.join(", ")}
                                  </p>
                                ) : null}
                              </div>
                            ))
                          ) : (
                            <div className="w-full max-w-[19rem] rounded-md border border-slate-200 bg-surface-muted px-3 py-2 text-xs text-ink-muted">
                              No Data Mart outputs recorded for this dataset yet.
                            </div>
                          )}
                        </div>
                      </div>
                      {dataFlowState === "loading" && !activeDataFlow ? (
                        <BackendWaitNotice
                          active
                          context="data_flow"
                          className="mt-3 text-xs"
                        />
                      ) : null}
                      {dataFlowState === "error" && !activeDataFlow ? (
                        <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                          {dataFlowError ?? "Dimensional Model and Data Mart evidence could not be loaded."}
                        </div>
                      ) : null}
                      {activeDataFlow?.artifacts.length ? (
                        <p className="mt-3 text-xs text-ink-muted">
                          {activeDataFlow.artifacts.length} redacted dbt artifacts are available in
                          backend evidence for this transform run.
                        </p>
                      ) : null}
                      {isReadyForAnalysis ? (
                        <div className="mt-3 flex justify-end">
                          {selectedDatasetIsDeleting || dataFlowProcessRunning ? (
                            <Button
                              type="button"
                              size="sm"
                              disabled
                              title={
                                selectedDatasetIsDeleting
                                  ? "Wait until dataset removal finishes before opening Dashboard for this dataset."
                                  : `Wait for the current process to finish: ${dataFlowProcessLabel}.`
                              }
                            >
                              Open Dashboard
                            </Button>
                          ) : (
                            <Button size="sm" href={activeTransformNextRoute ?? "/demo/dashboard"}>
                              Open Dashboard
                            </Button>
                          )}
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  {visibleActiveTab === "Schema Preview" ? (
                    <>
                  <div
                    className="mt-4 max-w-full overflow-x-auto overscroll-x-contain rounded-md border border-border"
                  >
                    <table className="w-full min-w-[820px] table-fixed divide-y divide-border text-left text-xs lg:min-w-0">
                      <colgroup>
                        <col className="w-[3.5%]" />
                        <col className="w-[13%]" />
                        <col className="w-[7.5%]" />
                        <col className="w-[3.5%]" />
                        <col className="w-[19%]" />
                        <col className="w-[10.5%]" />
                        <col className="w-[5.5%]" />
                        <col className="w-[6%]" />
                        <col className="w-[21%]" />
                        <col className="w-[10.5%]" />
                      </colgroup>
                      <caption className="sr-only">
                        Schema preview mappings. Scroll horizontally on small screens to review all columns.
                      </caption>
                      <thead className="bg-surface-muted text-xs font-semibold text-ink-muted">
                        <tr>
                          <th className="sticky left-0 z-20 bg-surface-muted px-1 py-2 text-center text-[0.6875rem] shadow-[1px_0_0_#e2e8f0]">
                            Use
                          </th>
                          <th className="px-2 py-2">Source</th>
                          <th className="px-1.5 py-2">
                            Type
                          </th>
                          <th className="px-1 py-2 text-center">Null</th>
                          <th className="px-2 py-2">Suggested</th>
                          <th className="px-1.5 py-2">
                            Role
                          </th>
                          <th className="px-1 py-2 text-center">Score</th>
                          <th className="px-1 py-2 text-center">Review</th>
                          <th className="px-2 py-2">Model field</th>
                          <th className="px-2 py-2">Sample values</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border bg-surface">
                        {activeDatasetDetail.schema_preview.columns.map((column) => {
                          const semanticColumn = semanticByProfileId.get(column.id);
                          const draft = mappingDrafts[column.id];
                          const roleText = semanticColumn
                            ? roleLabel(semanticColumn.semantic_role)
                            : "";
                          return (
                            <tr
                              key={column.id}
                              className={cn(
                                semanticColumn?.needs_review ? "bg-amber-50/35" : "",
                              )}
                            >
                              <td className="sticky left-0 z-10 bg-inherit px-1 py-2 text-center shadow-[1px_0_0_#e2e8f0]">
                                <input
                                  type="checkbox"
                                  checked={draft?.include_in_model ?? true}
                                  disabled={
                                    isReadyForAnalysis ||
                                    selectedDatasetIsDeleting ||
                                    dataFlowProcessRunning
                                  }
                                  onChange={(event) =>
                                    updateMappingDraft(column.id, {
                                      include_in_model: event.target.checked,
                                    })
                                  }
                                  aria-label={`Use ${column.raw_column_name} in model`}
                                  className="h-4 w-4 rounded border-border text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed"
                                />
                              </td>
                              <td className="px-2 py-2">
                                <p className="break-words font-mono text-[0.6875rem] leading-tight text-ink">
                                  {column.raw_column_name}
                                </p>
                              </td>
                              <td className="px-1.5 py-2">
                                <span
                                  className="inline-flex max-w-full min-w-0 overflow-hidden rounded-full bg-primary-tint px-1.5 py-0.5 text-[0.6875rem] font-semibold leading-tight text-primary"
                                  title={column.detected_type}
                                >
                                  <span className="min-w-0 truncate">
                                    {column.detected_type}
                                  </span>
                                </span>
                              </td>
                              <td className="px-1 py-2 text-center font-mono text-[0.6875rem] text-ink-soft">
                                {formatNullRate(column.null_rate)}
                              </td>
                              <td className="px-2 py-2">
                                {semanticColumn ? (
                                  <div>
                                    <p className="break-words font-mono text-[0.6875rem] leading-tight text-ink">
                                      {semanticColumn.suggested_name}
                                    </p>
                                    <p className="mt-1 line-clamp-2 text-[0.6875rem] leading-tight text-ink-muted">
                                      {semanticColumn.reason}
                                    </p>
                                  </div>
                                ) : (
                                  <span className="text-[0.6875rem] text-ink-muted">
                                    Not generated
                                  </span>
                                )}
                              </td>
                              <td className="px-1.5 py-2">
                                {semanticColumn ? (
                                  <span
                                    className="inline-flex max-w-full min-w-0 overflow-hidden rounded-full bg-blue-50 px-1.5 py-0.5 text-[0.6875rem] font-semibold leading-tight text-blue-700"
                                    title={roleText}
                                  >
                                    <span className="min-w-0 truncate">
                                      {roleText}
                                    </span>
                                  </span>
                                ) : (
                                  <span className="text-[0.6875rem] text-ink-muted">Unknown</span>
                                )}
                              </td>
                              <td className="px-1 py-2 text-center font-mono text-[0.6875rem] leading-tight text-ink-soft">
                                {semanticConfidenceLabel(semanticColumn)}
                              </td>
                              <td className="px-1 py-2 text-center">
                                <span
                                  className={cn(
                                    "inline-flex rounded-full border px-1.5 py-0.5 text-[0.625rem] font-semibold leading-tight",
                                    semanticColumn?.needs_review || semanticColumn?.user_edited
                                      ? "border-amber-200 bg-amber-50 text-amber-700"
                                      : semanticColumn
                                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                        : "border-slate-200 bg-slate-100 text-slate-600",
                                  )}
                                >
                                  {semanticReviewLabel(semanticColumn)}
                                </span>
                              </td>
                              <td className="px-2 py-2">
                                <div className="grid gap-1.5">
                                  <input
                                    value={draft?.approved_name ?? ""}
                                    aria-label={`Approved name for ${column.raw_column_name}`}
                                    disabled={
                                      isReadyForAnalysis ||
                                      selectedDatasetIsDeleting ||
                                      dataFlowProcessRunning
                                    }
                                    onChange={(event) =>
                                      updateMappingDraft(column.id, {
                                        approved_name: event.target.value,
                                      })
                                    }
                                    className={cn(
                                      "w-full rounded-md border px-2 py-1.5 font-mono text-[0.6875rem] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary",
                                      isReadyForAnalysis ||
                                        selectedDatasetIsDeleting ||
                                        dataFlowProcessRunning
                                        ? "border-slate-200 bg-slate-100 text-ink-muted disabled:cursor-not-allowed"
                                        : "border-border bg-surface text-ink",
                                    )}
                                  />
                                  <div className="flex items-center gap-2">
                                    <select
                                      value={draft?.approved_role ?? "unknown"}
                                      aria-label={`Approved role for ${column.raw_column_name}`}
                                      disabled={
                                        isReadyForAnalysis ||
                                        selectedDatasetIsDeleting ||
                                        dataFlowProcessRunning
                                      }
                                      onChange={(event) =>
                                        updateMappingDraft(column.id, {
                                          approved_role: event.target.value as SemanticRole,
                                        })
                                      }
                                      className={cn(
                                        "min-w-0 flex-1 rounded-md border px-2 py-1.5 text-[0.6875rem] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary",
                                        isReadyForAnalysis ||
                                          selectedDatasetIsDeleting ||
                                          dataFlowProcessRunning
                                          ? "appearance-none border-slate-200 bg-slate-100 text-ink-muted disabled:cursor-not-allowed"
                                          : "border-border bg-surface text-ink",
                                      )}
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
                              <td className="px-2 py-2 font-mono text-[0.6875rem] leading-tight text-ink-muted">
                                {column.sample_values.length > 0 ? (
                                  <ul className="grid gap-1">
                                    {column.sample_values.slice(0, 3).map((value, index) => (
                                      <li
                                        key={`${column.id}-sample-${index}`}
                                        className="truncate whitespace-nowrap"
                                        title={value}
                                      >
                                        {value}
                                      </li>
                                    ))}
                                  </ul>
                                ) : (
                                  <span>No non-null sample</span>
                                )}
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
                        title={
                          selectedDatasetIsDeleting
                            ? "Wait until dataset removal finishes before saving mappings."
                            : dataFlowProcessRunning
                              ? `Wait for the current process to finish: ${dataFlowProcessLabel}.`
                            : activeTransformRunning
                              ? "Wait until dbt transformation finishes before saving mappings."
                            : "Save reviewed names and roles for dbt transformation."
                        }
                      >
                        {activeSemanticActionState === "saving" ? <InlineSpinner /> : null}
                        {activeSemanticActionState === "saving" ? "Saving..." : "Save mappings"}
                      </Button>
                      {!isReadyForAnalysis ? (
                        <Button
                          size="sm"
                          disabled={!canTransform}
                          onClick={() => void handleTransform()}
                          title={
                            selectedDatasetIsDeleting
                              ? "Wait until dataset removal finishes before running dbt."
                              : dataFlowProcessRunning
                                ? `Wait for the current process to finish: ${dataFlowProcessLabel}.`
                              : semanticMappingsReady
                              ? "Run dbt on Snowflake to build Staging, Intermediate, Dimensional Model, and Data Marts."
                              : "Generate or save semantic mappings before running dbt."
                          }
                        >
                          {activeTransformRunning ? <InlineSpinner /> : null}
                          {activeTransformRunning ? "Transforming..." : "Transform"}
                        </Button>
                      ) : null}
                    </div>
                  </div>

                  {activeTransformMessage ? (
                    <div
                      className={cn(
                        "mt-3 rounded-md border px-3 py-2 text-sm",
                        isReadyForAnalysis
                          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                          : "border-amber-200 bg-amber-50 text-amber-800",
                      )}
                    >
                      {activeTransformMessage}
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
        <div className="flex items-center gap-2 px-6 py-8 text-sm text-ink-muted">
          <InlineSpinner />
          Loading Data Flow...
        </div>
      }
    >
      <DataFlowContent />
    </Suspense>
  );
}
