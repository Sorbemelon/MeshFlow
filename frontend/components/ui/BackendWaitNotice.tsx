"use client";

import { cn } from "@/lib/cn";
import {
  useBackendWaitProgress,
  type BackendWaitContext,
} from "@/lib/useBackendWaitProgress";

function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "mt-0.5 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent",
        className,
      )}
      aria-hidden
    />
  );
}

export function BackendWaitNotice({
  active,
  context = "backend",
  tone = "light",
  compact = false,
  className,
}: {
  active: boolean;
  context?: BackendWaitContext;
  tone?: "light" | "dark";
  compact?: boolean;
  className?: string;
}) {
  if (!active) {
    return null;
  }

  return (
    <ActiveBackendWaitNotice
      context={context}
      tone={tone}
      compact={compact}
      className={className}
    />
  );
}

function ActiveBackendWaitNotice({
  context,
  tone,
  compact,
  className,
}: {
  context: BackendWaitContext;
  tone: "light" | "dark";
  compact: boolean;
  className?: string;
}) {
  const progress = useBackendWaitProgress(true, context);
  const isDark = tone === "dark";

  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2.5 text-sm",
        compact && "px-2.5 py-2 text-xs",
        isDark
          ? "border-white/15 bg-white/10 text-white"
          : "border-blue-200 bg-blue-50 text-blue-900",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <div className={cn("flex items-start gap-2.5", compact && "gap-2")}>
        <Spinner
          className={cn(
            compact && "h-3.5 w-3.5",
            isDark ? "text-white" : "text-blue-700",
          )}
        />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 font-semibold">
            <span>{progress.label}</span>
            {progress.elapsedSeconds >= 5 ? (
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-medium",
                  isDark ? "bg-white/10 text-white/80" : "bg-white text-blue-700",
                )}
              >
                Waiting {progress.elapsedSeconds}s
              </span>
            ) : null}
          </div>
          <p
            className={cn(
              compact ? "mt-0.5 leading-4" : "mt-1 leading-5",
              isDark ? "text-white/75" : "text-blue-800/80",
            )}
          >
            {progress.detail}
          </p>
          {progress.isColdStartLikely ? (
            <p
              className={cn(
                compact ? "mt-0.5 text-[0.7rem] leading-4" : "mt-1 text-xs leading-5",
                isDark ? "text-white/60" : "text-blue-700/70",
              )}
            >
              {compact
                ? "Waking the hosted backend can take some time. Please wait."
                : "Backend wakeup can take some time. Please wait. Exact hosted backend progress is not exposed to the browser, so this status is estimated from wait time."}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
