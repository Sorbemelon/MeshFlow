---
id: DEC-20260627-2148-user-public-reset-demo-always-preserv-C36N
type: decision
status: approved
view: main
user: "USER"
agent: "codex"
git: "main@10d01c7"
created_at: 2026-06-27T21:48:27+07:00
tags:
  - "phase-10n"
  - "reset"
  - "quota"
source_refs:
  - "docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#5-production-limits::section"
user_reply_excerpt: "Phase 10N \u2014 Reset Demo behavior repair. Public reset endpoint always preserves quota. Launch Demo after reset starts a fresh workspace flow while preserving backend quota usage."
approved_summary: "Public Reset Demo always preserves quota usage. The user-facing Reset Demo flow clears workspace data but never restores quota usage, including local development UI usage. Development/test quota reset, if ever needed, must be separate from the public Reset Demo endpoint and flow.\n\nImplementation impact:\n- Public reset response returns status=reset, usage_reset=false, quota_restored=false, workspace_cleared=true, and a next_action to launch a new workspace flow.\n- Reset keeps the valid backend session for quota accounting while clearing workspace state.\n- Landing shows Launch Demo after reset, not Continue Demo.\n- Launch Demo after reset reuses the valid reset/empty session and routes to /demo/upload instead of creating a quota-bypassing fresh session.\n- Tests must assert reset preserves usage even if older ALLOW_DEMO_RESET_USAGE configuration appears in stale docs or local environments."
approval_mode: user_approved_buffer_text
---

# Decision: Public Reset Demo always preserves quota usage

Public Reset Demo always preserves quota usage. The user-facing Reset Demo flow clears workspace data but never restores quota usage, including local development UI usage. Development/test quota reset, if ever needed, must be separate from the public Reset Demo endpoint and flow.

Implementation impact:
- Public reset response returns status=reset, usage_reset=false, quota_restored=false, workspace_cleared=true, and a next_action to launch a new workspace flow.
- Reset keeps the valid backend session for quota accounting while clearing workspace state.
- Landing shows Launch Demo after reset, not Continue Demo.
- Launch Demo after reset reuses the valid reset/empty session and routes to /demo/upload instead of creating a quota-bypassing fresh session.
- Tests must assert reset preserves usage even if older ALLOW_DEMO_RESET_USAGE configuration appears in stale docs or local environments.
