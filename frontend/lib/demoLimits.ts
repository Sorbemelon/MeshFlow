export const DEMO_LIMITS = {
  sessionLifetime: "3 days",
  demoDatasetPerSession: 1,
  fileSizeMb: 5,
  totalUploadSizeMb: 10,
  successfulAnalysisRunsPerSession: 8,
  dashboardCardsPerSession: 8,
  preferredChartsPerAnalysis: 1,
  maxChartsPerAnalysis: 3,
  dashboardsPerSession: 1,
} as const;

export const LANDING_DEMO_LIMIT_ITEMS = [
  { count: DEMO_LIMITS.sessionLifetime, label: "anonymous session" },
  { count: "1x", label: "demo dataset" },
  { count: `${DEMO_LIMITS.fileSizeMb} MB`, label: "per file" },
  { count: `${DEMO_LIMITS.totalUploadSizeMb} MB`, label: "upload storage/session" },
  {
    count: `${DEMO_LIMITS.successfulAnalysisRunsPerSession}`,
    label: "successful analyses",
  },
  {
    count: `${DEMO_LIMITS.dashboardCardsPerSession}`,
    label: "dashboard cards",
  },
  {
    count: `${DEMO_LIMITS.preferredChartsPerAnalysis} / ${DEMO_LIMITS.maxChartsPerAnalysis}`,
    label: "preferred / max charts",
  },
] as const;

export const LANDING_DEMO_LIMIT_NOTE =
  "Includes 1 dashboard. Reset clears the workspace but does not restore public quota; deleting items does not restore quota. Expired sessions are cleaned up.";

export const SIDEBAR_DEMO_USAGE_ITEMS = [
  {
    label: "Storage",
    value: `0 MB / ${DEMO_LIMITS.totalUploadSizeMb} MB`,
  },
  {
    label: "Demo data",
    value: `0 / ${DEMO_LIMITS.demoDatasetPerSession}`,
  },
  {
    label: "Analyses",
    value: `0 / ${DEMO_LIMITS.successfulAnalysisRunsPerSession}`,
  },
  {
    label: "Cards",
    value: `0 / ${DEMO_LIMITS.dashboardCardsPerSession}`,
  },
  {
    label: "Session",
    value: DEMO_LIMITS.sessionLifetime,
  },
] as const;
