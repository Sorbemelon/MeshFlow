"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import { displayDatasetName } from "@/lib/datasetNames";
import {
  type ReadinessCheck,
  type UploadPreflightResponse,
} from "@/lib/meshflowApi";

const ip = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

const WALKTHROUGH = [
  { n: "1", title: "Choose raw data", body: "Use the curated demo or upload your own CSV file." },
  { n: "2", title: "Review schema", body: "Inspect detected columns and confirm the mapping." },
  { n: "3", title: "Transform with warehouse/dbt", body: "Build Staging -> Intermediate -> Dimensional Model -> Data Marts." },
  { n: "4", title: "Ask the AI Analytics Engineer", body: "Attach your dataset and ask a question in plain language." },
  { n: "5", title: "Save charts to dashboard", body: "Validated results land as chart cards with evidence." },
];

type UploadCheckState =
  | "idle"
  | "frontend_blocked"
  | "checking"
  | "blocked"
  | "ready"
  | "failed";

type UploadFailureNotice = {
  message: string;
  nextAction: string | null;
  errorCode: string | null;
};

const ERROR_LABELS: Record<string, string> = {
  FILE_TOO_LARGE: "The selected file is larger than the demo file-size limit.",
  INVALID_FILE_TYPE: "Only .csv files are supported in the MVP.",
  INVALID_CSV_FORMAT: "The CSV structure is not valid for upload preflight.",
  TOTAL_UPLOAD_LIMIT_REACHED: "This file would exceed the session upload-size quota.",
};

function fileSizeMb(sizeBytes: number): number {
  return Math.round((sizeBytes / (1024 * 1024)) * 100) / 100;
}

function readableIssue(code: string): string {
  return ERROR_LABELS[code] ?? code.replaceAll("_", " ").toLowerCase();
}

function validateSelectedFile(file: File, fileSizeLimitMb: number): string[] {
  const issues: string[] = [];
  if (!file.name.toLowerCase().endsWith(".csv")) {
    issues.push("INVALID_FILE_TYPE");
  }

  if (file.size === 0) {
    issues.push("INVALID_CSV_FORMAT");
  }

  if (file.size > fileSizeLimitMb * 1024 * 1024) {
    issues.push("FILE_TOO_LARGE");
  }

  return issues;
}

function readinessBadge(check: ReadinessCheck) {
  if (check.status === "ready") {
    return <StatusBadge status="ready" label="Ready" />;
  }

  if (check.status === "failed") {
    return <StatusBadge status="failed" label="Failed" />;
  }

  if (check.status === "not_configured") {
    return <StatusBadge status="review" label="Not configured" />;
  }

  return <StatusBadge status="waiting" label="Not checked" />;
}

