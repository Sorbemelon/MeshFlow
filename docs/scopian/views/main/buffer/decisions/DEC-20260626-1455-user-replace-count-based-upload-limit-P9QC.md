---
id: DEC-20260626-1455-user-replace-count-based-upload-limit-P9QC
type: decision
status: approved
view: main
user: "USER"
agent: "codex"
git: "main@fba9a4d"
created_at: 2026-06-26T14:55:53+07:00
tags:
  - "upload-limits"
  - "phase-10f"
source_refs:
  - "docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#5-production-limits::section"
  - "docs/scopian/sources/DATA_MODEL.md#4-usage-limits::section"
user_reply_excerpt: "Current phase: Phase 10F. Part A record upload-limit scope decision in Scopian buffer. Decision title: Replace count-based upload limit with storage-based upload limit."
approved_summary: "Title: Replace count-based upload limit with storage-based upload limit\n\nDecision:\nMeshFlow no longer shows or enforces a count-based uploaded-file/uploaded-dataset limit for public demo uploads. Uploaded CSVs are limited by storage usage instead of upload count.\n\nDetails:\n- Remove the user-facing 1 uploaded CSV / upload-count limit from landing and workspace demo-limit UI.\n- Keep demo dataset limited to one per session.\n- Keep successful analyses limited to 8 per session.\n- Keep dashboard cards limited to 8 per session.\n- Keep charts per analysis as prefer 1, maximum 3.\n- Keep upload storage limits as the active control: max file size remains a safety validation limit if currently configured; total uploaded storage per session remains the public quota limit.\n- Upload usage should count successful stored upload size, not number of uploaded files.\n- Failed validation/preflight/upload/load does not consume upload storage quota.\n- Deleting datasets or resetting in production does not restore used quota.\n- Reset may restore usage only in development if explicitly configured.\n\nReason:\nThe user wants upload limits to be easier to understand and based on storage usage, not number of files. The UI should be consistent between the landing page and demo workspace.\n\nImplementation impact:\n- Remove or stop using uploaded dataset/file count as an active quota blocker.\n- Update frontend limit copy and sidebar counts to show storage usage instead of CSV count.\n- Backend preflight/upload quota should block by storage size, not upload count.\n- Keep demo dataset once-per-session behavior unchanged."
approval_mode: user_approved_buffer_text
---

# Decision: Replace count-based upload limit with storage-based upload limit

Title: Replace count-based upload limit with storage-based upload limit

Decision:
MeshFlow no longer shows or enforces a count-based uploaded-file/uploaded-dataset limit for public demo uploads. Uploaded CSVs are limited by storage usage instead of upload count.

Details:
- Remove the user-facing 1 uploaded CSV / upload-count limit from landing and workspace demo-limit UI.
- Keep demo dataset limited to one per session.
- Keep successful analyses limited to 8 per session.
- Keep dashboard cards limited to 8 per session.
- Keep charts per analysis as prefer 1, maximum 3.
- Keep upload storage limits as the active control: max file size remains a safety validation limit if currently configured; total uploaded storage per session remains the public quota limit.
- Upload usage should count successful stored upload size, not number of uploaded files.
- Failed validation/preflight/upload/load does not consume upload storage quota.
- Deleting datasets or resetting in production does not restore used quota.
- Reset may restore usage only in development if explicitly configured.

Reason:
The user wants upload limits to be easier to understand and based on storage usage, not number of files. The UI should be consistent between the landing page and demo workspace.

Implementation impact:
- Remove or stop using uploaded dataset/file count as an active quota blocker.
- Update frontend limit copy and sidebar counts to show storage usage instead of CSV count.
- Backend preflight/upload quota should block by storage size, not upload count.
- Keep demo dataset once-per-session behavior unchanged.
