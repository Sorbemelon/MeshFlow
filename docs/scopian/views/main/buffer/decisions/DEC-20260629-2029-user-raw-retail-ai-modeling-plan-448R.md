---
id: DEC-20260629-2029-user-raw-retail-ai-modeling-plan-448R
type: decision
status: approved
view: main
user: "USER"
agent: "codex"
git: "main@172b31e"
created_at: 2026-06-29T20:29:07+07:00
tags:
  - "ai-workflow"
  - "data-flow"
source_refs:
  - "docs/scopian/sources/AI_WORKFLOW.md"
  - "docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md"
user_reply_excerpt: "AI Modeling Plan should not be Not Required. The Raw Retail Demo should use the AI Modeling Plan or else we are missing the real AI modeling plan show in our demo."
approved_summary: "Raw Retail Demo uses a real AI modeling proposal before dbt transformation. The demo Data Flow status rail must mark AI Modeling Plan completed only from stored modeling_proposal_json evidence or modeling_proposal metadata; it must not show Not Required for Raw Retail."
approval_mode: user_approved_buffer_text
---

# Decision: Raw Retail AI modeling plan

Raw Retail Demo uses a real AI modeling proposal before dbt transformation. The demo Data Flow status rail must mark AI Modeling Plan completed only from stored modeling_proposal_json evidence or modeling_proposal metadata; it must not show Not Required for Raw Retail.
