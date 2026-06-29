# MeshFlow v2 Data Model

Status: Final approved Phase 0 source document, aligned with approved Phase 10 implementation decisions.

This document defines the approved data model principles and MVP entities. Keep the schema simple and maintainable. Do not over-model future features too early.

## 1. Data model principles

```text
A workspace session can have multiple datasets.
The Raw Retail Demo can be added once per session.
Uploaded CSV usage is limited by stored upload size, not public upload count.
The dashboard is one shared canvas per session.
Dashboard cards can come from multiple datasets.
Each analysis run attaches exactly one dataset in MVP.
Each chart stores a data snapshot.
History remains readable after dataset deletion.
Deleting a dataset disables rerun/refine but does not delete generated outputs.
Successful usage is not decremented by deletion.
```

## 2. Key entities

Current MVP entities:

```text
demo_sessions
datasets
dataset_files
column_profiles
semantic_columns
dataset_question_suggestions
dataset_transformation_runs
dbt_artifacts
data_flow_nodes
data_flow_edges
analysis_runs
analysis_run_charts
analysis_insights
dashboard_cards
ai_provider_runs
```

The schema should grow phase by phase only when product behavior requires it.

## 3. demo_sessions

Purpose: anonymous public demo session and successful usage counter.

Important fields:

```text
id
status: active | expired | reset
created_at
expires_at
last_seen_at
reset_at nullable
successful_uploads_used
demo_dataset_used
uploaded_datasets_used internal legacy counter if retained
successful_analysis_runs_used
dashboard_cards_used
total_upload_mb_used
created_from_ip_hash nullable
user_agent_hash nullable
```

Rules:

```text
Workspace routes require an active session.
Expired sessions are inaccessible.
Public reset clears workspace data but does not reset usage.
Development/test usage reset, if ever needed, must be separate from the public Reset Demo flow.
Upload storage usage increments only after successful stored upload/load.
```

## 4. datasets

Purpose: one dataset in a workspace session.

Important fields:

```text
id
demo_session_id
name
source_type: demo_raw_retail | uploaded_csv
status: schema_review | warehouse_loaded | transforming | ready_for_analysis | transform_failed | failed | deleted
raw_table_name
storage_uri
storage_key
row_count
column_count
created_at
updated_at
deleted_at nullable
```

Rules:

```text
Raw Retail Demo can be added once per session.
Deleted datasets should not appear as normal active datasets.
Deleted datasets must remain referenceable by historical outputs.
Dashboard cards and history use snapshots so they still render after deletion.
```

## 5. dataset_files

Purpose: source file records.

Important fields:

```text
id
dataset_id
file_name
storage_key
file_size_bytes
content_type nullable
checksum_sha256 nullable
row_count
column_count
created_at
```

MVP upload rule:

```text
one CSV file per uploaded dataset
session-level upload quota is total stored upload size
```

## 6. column_profiles

Purpose: deterministic column profiling from warehouse/raw table.

Important fields:

```text
id
dataset_id
dataset_file_id nullable
column_index
raw_column_name
normalized_column_name
snowflake_column_name
detected_type: date | integer | decimal | boolean | string | identifier | unknown
null_count
null_rate
unique_count nullable
sample_values_json
parse_stats_json nullable
created_at
```

Profiling is deterministic and does not require AI.

## 7. semantic_columns

Purpose: AI-assisted semantic column suggestions plus user-approved mapping.

Important fields:

```text
id
dataset_id
column_profile_id
raw_column_name
suggested_name
semantic_role: identifier | date_time | measure_column | metric_candidate | dimension | unknown
confidence
needs_review
reason
approved_name nullable
approved_role nullable
include_in_model
user_edited
provider_name nullable
provider_model nullable
created_at
updated_at
```

Rules:

```text
Semantic preparation is column mapping only.
Suggested questions are not stored here.
AI suggestions are suggestions, not truth.
Low-confidence fields need review.
User edits are stored and used for dbt transformation.
Manual mappings may be saved without AI suggestions.
```

## 8. dataset_question_suggestions

Purpose: post-dbt/Data-Marts suggested questions for the Dashboard AI Analytics Engineer.

Important fields:

```text
id
dataset_id
question
intent nullable
sort_order
provider_name nullable
provider_model nullable
created_at
```

Rules:

```text
Generate only after Data Marts exist.
Use the backend-known mart catalog.
Expose separately from semantic_preparation as question_suggestions.
Do not fake suggestions when providers fail.
```

## 9. dataset_transformation_runs

Purpose: track the Transform process.

Important fields:

```text
id
dataset_id
status: pending | running | completed | failed
started_at
completed_at nullable
failed_step nullable
error_code nullable
error_message nullable
dbt_project_path nullable
dbt_target_name nullable
dbt_run_summary_json nullable
created_at
```

