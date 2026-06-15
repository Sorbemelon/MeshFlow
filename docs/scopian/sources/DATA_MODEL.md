# MeshFlow v2 Data Model

Status: Final approved Phase 0 source document.

This document defines the approved data model principles and MVP entities. Keep the schema simple and maintainable. Do not over-model future features too early.

## 1. Data model principles

```text
A workspace session can have multiple datasets.
The Raw Retail Demo can be added once per session.
The uploaded dataset MVP supports one CSV file.
The dashboard is one shared canvas per session.
Dashboard cards can come from multiple datasets.
Each analysis run attaches exactly one dataset in MVP.
Each chart stores a data snapshot.
History remains readable after dataset deletion.
Deleting a dataset disables rerun/refine but does not delete generated outputs.
Successful usage is not decremented by deletion.
```

## 2. Key entities

MVP entities:

```text
demo_sessions
datasets
dataset_files
column_profiles
semantic_columns
dataset_preparation_runs
data_flow_nodes
data_flow_edges
dbt_artifacts
snowflake_loads
analysis_runs
analysis_run_charts
analysis_insights
dashboard_cards
provider_runs
usage_limits
cleanup_runs
```

Not all future fields need to be implemented in Phase 1. The schema should grow phase by phase.

## 3. demo_sessions

Purpose: anonymous public demo session.

Important fields:

```text
id
public_session_id
session_token_hash optional
status: active | expired | reset
created_at
expires_at
last_seen_at
reset_at nullable
allow_usage_reset_snapshot boolean
metadata_json
```

Rules:

```text
Workspace routes require an active session.
Expired sessions are inaccessible.
Reset clears workspace data but does not reset production usage.
Development can reset usage if ALLOW_DEMO_RESET_USAGE=true.
```

## 4. usage_limits

Purpose: track quota and usage.

Important fields:

```text
id
session_id
quota_key
limit_value
used_value
failed_attempt_count
window_started_at
window_ends_at
created_at
updated_at
```

Quota keys may include:

```text
uploaded_dataset_success_count
uploaded_file_success_count
demo_dataset_added_count
analysis_success_count
dashboard_card_success_count
upload_failed_attempt_count
analysis_failed_attempt_count
```

Rules:

```text
Successful processing increments product usage.
Failures do not consume product usage quota.
Failed attempts may still be tracked for abuse/rate-limit protection.
Deleting successful objects does not decrement usage.
Reset does not reset production usage.
```

## 5. datasets

Purpose: one dataset in a workspace session.

Important fields:

```text
id
session_id
name
source_type: raw_retail_demo | uploaded_csv
status: created | raw_loaded | schema_review | transforming | ready | failed | deleted
is_demo_dataset boolean
deleted_at nullable
created_at
updated_at
ready_at nullable
failure_code nullable
failure_message nullable
snapshot_json
```

Rules:

```text
Raw Retail Demo can be added once per session.
Deleted datasets should not appear as normal active datasets.
Deleted datasets must remain referenceable by historical outputs.
Dashboard cards and history use snapshots so they still render after deletion.
```

## 6. dataset_files

Purpose: source file records.

Important fields:

```text
id
dataset_id
original_file_name
logical_file_name
file_type
file_size_bytes
s3_uri
s3_key
content_hash
row_count
column_count
validation_status: pending | valid | invalid
validation_error_code nullable
validation_message nullable
created_at
```

MVP upload rule:

```text
one CSV file per uploaded dataset
```

## 7. column_profiles

Purpose: deterministic column profiling from warehouse/raw table.

Important fields:

```text
id
dataset_id
dataset_file_id nullable
raw_table_name
raw_column_name
detected_type: date | integer | decimal | boolean | string | identifier | unknown
null_rate
unique_count
sample_values_json
numeric_parse_success
date_parse_success
boolean_parse_success
cardinality_level
value_distribution_json
created_at
```

Profiling is deterministic and does not require AI.

## 8. semantic_columns

Purpose: AI-assisted semantic suggestions plus user-approved mapping.

Important fields:

```text
id
dataset_id
column_profile_id
raw_column_name
suggested_name
approved_name
semantic_role: identifier | date_time | measure_column | metric_candidate | dimension | unknown
confidence
needs_review boolean
reason
included boolean
user_edited boolean
provider_run_id nullable
created_at
updated_at
```

Rules:

```text
AI suggestions are suggestions, not truth.
Low-confidence fields need review.
User edits are stored and used for dbt transformation.
```

## 9. dataset_preparation_runs

Purpose: track the Transform process.

