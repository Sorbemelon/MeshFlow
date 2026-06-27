---
id: DEC-20260627-0525-user-remove-demo-dataset-upload-count-NXJ5
type: decision
status: approved
view: main
user: "USER"
agent: "codex"
git: "main@de5381b"
created_at: 2026-06-27T05:25:34+07:00
tags:
  - "demo-dataset"
  - "quota"
  - "phase-10"
source_refs:
  - "docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#5-production-limits::section"
user_reply_excerpt: "Remove the limit for demo dataset upload. The demo dataset can now delete and upload again freely."
approved_summary: "Raw Retail demo dataset is no longer limited by a per-session demo dataset quota. MeshFlow still prevents duplicate active Raw Retail demo datasets, but after a user deletes or soft-deletes the active demo dataset, the same session may add a fresh demo dataset again. Remove max_demo_datasets_per_session and demo_dataset_used from the active app/API/frontend quota surface. Keep any legacy database column only for compatibility; it must not block, increment, or appear as an active public quota. This does not restore or change upload storage, analysis, chart, or dashboard quotas."
approval_mode: user_approved_buffer_text
---

# Decision: Remove demo dataset upload count limit

Raw Retail demo dataset is no longer limited by a per-session demo dataset quota. MeshFlow still prevents duplicate active Raw Retail demo datasets, but after a user deletes or soft-deletes the active demo dataset, the same session may add a fresh demo dataset again. Remove max_demo_datasets_per_session and demo_dataset_used from the active app/API/frontend quota surface. Keep any legacy database column only for compatibility; it must not block, increment, or appear as an active public quota. This does not restore or change upload storage, analysis, chart, or dashboard quotas.
