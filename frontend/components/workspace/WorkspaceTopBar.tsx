"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";

export function WorkspaceTopBar() {
  const { backendStatus, sessionStatus } = useWorkspaceSession();

  const demoBadge =
    sessionStatus === "active"
      ? {
          status: "ready" as const,
          label: "Active",
        }
      : sessionStatus === "checking"
        ? { status: "running" as const, label: "Checking..." }
        : sessionStatus === "expired"
          ? { status: "failed" as const, label: "Expired" }
          : sessionStatus === "backend_unavailable"
            ? { status: "review" as const, label: "Session unknown" }
            : { status: "waiting" as const, label: "No session" };

  const backendBadge =
    backendStatus === "available"
      ? { status: "ready" as const, label: "Available" }
      : backendStatus === "checking"
        ? { status: "running" as const, label: "Checking..." }
        : { status: "failed" as const, label: "Unavailable" };

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-border bg-surface/95 px-6 py-3 backdrop-blur-sm">
      <div className="flex items-center gap-2.5">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-tint text-primary">
          <svg
            width={15}
            height={15}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.8}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <rect x="4" y="5" width="16" height="14" rx="2" />
            <path d="M8 9h8M8 13h5" />
          </svg>
        </span>
        <span className="text-sm font-semibold text-ink">Demo Session</span>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-muted px-2.5 py-1">
          <span className="text-xs font-medium text-ink-muted">Demo</span>
          <StatusBadge
            status={demoBadge.status}
            label={demoBadge.label}
            showIcon={false}
          />
        </span>
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-muted px-2.5 py-1">
          <span className="text-xs font-medium text-ink-muted">Backend</span>
          <StatusBadge
            status={backendBadge.status}
            label={backendBadge.label}
            showIcon={false}
          />
        </span>
      </div>
    </header>
  );
}
