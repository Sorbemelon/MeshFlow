---
generated_by: scopian
generator_schema: v0.2-B
view: main
generated_at: 2026-06-18T12:43:49+07:00
non_canonical: true
generated_mode: single
canonical_inputs:
  - VIEW.md
  - selected Scope Sources
  - approved Scope Buffer
  - context.yml
  - source_registry.yml
input_hashes:
  view: sha256:d8813ce52fd6
  sources: sha256:4a0593b28507
  buffer: sha256:fbe41a37ce33
  context: sha256:5ef45bc1a5d7
  registry: sha256:b41cce7544f0
---

# Generated Scope View

## Non-Canonical Notice

This file is generated and non-canonical.
Canonical scope comes from VIEW.md, selected Scope Sources, approved Scope Buffer records, context.yml, and source_registry.yml.
Regenerate with `scopian view refresh` after source or buffer changes.

## Active Scope View

- view: main
- view_path: docs/scopian/views/main/VIEW.md
- generated_at: 2026-06-18T12:43:49+07:00

## Selected Sources

- docs/scopian/sources/AI_WORKFLOW.md (sha256:a77e00b72623804082c5830082e12ae7a5869335ce08af020990bc733c599734)
- docs/scopian/sources/API_CONTRACT.md (sha256:646d49cd4ba0bc4dfaf0f8cdffeff35d23608f7f973fe384587039f2541fe32b)
- docs/scopian/sources/BUILD_PHASES.md (sha256:3935d01c9073d8d70cdffbeb46fdfddcd8f57792ba818908ee7fa8317828cd28)
- docs/scopian/sources/DATA_MODEL.md (sha256:26d16b387a119bafca06bea19be125d50c092414417087c9f4302ece90951649)
- docs/scopian/sources/DATA_SELECTION_UX.md (sha256:bd9d319a4be5fe83327f0c0dcfd7434acb0252b9d9cd5ad1e414216c5f5c81ae)
- docs/scopian/sources/FRONTEND_UX_SCOPE.md (sha256:9dbd222f45834907ce53736e8db78d5c82422bd9cd2d3169ef138ce03c7ee540)
- docs/scopian/sources/LEGACY_REFERENCE_RULES.md (sha256:7cf570714a2d15c6df27933b1d4aee6f3f4ca4617ba46f0e3b3db649bbdb570d)
- docs/scopian/sources/MAINTENANCE_RULES.md (sha256:4d579eb37606b6e47199338f365063140b5d7c6daa3a4d0d3712128f62157815)
- docs/scopian/sources/PRODUCT_SCOPE.md (sha256:2f6c4329924e8ed44689b29ba218c81fa8fe5f000f58a87b76f8d190eff5e214)
- docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md (sha256:ad9d058c588b09bb93402e5777e7e411d07cbba73775f52a884124afe8eab3fa)
- docs/scopian/sources/SYSTEM_ARCHITECTURE.md (sha256:5c85a3a33fe5d0e42ce7e915cf7897ced7134d58d84baba1d74f31d35a8a4d41)
- docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md (sha256:b02c43a20d8f9ea10d73cb207442e04da879ce752caed3064feceb3413b72af7)
- DESIGN.md (sha256:9c433b2fda9ab692012d369d87293e453aaad381438047b1135e99027ab9dc6e)
- PRODUCT.md (sha256:8e574e1b9aad45d736182911b035fff7b52c2152c2f9ffb0749f62dfea717ac8)

## Approved Buffer Summary