Important fields:

```text
id
dataset_id
status: pending | running | succeeded | failed
started_at
finished_at nullable
failed_step nullable
error_code nullable
error_message nullable
approved_mapping_snapshot_json
created_models_json
```

Rules:

```text
Transform button is shown when schema review is needed or transformation failed.
Transform button is removed after success.
Failed transform keeps retry possible.
```

## 10. snowflake_loads

Purpose: track Warehouse Raw loading.

Important fields:

```text
id
dataset_id
status: pending | running | succeeded | failed
snowflake_database
snowflake_schema
raw_table_name
copy_into_sql nullable
row_count nullable
error_code nullable
error_message nullable
created_at
finished_at nullable
```

There is no fake Snowflake load.

## 11. dbt_artifacts

Purpose: generated/executed dbt model metadata.

Important fields:

```text
id
dataset_id
preparation_run_id
layer: staging | intermediate | dimensional_model | data_mart
model_name
model_type: table | view | incremental nullable
file_path nullable
sql_snapshot
schema_yml_snapshot nullable
status: generated | running | succeeded | failed
error_code nullable
error_message nullable
created_at
```

Rules:

```text
dbt artifacts represent real generation/execution status.
No mock dbt success.
```

## 12. data_flow_nodes and data_flow_edges

Purpose: compact lineage/evidence.

Node fields:

```text
id
dataset_id
node_type: raw_input | warehouse_raw | staging | intermediate | dimensional_model | data_mart | analysis_output | dashboard_card
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

The preparation rail only displays:

```text
Raw Input
Warehouse Raw
Staging
Intermediate
Dimensional Model
Data Marts
```

Analysis/dashboard lineage may appear in evidence drawers or History.

## 13. analysis_runs

Purpose: one AI Analytics Engineer question/action.

Important fields:

```text
id
session_id
attached_dataset_id
question
normalized_question
status: planning | validating | running | generated | failed
intent nullable
source_model nullable
grain nullable
generated_sql nullable
output_schema_json nullable
preview_rows_json nullable
provider_summary_json
fallback_chain_json
warnings_json
error_code nullable
error_message nullable
created_at
finished_at nullable
```

Rules:

```text
attached_dataset_id is required in MVP.
Dataset must belong to the session.
Dataset must be ready.
Deleted dataset cannot be used for new analysis.
```

## 14. analysis_run_charts

Purpose: chart outputs with snapshots.

Important fields:

```text
id
analysis_run_id
attached_dataset_id
chart_type
title
chart_spec_json
chart_data_json
source_model_snapshot
metric_summary
dimension_summary
dataset_snapshot_json
sort_order
created_at
```

Snapshot rule:

```text
Chart cards must render even if the source dataset is later deleted.
```

## 15. analysis_insights

Purpose: insights generated after result data exists.

Important fields:

```text
id
analysis_run_id
chart_id nullable
level: question | chart
summary
key_findings_json
tags_json
confidence
provider_run_id nullable
created_at
```

No insight should be generated before warehouse result data exists.

## 16. dashboard_cards

Purpose: one shared dashboard canvas per session.

Important fields:

```text
id
session_id
source_analysis_run_id
source_chart_id nullable
card_type: chart | result_group
attached_dataset_id
position
size_json nullable
is_collapsed boolean
card_snapshot_json
created_at
deleted_at nullable
```

Rules:

```text
One dashboard per session.
Max 8 successful dashboard cards.
Deleting a card does not decrement used card quota.
Dashboard cards can come from multiple datasets.
```

## 17. provider_runs

Purpose: provider evidence without exposing secrets.

Important fields:

```text
id
session_id
analysis_run_id nullable
dataset_id nullable
task_type: semantic_suggestions | suggested_questions | analysis_plan | insight_generation | chart_explanation | lineage_explanation
provider_name: gemini | openai
model_name
lane nullable
status: succeeded | failed
temperature
error_code nullable
error_message nullable
latency_ms nullable
created_at
```

Rules:

```text
No API keys stored.
Frontend shows compact badges only.
Full chain belongs in evidence/detail views.
```

## 18. cleanup_runs

Purpose: cleanup expired sessions/resources.

Important fields:

```text
id
session_id nullable
status: running | succeeded | partial | failed
started_at
finished_at nullable
resources_deleted_json
errors_json
```

Cleanup should include metadata, S3 objects, Snowflake session schemas/tables, generated dbt artifacts/metadata, analysis outputs, dashboard cards, history records, and temp files.

## 19. Status color mapping

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
