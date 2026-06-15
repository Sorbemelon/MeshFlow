---
id: DEC-20260616-0336-user-demo-limit-correction-AW5Q
type: decision
status: approved
view: main
user: "USER"
agent: "codex"
git: "main@3b688e3"
created_at: 2026-06-16T03:36:40+07:00
tags:
  - "demo-limits"
  - "quota"
  - "phase-2t"
source_refs:
  - "docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#5-production-limits::section"
  - "docs/scopian/sources/DATA_MODEL.md#4-usage-limits::section"
user_reply_excerpt: "The user approved a frontend demo-limit correction during Phase 2T.\n\nThe corrected canonical limit is:\n- Successful analysis runs: 8 per demo session\n- Dashboard cards: 8 per demo session\n\nReason:\nEach successful analysis run produces at least one dashboard card, so allowing more successful analysis runs than dashboard cards creates confusing quota behavior."
approved_summary: "Title:\nAlign analysis-run limit with dashboard-card limit\n\nDecision:\nMeshFlow v2 now uses 8 successful analysis runs and 8 dashboard cards per demo session.\n\nDetails:\n- Successful analysis runs per demo session: 8\n- Dashboard cards per demo session: 8\n- Charts per analysis: prefer 1 chart, maximum 3\n- Session lifetime: 3 days\n- Demo dataset can be added once per session\n- Uploaded CSV datasets: 1 per session in MVP\n- File size limit: 5 MB per file\n- Total upload size limit: 10 MB per session\n- Dashboard count: 1 dashboard\n- Reset Demo does not reset quota or usage in production\n- Reset Demo may reset quota/usage only in development if explicitly configured\n- Deleting datasets, analysis outputs, generated charts, or dashboard cards does not reduce used quota after successful processing\n- Usage counters represent successful processed usage, not currently visible items\n- Expired sessions are cleaned up after expiry\n\nReason:\nEach successful analysis run produces at least one dashboard card, so allowing more successful analysis runs than dashboard cards creates confusing quota behavior. Keeping both limits equal makes the public demo quota easier to explain and easier to implement correctly.\n\nSupersedes:\nThe previous planned value of 10 successful analysis runs per session.\n\nImplementation impact:\n- Frontend demo-limit copy already reflects 8 analyses / 8 cards.\n- Phase 3 backend session/limits contract must use 8 successful analysis runs and 8 dashboard cards.\n- Future quota logic must count successful usage, not currently visible items.\n- Production reset and deletion must not restore quota usage."
approval_mode: user_approved_buffer_text
---

# Decision: demo limit correction

Title:
Align analysis-run limit with dashboard-card limit

Decision:
MeshFlow v2 now uses 8 successful analysis runs and 8 dashboard cards per demo session.

Details:
- Successful analysis runs per demo session: 8
- Dashboard cards per demo session: 8
- Charts per analysis: prefer 1 chart, maximum 3
- Session lifetime: 3 days
- Demo dataset can be added once per session
- Uploaded CSV datasets: 1 per session in MVP
- File size limit: 5 MB per file
- Total upload size limit: 10 MB per session
- Dashboard count: 1 dashboard
- Reset Demo does not reset quota or usage in production
- Reset Demo may reset quota/usage only in development if explicitly configured
- Deleting datasets, analysis outputs, generated charts, or dashboard cards does not reduce used quota after successful processing
- Usage counters represent successful processed usage, not currently visible items
- Expired sessions are cleaned up after expiry

Reason:
Each successful analysis run produces at least one dashboard card, so allowing more successful analysis runs than dashboard cards creates confusing quota behavior. Keeping both limits equal makes the public demo quota easier to explain and easier to implement correctly.

Supersedes:
The previous planned value of 10 successful analysis runs per session.

Implementation impact:
- Frontend demo-limit copy already reflects 8 analyses / 8 cards.
- Phase 3 backend session/limits contract must use 8 successful analysis runs and 8 dashboard cards.
- Future quota logic must count successful usage, not currently visible items.
- Production reset and deletion must not restore quota usage.