export default function UploadPage() {
  const router = useRouter();
  const fileInputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const {
    activeProcessLabel,
    clearDatasetUploadOperation,
    datasetUploadOperation,
    isAnyProcessRunning,
    limits,
    sessionId,
    startCsvDatasetUpload,
    startDemoDatasetUpload,
    workspace,
  } = useWorkspaceSession();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [checkState, setCheckState] = useState<UploadCheckState>("idle");
  const [frontendErrors, setFrontendErrors] = useState<string[]>([]);

  const fileLimitMb = limits?.max_upload_file_size_mb ?? 5;
  const demoDataset =
    workspace?.datasets.find((dataset) => dataset.source_type === "demo_raw_retail") ??
    null;
  const csvOperation =
    datasetUploadOperation?.kind === "csv" ? datasetUploadOperation : null;
  const demoOperation =
    datasetUploadOperation?.kind === "demo_dataset" ? datasetUploadOperation : null;
  const preflight: UploadPreflightResponse | null = csvOperation?.preflight ?? null;
  const requestError: UploadFailureNotice | null =
    csvOperation?.status === "failed"
      ? {
          message: csvOperation.error?.message ?? csvOperation.message,
          nextAction: csvOperation.error?.next_action ?? null,
          errorCode: csvOperation.error?.error_code ?? null,
        }
      : null;
  const effectiveCheckState: UploadCheckState =
    csvOperation?.status === "checking"
      ? "checking"
      : csvOperation?.status === "uploading" || csvOperation?.status === "completed"
        ? "ready"
        : csvOperation?.status === "failed"
          ? csvOperation.preflight?.can_upload === false
            ? "blocked"
            : "failed"
          : checkState;
  const isUploading = csvOperation?.status === "uploading";
  const isAddingDemo = demoOperation?.status === "preparing_demo";
  const uploadResult =
    csvOperation?.status === "completed" ? csvOperation.result ?? null : null;
  const demoRequestError =
    demoOperation?.status === "failed" ? demoOperation.error?.message ?? demoOperation.message : null;
  const selectedFileName = selectedFile?.name ?? csvOperation?.fileName ?? null;
  const selectedFileMb =
    selectedFile !== null
      ? fileSizeMb(selectedFile.size)
      : csvOperation?.fileSizeMb ?? null;
  const isFileProcessing = effectiveCheckState === "checking" || isUploading;

  useEffect(() => {
    const nextRoute = datasetUploadOperation?.result?.next_route;
    if (datasetUploadOperation?.status !== "completed" || !nextRoute) {
      return;
    }

    clearDatasetUploadOperation();
    router.push(nextRoute);
  }, [
    clearDatasetUploadOperation,
    datasetUploadOperation?.result?.next_route,
    datasetUploadOperation?.status,
    router,
  ]);

  async function runPreflight(file: File) {
    if (isAnyProcessRunning) {
      return;
    }

    setCheckState("checking");

    const response = await startCsvDatasetUpload(file);
    if (!response) {
      setCheckState("failed");
    }
  }

  function handleFileChange(file: File | null) {
    if (isAnyProcessRunning) {
      return;
    }

    clearDatasetUploadOperation();
    setSelectedFile(file);

    if (!file) {
      setFrontendErrors([]);
      setCheckState("idle");
      return;
    }

    const issues = validateSelectedFile(file, fileLimitMb);
    setFrontendErrors(issues);
    if (issues.length > 0) {
      setCheckState("frontend_blocked");
      return;
    }

    void runPreflight(file);
  }

  async function handleUseDemoDataset() {
    if (!sessionId || isAnyProcessRunning || demoDataset) {
      return;
    }

    await startDemoDatasetUpload();
  }

  const filePickerDisabled = isAnyProcessRunning;
  const uploadStateMessage =
    isAnyProcessRunning && !isFileProcessing && !isAddingDemo
      ? `Wait for the current process to finish: ${activeProcessLabel}.`
      : !sessionId
      ? "Waiting for an active demo session before file checks can run."
      : selectedFileName
        ? isUploading
          ? "Preflight passed. Uploading to S3 and loading Snowflake Warehouse Raw."
          : effectiveCheckState === "checking"
            ? "Checking file, quota, S3, and Snowflake readiness."
            : effectiveCheckState === "ready"
              ? "Preflight passed. Upload starts automatically."
            : effectiveCheckState === "frontend_blocked" ||
                effectiveCheckState === "blocked" ||
                effectiveCheckState === "failed"
              ? "MeshFlow found a blocker before upload."
              : "File selected. Waiting for upload checks."
        : `Choose a CSV file to upload. Max ${fileLimitMb} MB per file.`;

  const issueList = [
    ...frontendErrors,
    ...(preflight?.file.errors ?? []),
    ...(preflight?.file.warnings ?? []),
    ...(preflight?.quota.errors ?? []),
  ];
  const readinessBlockers = preflight
    ? [preflight.readiness.s3, preflight.readiness.snowflake].filter(
        (check) => check.status === "failed" || check.status === "not_configured",
      )
    : [];
  const uploadBlocked =
    Boolean(selectedFileName) &&
    (effectiveCheckState === "frontend_blocked" ||
      effectiveCheckState === "blocked" ||
      effectiveCheckState === "failed" ||
      Boolean(requestError));

  return (
    <div className="px-6 py-8">
      {/* Page header with amber icon */}
      <header className="mb-6 flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/12 text-amber-600">
          <svg {...ip} width={20} height={20}>
            <path d="M12 16V4M7 9l5-5 5 5" />
            <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
          </svg>
        </span>
        <div>
          <h1 className="text-xl font-semibold text-ink">
            Upload Dataset
          </h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Add the curated demo dataset or bring your own CSV file.
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        {/* ── Left: combined dataset card ─────────────────────────── */}
        <div className="rounded-lg border border-border bg-surface p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)]" style={{ borderTop: "4px solid #f59e0b" }}>

          {/* Section 1 — Raw Retail Demo */}
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-ink">
                Raw Retail Transactions Demo
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                A raw, denormalized retail transactions file. MeshFlow turns it
                into a Dimensional Model and Data Marts. Remove it later if you
                want to add a fresh copy.
              </p>
            </div>
            <StatusBadge
              status={demoDataset ? "ready" : isAddingDemo ? "running" : "waiting"}
              label={
                demoDataset
                  ? "Added"
                  : isAddingDemo
                    ? "Preparing"
                    : "Not added"
              }
              className="shrink-0 mt-0.5"
            />
          </div>

          <Button
            className="mt-4"
            size="sm"
            disabled={!sessionId || isAnyProcessRunning || Boolean(demoDataset)}
            onClick={handleUseDemoDataset}
            title={
              !sessionId
                ? "Available once a demo session is active."
                : demoDataset
                ? "An active copy already exists. Delete it from Data Flow before adding a fresh copy."
                : isAnyProcessRunning
                ? `Wait for the current process to finish: ${activeProcessLabel}.`
                : "Upload the curated raw retail CSV to S3 and load it into Snowflake Warehouse Raw."
            }
          >
            {isAddingDemo ? (
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
            ) : null}
            {demoDataset
              ? "Demo Dataset Added"
              : isAddingDemo
                ? "Preparing demo dataset..."
                : "Use Demo Dataset"}
          </Button>

          {demoRequestError ? (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {demoRequestError}
            </div>
          ) : null}

          {/* Divider */}
          <hr className="my-5 border-border" />

          {/* Section 2 — Upload CSV */}
          <h2 className="text-base font-semibold text-ink">
            Upload your own CSV
          </h2>
          <p className="mt-1 text-sm text-ink-soft">
            Upload CSV files within the session storage limit. Each file also gets a safety check before upload.
          </p>

          <input
            id={fileInputId}
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            disabled={filePickerDisabled}
            className="sr-only"
            onChange={(e) => {
              handleFileChange(e.target.files?.[0] ?? null);
              e.currentTarget.value = "";
            }}
          />

          <div className="mt-3 rounded-md border border-dashed border-border bg-surface-muted px-4 py-5 text-center">
            {selectedFileName ? (
              <p className="text-sm text-ink-soft">
                Selected:{" "}
                <span className="font-mono text-ink">{selectedFileName}</span>
                {selectedFileMb !== null ? (
                  <span className="ml-2 text-xs text-ink-muted">
                    {selectedFileMb} MB
                  </span>
                ) : null}
              </p>
            ) : (
              <p className="text-sm text-ink-muted">
                Choose a CSV file. MeshFlow checks it first, then uploads automatically if it is ready.
              </p>
            )}

            <div className="mt-3 flex items-center justify-center gap-2">
              {selectedFileName ? (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  disabled={filePickerDisabled}
                  title={
                    isAddingDemo
                      ? "Wait for the demo dataset to finish preparing before changing files."
                      : isAnyProcessRunning
                        ? `Wait for the current process to finish: ${activeProcessLabel}.`
                      : undefined
                  }
                  onClick={() => inputRef.current?.click()}
                >
                  Change file
                </Button>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  disabled={filePickerDisabled}
                  title={
                    isAddingDemo
                      ? "Wait for the demo dataset to finish preparing before uploading a CSV."
                      : isAnyProcessRunning
                        ? `Wait for the current process to finish: ${activeProcessLabel}.`
                      : undefined
                  }
                  onClick={() => inputRef.current?.click()}
                >
                  Upload
                </Button>
              )}
            </div>
            <p
              className={
                uploadBlocked || !sessionId
                  ? "mt-2 text-xs font-medium text-red-700"
                  : "mt-2 text-xs text-ink-muted"
              }
            >
              {uploadStateMessage}
            </p>
          </div>

          {uploadBlocked ? (
            <div
              className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-800"
              role="alert"
              aria-live="assertive"
            >
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status="failed" label={requestError ? "Upload failed" : "Upload blocked"} />
                {requestError?.errorCode ? (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 font-mono text-[0.6875rem] font-semibold text-red-700">
                    {requestError.errorCode}
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-xs leading-relaxed">
                {requestError?.message ??
                  preflight?.message ??
                  "MeshFlow cannot upload this CSV yet."}
              </p>
              {issueList.length > 0 || readinessBlockers.length > 0 ? (
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-relaxed">
                  {[...new Set(issueList)].map((issue) => (
                    <li key={issue}>{readableIssue(issue)}</li>
                  ))}
                  {readinessBlockers.map((check) => (
                    <li key={`${check.status}-${check.message}`}>
                      {check.message}
                      {check.next_action ? ` ${check.next_action}` : ""}
                    </li>
                  ))}
                </ul>
              ) : null}
              {requestError?.nextAction ? (
                <p className="mt-2 text-xs font-medium text-red-700">
                  {requestError.nextAction}
                </p>
              ) : null}
              {effectiveCheckState !== "checking" ? (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {selectedFile ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={isAnyProcessRunning}
                      onClick={() => runPreflight(selectedFile)}
                    >
                      Retry checks
                    </Button>
                  ) : null}
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={filePickerDisabled}
                    onClick={() => inputRef.current?.click()}
                  >
                    Change file
                  </Button>
                </div>
              ) : null}
            </div>
          ) : null}

          {effectiveCheckState === "checking" ? (
            <div className="mt-3 flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
              <StatusBadge status="running" label="Checking" />
              <span>Checking file, S3, and Snowflake readiness...</span>
            </div>
          ) : null}

          {issueList.length > 0 ? (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2">
              <p className="text-xs font-semibold text-red-700">
                Preflight blocked
              </p>
              <ul className="mt-1.5 list-disc space-y-1 pl-4 text-xs text-red-700">
                {[...new Set(issueList)].map((issue) => (
                  <li key={issue}>{readableIssue(issue)}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {isUploading ? (
            <div className="mt-3 flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
              <StatusBadge status="running" label="Uploading" />
              <span>Uploading to S3 and loading Snowflake Warehouse Raw...</span>
            </div>
          ) : null}

          {uploadResult ? (
            <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
              Upload completed for{" "}
              <span className="font-mono">
                {displayDatasetName(uploadResult.dataset.name, uploadResult.dataset.id)}
              </span>.
              Opening Data Flow for schema review.
            </div>
          ) : null}

          {preflight ? (
            <div className="mt-3 grid gap-2">
              <div className="rounded-md border border-border bg-surface px-3 py-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-semibold text-ink">
                    File validation
                  </span>
                  <StatusBadge
                    status={preflight.file.valid ? "ready" : "failed"}
                    label={preflight.file.valid ? "Valid" : "Blocked"}
                  />
                </div>
                {preflight.file.valid ? (
                  <p className="mt-1 text-xs text-ink-muted">
                    {preflight.file.column_count} columns,{" "}
                    {preflight.file.row_count_previewed} previewed row
                    {preflight.file.row_count_previewed === 1 ? "" : "s"}.
                  </p>
                ) : null}
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-md border border-border bg-surface px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold text-ink">
                      S3 readiness
                    </span>
                    {readinessBadge(preflight.readiness.s3)}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                    {preflight.readiness.s3.message}
                  </p>
                </div>
                <div className="rounded-md border border-border bg-surface px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold text-ink">
                      Snowflake readiness
                    </span>
                    {readinessBadge(preflight.readiness.snowflake)}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                    {preflight.readiness.snowflake.message}
                  </p>
                </div>
              </div>

              <p className="rounded-md border border-border bg-surface px-3 py-2 text-xs text-ink-muted">
                {preflight.can_upload
                  ? "Ready for upload. MeshFlow is uploading to S3, loading Warehouse Raw in Snowflake, and opening Data Flow for schema review."
                  : preflight.message}
              </p>
            </div>
          ) : null}

          <p className="mt-3 text-xs text-ink-muted">
            MeshFlow validates the CSV, storage quota, and S3 + Snowflake readiness
            before any data is sent. Invalid or unsupported files are rejected
            with a clear reason; no partial or invented success.
          </p>
        </div>

        {/* ── Right: Demo Walkthrough card ────────────────────────── */}
        <div className="rounded-lg border border-border bg-surface p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
          <div className="flex items-center gap-2 text-ink">
            <svg
              width={16}
              height={16}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
              className="text-primary"
            >
              <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" stroke="none" />
            </svg>
            <h2 className="text-base font-semibold">Demo Walkthrough</h2>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            Five steps from raw file to validated chart.
          </p>

          <ol className="mt-5 space-y-0">
            {WALKTHROUGH.map((step, i) => (
              <li key={step.n} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-tint font-mono text-[0.625rem] font-semibold text-primary">
                    {step.n}
                  </span>
                  {i < WALKTHROUGH.length - 1 ? (
                    <span className="mt-1 w-px flex-1 bg-border" style={{ minHeight: "24px" }} />
                  ) : null}
                </div>
                <div className={i < WALKTHROUGH.length - 1 ? "pb-4" : ""}>
                  <p className="text-sm font-medium text-ink">{step.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">
                    {step.body}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
