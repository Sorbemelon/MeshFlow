---
id: DEC-20260627-1930-user-post-refinement-workflow-and-das-E5MX
type: decision
status: approved
view: main
user: "USER"
agent: "codex"
git: "main@de5381b"
created_at: 2026-06-27T19:30:30+07:00
tags:
  - "phase-10m"
  - "dashboard"
  - "semantic-preparation"
  - "data-flow"
source_refs:
  - "docs/scopian/sources/AI_WORKFLOW.md#semantic-preparation"
  - "docs/scopian/sources/FRONTEND_UX_SCOPE.md#dashboard"
  - "docs/scopian/sources/DATA_MODEL.md#analysis-and-dashboard"
  - "docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#5-production-limits::section"
user_reply_excerpt: "User approved these refinements across the current direct-update sequence: make semantic preparation an async backend job with polling and retry, expose Add to dashboard from the Dashboard page, do not count a deleted and re-added saved result group/chart again, make backend return model metadata/relationships for uploaded datasets, auto-upload after file validation, and reset demo back to the landing fresh-start state."
approved_summary: "Post-refinement behavior remains within the current MeshFlow v2 demo scope: semantic preparation may run as an asynchronous backend job with polling and retry UI, but it remains column-mapping only and must store no fake suggestions. CSV upload UI may auto-upload after successful validation/preflight and must show honest validation/readiness/upload failures. Reset Demo may navigate immediately to the landing page and clear the local session state while backend cleanup continues honestly. Dashboard may expose an Add to dashboard drawer for saved result groups and may restore a previously archived result-group card without consuming additional dashboard-card/chart quota again. Data Flow may expose backend-owned raw preview rows and validated model metadata/relationships so the UI can render real raw-table previews, transformation flow evidence, star-schema metadata, and mart-to-dimension wiring without name-based inference. Raw Retail demo dataset count quota is removed per the separate approved buffer decision; duplicate active demo datasets are still prevented, and deleted/reset demo datasets may be added again."
approval_mode: user_approved_buffer_text
---

# Decision: Post-refinement workflow and dashboard behavior sync

Post-refinement behavior remains within the current MeshFlow v2 demo scope: semantic preparation may run as an asynchronous backend job with polling and retry UI, but it remains column-mapping only and must store no fake suggestions. CSV upload UI may auto-upload after successful validation/preflight and must show honest validation/readiness/upload failures. Reset Demo may navigate immediately to the landing page and clear the local session state while backend cleanup continues honestly. Dashboard may expose an Add to dashboard drawer for saved result groups and may restore a previously archived result-group card without consuming additional dashboard-card/chart quota again. Data Flow may expose backend-owned raw preview rows and validated model metadata/relationships so the UI can render real raw-table previews, transformation flow evidence, star-schema metadata, and mart-to-dimension wiring without name-based inference. Raw Retail demo dataset count quota is removed per the separate approved buffer decision; duplicate active demo datasets are still prevented, and deleted/reset demo datasets may be added again.
