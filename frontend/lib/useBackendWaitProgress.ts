"use client";

import { useEffect, useMemo, useState } from "react";

export type BackendWaitContext =
  | "backend"
  | "landing"
  | "workspace"
  | "data_flow"
  | "reset";

export type BackendWaitProgress = {
  elapsedSeconds: number;
  label: string;
  detail: string;
  isColdStartLikely: boolean;
};

export function useBackendWaitProgress(
  active: boolean,
  context: BackendWaitContext = "backend",
): BackendWaitProgress {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!active) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setElapsedSeconds((seconds) => seconds + 1);
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [active]);

  const visibleElapsedSeconds = active ? elapsedSeconds : 0;

  return useMemo(() => {
    if (context === "reset") {
      return {
        elapsedSeconds: visibleElapsedSeconds,
        label:
          visibleElapsedSeconds >= 10
            ? "Still clearing the workspace..."
            : "Resetting demo workspace...",
        detail:
          "MeshFlow is clearing workspace data while preserving public quota usage.",
        isColdStartLikely: false,
      };
    }

    if (context === "data_flow") {
      return {
        elapsedSeconds: visibleElapsedSeconds,
        label:
          visibleElapsedSeconds >= 12
            ? "Still loading Data Flow evidence..."
            : "Loading Data Flow evidence...",
        detail:
          visibleElapsedSeconds >= 12
            ? "The hosted backend may still be reading metadata and warehouse preview data. This can take a few seconds after a cold wakeup or transformation."
            : "MeshFlow is reading the selected dataset, metadata database records, and warehouse/dbt evidence.",
        isColdStartLikely: visibleElapsedSeconds >= 12,
      };
    }

    if (context === "workspace") {
      return {
        elapsedSeconds: visibleElapsedSeconds,
        label:
          visibleElapsedSeconds >= 15
            ? "Still loading the workspace..."
            : visibleElapsedSeconds >= 5
              ? "Waking the demo backend..."
              : "Checking demo workspace...",
        detail:
          visibleElapsedSeconds >= 15
            ? "Render cold starts can take around a minute on hosted demos. The workspace will open once the backend responds."
            : visibleElapsedSeconds >= 5
              ? "The hosted backend may be resuming from sleep. Keep this tab open."
              : "MeshFlow is validating the demo session and loading workspace metadata.",
        isColdStartLikely: visibleElapsedSeconds >= 5,
      };
    }

    if (context === "landing") {
      return {
        elapsedSeconds: visibleElapsedSeconds,
        label:
          visibleElapsedSeconds >= 15
            ? "Still checking the backend..."
            : visibleElapsedSeconds >= 5
              ? "Waking the demo backend..."
              : "Checking backend status...",
        detail:
          visibleElapsedSeconds >= 15
            ? "Render cold starts can take around a minute on hosted demos. The landing page will update once the backend responds."
            : visibleElapsedSeconds >= 5
              ? "The hosted backend may be resuming from sleep. Keep this tab open."
              : "MeshFlow is checking whether the backend is available. It is not starting a demo session until you click Launch Demo.",
        isColdStartLikely: visibleElapsedSeconds >= 5,
      };
    }

    return {
      elapsedSeconds: visibleElapsedSeconds,
      label:
        visibleElapsedSeconds >= 35
          ? "Still starting the demo..."
          : visibleElapsedSeconds >= 5
            ? "Waking the demo backend..."
            : "Starting demo session...",
      detail:
        visibleElapsedSeconds >= 35
          ? "Render cold starts can take around a minute on hosted demos. The demo will continue once the backend responds."
          : visibleElapsedSeconds >= 5
            ? "The hosted backend may be resuming from sleep. This is normal for the live demo."
            : "Connecting to the MeshFlow backend. Please wait.",
      isColdStartLikely: visibleElapsedSeconds >= 5,
    };
  }, [context, visibleElapsedSeconds]);
}
