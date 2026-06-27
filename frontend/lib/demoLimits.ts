export const DEMO_LIMITS = {
  sessionLifetime: "3 days",
  fileSizeMb: 5,
  totalUploadSizeMb: 10,
  successfulAnalysisRunsPerSession: 8,
  chartsPerSession: 8,
  preferredChartsPerAnalysis: 1,
  maxChartsPerAnalysis: 3,
  dashboardsPerSession: 1,
} as const;

export const LANDING_DEMO_LIMIT_ITEMS = [
  { count: DEMO_LIMITS.sessionLifetime, label: "Session" },
  { count: "1", label: "Dashboard" },
  { count: `${DEMO_LIMITS.totalUploadSizeMb} MB`, label: "Upload Storage / Session" },
  {
    count: `${DEMO_LIMITS.successfulAnalysisRunsPerSession}`,
    label: "Analysis",
  },
  {
    count: `${DEMO_LIMITS.chartsPerSession}`,
    label: "Charts",
  },
  {
    count: `${DEMO_LIMITS.preferredChartsPerAnalysis} - ${DEMO_LIMITS.maxChartsPerAnalysis}`,
    label: "Charts Per Analysis",
  },
] as const;

export const LANDING_DEMO_LIMIT_NOTE =
  "Demo data can be removed and added again. Other limits count successful use: reset clears the workspace but does not restore public quota; deleting items does not restore quota. Expired sessions are cleaned up.";

export const SIDEBAR_DEMO_USAGE_ITEMS = [
  {
    label: "Upload",
    value: `0 MB / ${DEMO_LIMITS.totalUploadSizeMb} MB`,
  },
  {
    label: "Analysis",
    value: `0 / ${DEMO_LIMITS.successfulAnalysisRunsPerSession}`,
  },
  {
    label: "Charts",
    value: `0 / ${DEMO_LIMITS.chartsPerSession}`,
  },
  {
    label: "Session",
    value: DEMO_LIMITS.sessionLifetime,
  },
] as const;