- 2026-06-16T03:36:40+07:00 DEC-20260616-0336-user-demo-limit-correction-AW5Q: Title: Align analysis-run limit with dashboard-card limit Decision: MeshFlow v2 now uses 8 successful analysis runs and 8 dashboard card ... (docs/scopian/views/main/buffer/decisions/DEC-20260616-0336-user-demo-limit-correction-AW5Q.md)
- 2026-06-18T12:43:44+07:00 DEC-20260618-1243-user-revise-ai-provider-routing-and-m-3PZH: MeshFlow now uses two active Gemini API keys and two active Gemini models. GEMINI_API_KEY_3 and GEMINI_MODEL_3 are removed from the acti ... (docs/scopian/views/main/buffer/decisions/DEC-20260618-1243-user-revise-ai-provider-routing-and-m-3PZH.md)

## Scope Checklist

| Item ID | Scope Signal | Scope Item | Refs | Flags | Implementation Evidence |
|---|---|---|---|---|---|
| ITEM-likely-in-scope-1-data-model-principles-1ff29f01 | likely_in_scope | 1. Data model principles | docs/scopian/sources/DATA_MODEL.md#1-data-model-principles | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-10-chart-renderer-f7d39a50 | likely_in_scope | 10. Chart renderer | docs/scopian/sources/FRONTEND_UX_SCOPE.md#10-chart-renderer | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-10-strict-non-goals-b5f1729d | likely_in_scope | 10. Strict non-goals | docs/scopian/sources/PRODUCT_SCOPE.md#10-strict-non-goals | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-13-analysis-runs-80246ec5 | likely_in_scope | 13. analysis_runs | docs/scopian/sources/DATA_MODEL.md#13-analysis-runs | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-18-cleanup-runs-e262d041 | likely_in_scope | 18. cleanup_runs | docs/scopian/sources/DATA_MODEL.md#18-cleanup-runs | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-2-honest-failure-requirement-b5456593 | likely_in_scope | 2. Honest failure requirement | docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md#2-honest-failure-requirement | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-2-key-entities-e6e4c3e9 | likely_in_scope | 2. Key entities | docs/scopian/sources/DATA_MODEL.md#2-key-entities | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-3-upload-dataset-page-behavior-49584b64 | likely_in_scope | 3. Upload Dataset page behavior | docs/scopian/sources/DATA_SELECTION_UX.md#3-upload-dataset-page-behavior | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-5-2-uploaded-csv-mvp-06472726 | likely_in_scope | 5.2 Uploaded CSV MVP | docs/scopian/sources/PRODUCT_SCOPE.md#5-2-uploaded-csv-mvp | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-5-dataset-dropdown-delete-bin-ac-5408ba43 | likely_in_scope | 5. Dataset dropdown delete/bin action | docs/scopian/sources/DATA_SELECTION_UX.md#5-dataset-dropdown-delete-bin-action | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-5-production-limits-20f14fd3 | likely_in_scope | 5. Production limits | docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#5-production-limits | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-6-dataset-files-8c6af6f1 | likely_in_scope | 6. dataset_files | docs/scopian/sources/DATA_MODEL.md#6-dataset-files | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-6-frontend-architecture-d4d392a3 | likely_in_scope | 6. Frontend architecture | docs/scopian/sources/SYSTEM_ARCHITECTURE.md#6-frontend-architecture | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-6-snowflake-warehouse-raw-513d59ca | likely_in_scope | 6. Snowflake Warehouse Raw | docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md#6-snowflake-warehouse-raw | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-7-main-workspace-source-of-truth-81e5c275 | likely_in_scope | 7. Main workspace source of truth | docs/scopian/sources/SYSTEM_ARCHITECTURE.md#7-main-workspace-source-of-truth | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-8-ai-analytics-engineer-dataset-b3b09cac | likely_in_scope | 8. AI Analytics Engineer dataset attachment | docs/scopian/sources/DATA_SELECTION_UX.md#8-ai-analytics-engineer-dataset-attachment | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-9-failure-rules-7e987a1d | likely_in_scope | 9. Failure rules | docs/scopian/sources/MAINTENANCE_RULES.md#9-failure-rules | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-buttons-shape-gently-rounded-8px-7a62b756 | likely_in_scope | Buttons: **Shape:** Gently rounded (8px, `{rounded.md}`).; **Primary:** Indigo Intent (#4f46e5) fill, white text, 10px 18px padding. The single primary acti ... | DESIGN.md#buttons | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-meshflow-v2-data-model-b22641a9 | likely_in_scope | MeshFlow v2 Data Model | docs/scopian/sources/DATA_MODEL.md#meshflow-v2-data-model | none | not_checked_in_generated_view |
| ITEM-likely-in-scope-post-api-v1-analysis-runs-090ea98a | likely_in_scope | POST /api/v1/analysis-runs | docs/scopian/sources/API_CONTRACT.md#post-api-v1-analysis-runs | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-1-operating-loop-15904d1b | allowed_with_limits | 1. Operating loop | docs/scopian/sources/BUILD_PHASES.md#1-operating-loop | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-1-overview-dark-slate-console-sh-7df4b7d0 | allowed_with_limits | 1. Overview: Dark slate console shell; bright white/`slate-50` content surfaces.; Indigo as the one accent of intent; a functional status palette for everyt ... | DESIGN.md#1-overview | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-10-phase-7-analysis-workflow-76f42d29 | allowed_with_limits | 10. Phase 7 — Analysis workflow | docs/scopian/sources/BUILD_PHASES.md#10-phase-7-analysis-workflow | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-12-data-flow-nodes-and-data-flow-e00217cc | allowed_with_limits | 12. data_flow_nodes and data_flow_edges | docs/scopian/sources/DATA_MODEL.md#12-data-flow-nodes-and-data-flow-edges | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-12-data-marts-ready-state-904ab355 | allowed_with_limits | 12. Data Marts ready state | docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md#12-data-marts-ready-state | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-12-friendly-limit-errors-ca5e1c51 | allowed_with_limits | 12. Friendly limit errors | docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#12-friendly-limit-errors | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-12-phase-9-polish-and-portfolio-0a8581a2 | allowed_with_limits | 12. Phase 9 — Polish and portfolio package | docs/scopian/sources/BUILD_PHASES.md#12-phase-9-polish-and-portfolio-package | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-13-analysis-execution-dee78c13 | allowed_with_limits | 13. Analysis execution | docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md#13-analysis-execution | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-13-quality-gates-a855b8ff | allowed_with_limits | 13. Quality gates | docs/scopian/sources/BUILD_PHASES.md#13-quality-gates | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-17-provider-runs-0db86aac | allowed_with_limits | 17. provider_runs | docs/scopian/sources/DATA_MODEL.md#17-provider-runs | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-2-colors-0a2fa3b3 | allowed_with_limits | 2. Colors | DESIGN.md#2-colors | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-2-commit-style-eaa710a6 | allowed_with_limits | 2. Commit style | docs/scopian/sources/BUILD_PHASES.md#2-commit-style | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-2-complexity-budget-73520e85 | allowed_with_limits | 2. Complexity budget | docs/scopian/sources/MAINTENANCE_RULES.md#2-complexity-budget | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-2-theme-direction-6a8fc22d | allowed_with_limits | 2. Theme direction | docs/scopian/sources/FRONTEND_UX_SCOPE.md#2-theme-direction | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-3-source-of-truth-docs-fabf0c71 | allowed_with_limits | 3. Source-of-truth docs | docs/scopian/sources/MAINTENANCE_RULES.md#3-source-of-truth-docs | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-3-typography-6ca9b3dc | allowed_with_limits | 3. Typography | DESIGN.md#3-typography | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-4-data-flow-dataset-selector-3dea5eb6 | allowed_with_limits | 4. Data Flow dataset selector | docs/scopian/sources/DATA_SELECTION_UX.md#4-data-flow-dataset-selector | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-4-file-validation-39344cdb | allowed_with_limits | 4. File validation | docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md#4-file-validation | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-4-repository-shape-52c100de | allowed_with_limits | 4. Repository shape | docs/scopian/sources/SYSTEM_ARCHITECTURE.md#4-repository-shape | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-4-usage-limits-bd8a160f | allowed_with_limits | 4. usage_limits | docs/scopian/sources/DATA_MODEL.md#4-usage-limits | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-5-1-raw-retail-transactions-demo-73b341bf | allowed_with_limits | 5.1 Raw Retail Transactions Demo | docs/scopian/sources/PRODUCT_SCOPE.md#5-1-raw-retail-transactions-demo | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-5-actual-old-meshflow-theme-refe-b46b610c | allowed_with_limits | 5. Actual old MeshFlow theme reference | docs/scopian/sources/LEGACY_REFERENCE_RULES.md#5-actual-old-meshflow-theme-reference | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-5-backend-architecture-b0ac8c19 | allowed_with_limits | 5. Backend architecture | docs/scopian/sources/SYSTEM_ARCHITECTURE.md#5-backend-architecture | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-5-crosshelix-usage-c94a0785 | allowed_with_limits | 5. CrossHelix usage | docs/scopian/sources/MAINTENANCE_RULES.md#5-crosshelix-usage | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-5-datasets-5105c017 | allowed_with_limits | 5. datasets | docs/scopian/sources/DATA_MODEL.md#5-datasets | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-5-phase-2-frontend-skeleton-ed83be12 | allowed_with_limits | 5. Phase 2 — Frontend skeleton | docs/scopian/sources/BUILD_PHASES.md#5-phase-2-frontend-skeleton | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-5-s3-readiness-and-upload-47519b1a | allowed_with_limits | 5. S3 readiness and upload | docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md#5-s3-readiness-and-upload | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-6-codex-role-boundaries-60b2e189 | allowed_with_limits | 6. Codex role boundaries | docs/scopian/sources/MAINTENANCE_RULES.md#6-codex-role-boundaries | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-6-snapshot-requirement-944d6ec7 | allowed_with_limits | 6. Snapshot requirement | docs/scopian/sources/DATA_SELECTION_UX.md#6-snapshot-requirement | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-6-usage-counting-rules-f94c87cb | allowed_with_limits | 6. Usage counting rules | docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#6-usage-counting-rules | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-7-analysis-plan-output-30c58fe8 | allowed_with_limits | 7. Analysis plan output | docs/scopian/sources/AI_WORKFLOW.md#7-analysis-plan-output | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-7-data-flow-page-0e7347ee | allowed_with_limits | 7. Data Flow page | docs/scopian/sources/FRONTEND_UX_SCOPE.md#7-data-flow-page | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-7-reference-review-method-b8416368 | allowed_with_limits | 7. Reference review method | docs/scopian/sources/LEGACY_REFERENCE_RULES.md#7-reference-review-method | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-7-reset-demo-behavior-9224c9e3 | allowed_with_limits | 7. Reset Demo behavior | docs/scopian/sources/SESSION_LIMITS_AND_NAVIGATION.md#7-reset-demo-behavior | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-8-backend-validation-rules-a4c2dac2 | allowed_with_limits | 8. Backend validation rules | docs/scopian/sources/AI_WORKFLOW.md#8-backend-validation-rules | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-8-crosshelix-and-scopian-exclusi-65717610 | allowed_with_limits | 8. CrossHelix and Scopian exclusion | docs/scopian/sources/LEGACY_REFERENCE_RULES.md#8-crosshelix-and-scopian-exclusion | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-8-dashboard-page-c4d22073 | allowed_with_limits | 8. Dashboard page | docs/scopian/sources/FRONTEND_UX_SCOPE.md#8-dashboard-page | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-9-chart-scope-d9351af3 | allowed_with_limits | 9. Chart scope | docs/scopian/sources/PRODUCT_SCOPE.md#9-chart-scope | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-9-phase-6-dbt-transformation-and-117a386d | allowed_with_limits | 9. Phase 6 — dbt transformation and Data Flow | docs/scopian/sources/BUILD_PHASES.md#9-phase-6-dbt-transformation-and-data-flow | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-9-sql-generation-fbf3d790 | allowed_with_limits | 9. SQL generation | docs/scopian/sources/AI_WORKFLOW.md#9-sql-generation | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-do-do-keep-the-shell-dark-slate-11d78a6d | allowed_with_limits | Do:: **Do** keep the shell dark slate (#0f172a/#1e293b) and content on white / `slate-50`; indigo (#4f46e5) is the only accent of intent.; **Do** show prima ... | DESIGN.md#do | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-don-t-don-t-show-any-fake-succes-68f4a70b | allowed_with_limits | Don't:: **Don't** show any fake success: no fake dataset, fake chart data, fake insight, fake fallback dashboard, or fake generated suggestions. Report miss ... | DESIGN.md#don-t | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-get-api-v1-workspace-c2b72bb1 | allowed_with_limits | GET /api/v1/workspace | docs/scopian/sources/API_CONTRACT.md#get-api-v1-workspace | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-hierarchy-display-700-clamp-2rem-a9511a97 | allowed_with_limits | Hierarchy: **Display** (700, clamp(2rem → 3.5rem), 1.05, -0.02em): Landing hero headline only. Capped well under the 6rem ceiling; `text-wrap: balance`.; ** ... | DESIGN.md#hierarchy | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-meshflow-now-uses-two-active-gem-d65c854f | allowed_with_limits | MeshFlow now uses two active Gemini API keys and two active Gemini models. GEMINI_API_KEY_3 and GEMINI_MODEL_3 are removed from the acti ... | docs/scopian/views/main/buffer/decisions/DEC-20260618-1243-user-revise-ai-provider-routing-and-m-3PZH.md | approved_buffer | not_checked_in_generated_view |
| ITEM-allowed-with-limits-meshflow-v2-frontend-ux-scope-25819ffa | allowed_with_limits | MeshFlow v2 Frontend UX Scope | docs/scopian/sources/FRONTEND_UX_SCOPE.md#meshflow-v2-frontend-ux-scope | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-meshflow-v2-warehouse-and-dbt-ex-c89bc7d2 | allowed_with_limits | MeshFlow v2 Warehouse and dbt Execution | docs/scopian/sources/WAREHOUSE_DBT_EXECUTION.md#meshflow-v2-warehouse-and-dbt-execution | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-named-rules-6553be1c | allowed_with_limits | Named Rules | DESIGN.md#named-rules | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-neutral-shell-deep-0f172a-slate-ff139273 | allowed_with_limits | Neutral: **Shell Deep** (#0f172a / slate-900): The workspace shell and sidebar background; also the ink color on light surfaces.; **Shell** (#1e293b / slate ... | DESIGN.md#neutral | none | not_checked_in_generated_view |
| ITEM-allowed-with-limits-secondary-brand-cyan-38bdf8-and-5820d5e6 | allowed_with_limits | Secondary: **Brand Cyan** (#38bdf8) and **Brand Violet** (#7c3aed): The logo gradient (cyan→violet). Identity-only — the mark, the landing hero accent, deco ... | DESIGN.md#secondary | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-1-core-ai-principle-f131a579 | likely_out_of_scope | 1. Core AI principle | docs/scopian/sources/AI_WORKFLOW.md#1-core-ai-principle | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-1-core-rule-fa703ef6 | likely_out_of_scope | 1. Core rule | docs/scopian/sources/LEGACY_REFERENCE_RULES.md#1-core-rule | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-10-chartspec-generation-4e388dee | likely_out_of_scope | 10. ChartSpec generation | docs/scopian/sources/AI_WORKFLOW.md#10-chartspec-generation | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-12-claude-code-boundaries-867b4dd3 | likely_out_of_scope | 12. Claude Code boundaries | docs/scopian/sources/FRONTEND_UX_SCOPE.md#12-claude-code-boundaries | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-13-frontend-behavior-contract-0a279dd1 | likely_out_of_scope | 13. Frontend behavior contract | docs/scopian/sources/API_CONTRACT.md#13-frontend-behavior-contract | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-13-no-fake-ui-success-3e1c0d55 | likely_out_of_scope | 13. No fake UI success | docs/scopian/sources/FRONTEND_UX_SCOPE.md#13-no-fake-ui-success | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-2-rebuild-reason-6b562ff8 | likely_out_of_scope | 2. Rebuild reason | docs/scopian/sources/PRODUCT_SCOPE.md#2-rebuild-reason | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-4-what-must-not-be-copied-as-is-0082697e | likely_out_of_scope | 4. What must not be copied as-is | docs/scopian/sources/LEGACY_REFERENCE_RULES.md#4-what-must-not-be-copied-as-is | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-7-claude-code-role-boundaries-e8cef369 | likely_out_of_scope | 7. Claude Code role boundaries | docs/scopian/sources/MAINTENANCE_RULES.md#7-claude-code-role-boundaries | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-8-ai-scope-a1f190e0 | likely_out_of_scope | 8. AI scope | docs/scopian/sources/PRODUCT_SCOPE.md#8-ai-scope | none | not_checked_in_generated_view |
| ITEM-likely-out-of-scope-anti-references-upload-csv-ask-c-7d8070e8 | likely_out_of_scope | Anti-references: **"Upload CSV → ask chatbot → random chart."** The whole point is the warehouse-backed, validated path; never let the UI collapse into a to ... | PRODUCT.md#anti-references | none | not_checked_in_generated_view |
| ITEM-decision-required-4-scopian-usage-fe55cd60 | decision_required | 4. Scopian usage | docs/scopian/sources/MAINTENANCE_RULES.md#4-scopian-usage | requires-decision | not_checked_in_generated_view |
| ITEM-decision-required-5-preparation-ai-input-718ddbce | decision_required | 5. Preparation AI input | docs/scopian/sources/AI_WORKFLOW.md#5-preparation-ai-input | none | not_checked_in_generated_view |
| ITEM-conflict-detected-7-dashboard-scope-abc7e517 | conflict_detected | 7. Dashboard scope | docs/scopian/sources/PRODUCT_SCOPE.md#7-dashboard-scope | none | not_checked_in_generated_view |
| ITEM-conflict-detected-title-align-analysis-run-limit-w-d59598ea | conflict_detected | Title: Align analysis-run limit with dashboard-card limit Decision: MeshFlow v2 now uses 8 successful analysis runs and 8 dashboard card ... | docs/scopian/views/main/buffer/decisions/DEC-20260616-0336-user-demo-limit-correction-AW5Q.md | approved_buffer | not_checked_in_generated_view |

## Coverage Snapshot

- likely_in_scope: 20
- allowed_with_limits: 50
- likely_out_of_scope: 11
- decision_required: 2
- conflict_detected: 2
- insufficient_evidence: 0

## PM Summary

- agent_enhanced: false
- template_only: true
- correctness_claim: false
- decision_required_items: 2
- out_of_scope_items: 11

## Changelog Snapshot

- generated_refresh: 2026-06-18T12:43:49+07:00
- selected_sources: 14
- approved_buffer_records: 2

## Freshness Metadata

- view: sha256:d8813ce52fd6
- sources: sha256:4a0593b28507
- buffer: sha256:fbe41a37ce33
- context: sha256:5ef45bc1a5d7
- registry: sha256:b41cce7544f0

## Refresh Instructions

- Regenerate with `scopian view refresh` after source or buffer changes.
- Use `scopian view refresh --mode legacy_split` only when legacy split files are needed.
- Treat this generated file as scope evidence, not implementation correctness.
