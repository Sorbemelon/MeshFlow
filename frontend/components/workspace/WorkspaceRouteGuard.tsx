"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";

function sessionCopy(
  status: ReturnType<typeof useWorkspaceSession>["sessionStatus"],
) {
  switch (status) {
    case "checking":
      return {
        title: "Checking demo session",
        body: "MeshFlow is validating the anonymous session with the backend.",
      };
    case "expired":
      return {
        title: "This demo session expired",
        body: "Anonymous sessions last 3 days. Start a new session to continue.",
      };
    case "backend_unavailable":
      return {
        title: "Backend is unavailable",
        body: "Start the FastAPI backend, then retry this workspace request.",
      };
    case "error":
      return {
        title: "Workspace is not ready",
        body: "MeshFlow could not load the workspace contract from the backend.",
      };
    case "no_session":
    default:
      return {
        title: "No active demo session",
        body: "Start an anonymous demo session before opening the workspace.",
      };
  }
}

export function WorkspaceRouteGuard({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();
  const {
    backendStatus,
    error,
    refresh,
    sessionStatus,
    startSession,
  } = useWorkspaceSession();

  if (sessionStatus === "active") {
    return <>{children}</>;
  }

  const copy = sessionCopy(sessionStatus);
  const isChecking = sessionStatus === "checking";
  const canStart =
    sessionStatus === "no_session" || sessionStatus === "expired";

  async function handleStart() {
    const workspace = await startSession();
    if (workspace) {
      router.push("/demo/upload");
    }
  }

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] items-center justify-center px-6 py-10">
      <section className="w-full max-w-xl rounded-lg border border-border bg-surface p-6 text-center shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
        <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-primary-tint text-primary">
          <svg
            width={20}
            height={20}
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
        </div>
        <h1 className="mt-4 text-lg font-semibold text-ink">{copy.title}</h1>
        <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-muted">
          {error?.message ?? copy.body}
        </p>
        {error?.next_action ? (
          <p className="mt-1 text-xs text-ink-muted">{error.next_action}</p>
        ) : null}
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          <StatusBadge
            status={
              backendStatus === "available"
                ? "ready"
                : backendStatus === "checking"
                  ? "running"
                  : "failed"
            }
            label={
              backendStatus === "available"
                ? "Backend available"
                : backendStatus === "checking"
                  ? "Checking backend"
                  : "Backend unavailable"
            }
          />
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {canStart ? (
            <Button
              type="button"
              onClick={handleStart}
              disabled={backendStatus === "unavailable" || isChecking}
            >
              Start Demo
            </Button>
          ) : null}
          <Button
            type="button"
            variant="secondary"
            onClick={() => void refresh()}
            disabled={isChecking}
          >
            Retry
          </Button>
          <Button href="/" variant="ghost">
            Back to Landing
          </Button>
        </div>
      </section>
    </div>
  );
}