Rules:

```text
Transform button is shown when schema review is needed or transformation failed.
Transform button is removed after success.
Failed transform keeps retry possible.
Completed transformation marks dataset ready_for_analysis only after dbt succeeds.
```

## 10. dbt_artifacts

Purpose: generated/executed dbt artifact evidence.

Important fields:

```text
id
dataset_id
transformation_run_id
artifact_type: model_sql | schema_yml | project_yml | profiles_yml_redacted | manifest_summary | run_result_summary
layer: staging | intermediate | dimensional_model | data_mart
name
content_redacted
file_path nullable
created_at
```

Rules:

```text
dbt artifacts represent real generation/execution status.
Profiles stored as evidence must be redacted.
No mock dbt success.
```

## 11. data_flow_nodes and data_flow_edges

Purpose: compact lineage/evidence.

Node fields:

```text
id
dataset_id
node_type: raw_input | warehouse_raw | staging | intermediate | dimensional_model | data_mart
name
label
status
metadata_json
created_at
```

Edge fields:

```text
id
dataset_id
from_node_id
to_node_id
edge_type
metadata_json
created_at
```

The preparation rail displays:

```text
Raw Input
Warehouse Raw
Staging
Intermediate
Dimensional Model
Data Marts
```

Analysis/dashboard lineage may appear in evidence drawers or History.

## 12. analysis_runs

Purpose: one AI Analytics Engineer question/action.

Important fields:

```text
id
demo_session_id
dataset_id
question
normalized_question
status: planning | validating | running | completed | failed | reused
decision_type: create_new | reuse_existing | needs_user_confirmation
intent nullable
source_model nullable
grain nullable
metrics_json nullable
dimensions_json nullable
filters_json nullable
generated_sql nullable
output_schema_json nullable
preview_rows_json nullable
row_count nullable
error_code nullable
failed_step nullable
error_message nullable
provider_chain_json nullable
created_at
updated_at
completed_at nullable
```

Rules:

```text
attached_dataset_id is required in MVP.
Dataset must belong to the session.
Dataset must be ready_for_analysis.
Deleted dataset cannot be used for new analysis.
Reuse can return an existing completed run without consuming analysis quota.
```

## 13. analysis_run_charts

Purpose: chart outputs with snapshots.

Important fields:

```text
id
analysis_run_id
dataset_id
chart_type: kpi | line | bar | horizontal_bar | table
title
description nullable
chart_spec_json
data_json
source_model nullable
metric_summary nullable
dimension_summary nullable
sort_order
created_at
```

Snapshot rule:

```text
Chart cards must render even if the source dataset is later deleted.
```

## 14. analysis_insights

Purpose: insights generated after result data and charts exist.

Important fields:

```text
id
analysis_run_id
analysis_run_chart_id nullable
insight_level: question | chart
status: completed | failed
summary nullable
key_findings_json nullable
tags_json nullable
confidence nullable
provider_name nullable
provider_model nullable
error_code nullable
error_message nullable
created_at
updated_at
```

No insight should be generated before warehouse result data exists.

## 15. dashboard_cards

Purpose: one shared dashboard canvas per session.

Important fields:

```text
id
demo_session_id
dataset_id nullable
analysis_run_id nullable
analysis_run_chart_id nullable
card_type: result_group | chart
title
subtitle nullable
dataset_name_snapshot nullable
source_model_snapshot nullable
card_snapshot_json
sort_order
status: active | archived
archived_at nullable
created_at
updated_at
```

Rules:

```text
One dashboard per session.
Max 8 successful dashboard cards.
Deleting a card archives/removes it from the visible canvas.
Deleting a card does not decrement used card quota.
Dashboard cards can come from multiple datasets.
Card snapshots must render without a live dataset dependency.
```

## 16. ai_provider_runs

Purpose: provider run records without exposing secrets.

Important fields:

```text
id
dataset_id nullable
analysis_run_id nullable
task_type: semantic_preparation | dataset_question_suggestions | analysis_plan | insight_generation | modeling_proposal
provider_name: gemini | openai
provider_model nullable
status: completed | failed
error_code nullable
error_message nullable
fallback_from_provider nullable
latency_ms nullable
created_at
```

Rules:

```text
No API keys stored.
Frontend shows compact badges only.
Full chain belongs in evidence/detail views.
```

## 17. Status color mapping

UI status colors should be driven by status type:

```text
completed/ready: emerald
running/checking: blue
waiting/not started: slate
needs review: amber
setup required: amber or indigo
failed: red
provider/AI generated: indigo
deleted/archived: slate
```
