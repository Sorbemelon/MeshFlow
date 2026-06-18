---
id: DEC-20260618-1243-user-revise-ai-provider-routing-and-m-3PZH
type: decision
status: approved
view: main
user: "USER"
agent: "codex"
git: "main@bcfdc7a"
created_at: 2026-06-18T12:43:44+07:00
tags:
  - "ai-provider-routing"
  - "modeling-flow"
  - "implementation-time-decision"
source_refs:
  - "docs/scopian/sources/AI_WORKFLOW.md#dataset-preparation::section"
  - "docs/scopian/sources/SYSTEM_ARCHITECTURE.md#5-backend-architecture::section"
user_reply_excerpt: "The user approved the current implementation direction and listed the approved provider routing, active Gemini config, removed third lane, semantic-prep-only mapping, post-dbt suggested questions, and backend-owned dbt generation/validation."
approved_summary: "MeshFlow now uses two active Gemini API keys and two active Gemini models. GEMINI_API_KEY_3 and GEMINI_MODEL_3 are removed from the active app surface. Semantic preparation is column-mapping only. Suggested questions are generated after successful dbt transformation into Data Marts from the backend-known mart catalog. Provider routing for semantic preparation, suggested questions, analysis plans, and insights is GEMINI_MODEL_1 key 1/2 -> OpenAI -> GEMINI_MODEL_2 key 1/2 -> honest failure. Uploaded CSV modeling proposal routing is GEMINI_MODEL_1 key 1/2 -> GEMINI_MODEL_2 key 1/2 -> OpenAI -> honest failure. Uploaded CSV transformation may use AI-assisted modeling proposals, but backend-owned dbt SQL generation and validation remain required. No deterministic fallback is allowed and provider output is not trusted until backend validation passes."
approval_mode: user_approved_buffer_text
---

# Decision: Revise AI provider routing and modeling preparation flow

MeshFlow now uses two active Gemini API keys and two active Gemini models. GEMINI_API_KEY_3 and GEMINI_MODEL_3 are removed from the active app surface. Semantic preparation is column-mapping only. Suggested questions are generated after successful dbt transformation into Data Marts from the backend-known mart catalog. Provider routing for semantic preparation, suggested questions, analysis plans, and insights is GEMINI_MODEL_1 key 1/2 -> OpenAI -> GEMINI_MODEL_2 key 1/2 -> honest failure. Uploaded CSV modeling proposal routing is GEMINI_MODEL_1 key 1/2 -> GEMINI_MODEL_2 key 1/2 -> OpenAI -> honest failure. Uploaded CSV transformation may use AI-assisted modeling proposals, but backend-owned dbt SQL generation and validation remain required. No deterministic fallback is allowed and provider output is not trusted until backend validation passes.
