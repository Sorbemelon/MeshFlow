# MeshFlow v2 API Contract

Status: Final approved Phase 0 source document, aligned with approved Phase 10 implementation decisions.

This document defines the approved API contract principles for MeshFlow v2. Keep the API small and maintainable.

## 1. API principles

```text
One workspace endpoint powers the app shell.
Backend owns truth and validation.
Frontend does not invent fake successful data.
Analysis requests must explicitly attach a dataset.
Suggested questions are post-mart dataset question suggestions.
Failure responses must be honest and structured.
Deleting datasets preserves generated output snapshots.
```

## 2. Session header

Use a demo session header for workspace API calls:

```text
X-Demo-Session-Id: <public_session_id>
```

This keeps frontend session handling simple.

## 3. Standard error shape

All handled failures should return a clear error object.

```json
{
  "status": "failed",
  "error_code": "SNOWFLAKE_NOT_READY",
  "failed_step": "warehouse_readiness",
  "message": "Snowflake is not configured, so MeshFlow cannot upload this dataset to Warehouse Raw.",
  "next_action": "Check Snowflake environment variables and try again."
}
```

Common error codes:

```text
INVALID_FILE_TYPE
INVALID_CSV_FORMAT
S3_NOT_READY
SNOWFLAKE_NOT_READY
WAREHOUSE_LOAD_FAILED
SEMANTIC_SUGGESTION_FAILED
SEMANTIC_MAPPING_REQUIRED
TRANSFORMATION_FAILED
DBT_RUN_FAILED
ANALYSIS_PLAN_FAILED
ANALYSIS_QUERY_FAILED
INSIGHT_GENERATION_FAILED
CHARTSPEC_VALIDATION_FAILED
LIMIT_REACHED
DASHBOARD_CARD_LIMIT_REACHED
SESSION_EXPIRED
DATASET_NOT_READY
DATASET_DELETED
DATASET_NOT_FOUND
```

## 4. Core API groups

```text
/api/v1/demo-sessions
/api/v1/workspace
/api/v1/datasets
/api/v1/analysis-runs
/api/v1/dashboard
/api/v1/limits
/api/v1/health
```

Data Flow is dataset-scoped under `/api/v1/datasets/{dataset_id}/data-flow`.

History is represented by `/api/v1/analysis-runs` list/detail responses.

Avoid adding many tiny API groups.

## 5. Demo session endpoints

### POST /api/v1/demo-sessions

Creates a new anonymous demo session.

Response:

```json
{
  "session": {
    "id": "mf_demo_xxx",
    "status": "active",
    "created_at": "2026-06-14T00:00:00Z",
    "expires_at": "2026-06-17T00:00:00Z"
  }
}
```

### GET /api/v1/demo-sessions/current

Validates/restores the current session based on `X-Demo-Session-Id`.

### POST /api/v1/demo-sessions/reset

Resets workspace data for the current session.

Public reset rule:

```text
Reset does not reset quota or usage.
usage_reset = false
quota_restored = false
```

Development/test quota reset, if ever needed, must be separate from the public Reset Demo endpoint.

Reset responses should clearly report workspace cleanup, usage reset status, and external cleanup warnings.

## 6. Workspace endpoint

### GET /api/v1/workspace

Primary source of truth for the workspace shell.

Response shape:

```json
{
  "session": {},
  "datasets": [],
  "ready_datasets": [],
  "active_dataset": null,
  "dashboard": {
    "dashboard_count": 1,
    "cards": [],
    "cards_used": 0,
    "cards_limit": 8,
    "visible_card_count": 0
  },
  "history": {
    "analysis_runs": [],
    "successful_analysis_runs_used": 0,
    "successful_analysis_runs_limit": 8
  },
  "limits": {
    "retention_days": 3,
    "max_demo_datasets_per_session": 1,
    "max_upload_file_size_mb": 5,
    "max_total_upload_size_mb": 10,
    "max_successful_analysis_runs_per_session": 8,
    "max_dashboard_cards_per_session": 8,
    "preferred_charts_per_analysis": 1,
    "max_charts_per_analysis": 3,
    "dashboards_per_session": 1
  },
  "setup_status": {
    "backend": "available",
    "storage": "not_checked",
    "warehouse": "not_checked",
    "dbt": "not_checked",
    "ai": "not_checked"
  }
}
```

The workspace response must exclude deleted datasets from active selectors and ready datasets, while preserving dashboard/history snapshots.

## 7. Limits endpoint

### GET /api/v1/limits

Returns configured limits plus usage if a session header is present.

Upload limits are storage-based:

```text
max file size safety validation
total upload size per session quota
```

There is no public count-based uploaded CSV quota.

Successful stored uploads increment upload storage usage. Failed validation, preflight, upload, or load does not consume upload storage quota.

## 8. Dataset endpoints

### GET /api/v1/datasets

Returns active datasets for the current session.

### GET /api/v1/datasets/{dataset_id}

Returns dataset detail:

```json
{
  "dataset": {},
  "file": {},
  "schema_preview": {},
  "semantic_preparation": {
    "status": "completed",
    "semantic_columns": [],
    "provider_runs": []
  },
  "question_suggestions": {
    "status": "completed",
    "generated_from": "data_marts",
    "suggestions": [],
    "provider_runs": []
  }
}
```

`semantic_preparation` owns column mapping only.

`question_suggestions` owns post-dbt/Data-Marts question suggestions.

### POST /api/v1/datasets/upload/preflight

Checks a selected CSV before upload.

Validation/readiness checks:

```text
file type
file size safety limit
total upload storage quota
CSV parse
header row
unique normalized headers
at least 2 columns
at least 1 data row
row width consistency
encoding
Snowflake-safe names
S3 readiness
Snowflake readiness
```

Preflight does not upload to S3, create datasets, or load Snowflake.

### POST /api/v1/datasets/upload

Uploads a validated CSV and creates a dataset.

Behavior:

```text
validate file again server-side
verify storage quota
upload to S3
load to Snowflake Warehouse Raw
profile schema
return dataset and next route /demo/data-flow
```

Semantic preparation is not faked. The user may run/save column mapping from Data Flow.

### POST /api/v1/datasets/demo-retail

Adds the Raw Retail Transactions Demo once per session.

Behavior:

```text
check demo not already added
check S3 readiness
check Snowflake readiness
register/load raw demo file
load Warehouse Raw
profile schema
return dataset in schema_review status
```

If already added:

```text
return clear state so frontend disables button: Demo Dataset Added
```

### DELETE /api/v1/datasets/{dataset_id}

Deletes/archives a dataset from active management.

Rules:

```text
Do not delete generated dashboard cards.
Do not delete analysis history snapshots.
Disable rerun/refine for deleted dataset outputs.
Do not decrement upload, analysis, or dashboard-card usage.
Return honest cleanup status for S3/Snowflake/dbt runtime cleanup.
```

## 9. Semantic preparation endpoints

### GET /api/v1/datasets/{dataset_id}/semantic-preparation

Returns current semantic column mappings and provider run records.

### POST /api/v1/datasets/{dataset_id}/semantic-preparation

Runs AI-assisted column mapping suggestions.

Behavior:

```text
use compact column profile context
generate column mapping suggestions only
store semantic_columns
store provider run records
return honest failure if all provider attempts fail
```

This endpoint must not generate suggested questions.

### PATCH /api/v1/datasets/{dataset_id}/semantic-columns

Saves user-approved mapping edits.

The user may save mappings manually without AI suggestions.

## 10. Data Flow and transform endpoints

### GET /api/v1/datasets/{dataset_id}/data-flow

Returns preparation status, dbt evidence, lineage, models, and post-mart question suggestions for a dataset.

Response shape:

```json
{
  "dataset": {},
  "transformation": {},
  "nodes": [],
  "edges": [],
  "artifacts": [],
  "models": {
    "staging": [],
    "intermediate": [],
    "dimensional_model": [],
    "data_mart": []
  },
  "question_suggestions": {
    "status": "completed",
    "generated_from": "data_marts",
    "suggestions": []
  }
}
```

### GET /api/v1/datasets/{dataset_id}/transformation

Alias-style dataset transformation/data-flow evidence endpoint if retained by implementation.

### POST /api/v1/datasets/{dataset_id}/transform

Runs transformation from approved schema mapping through dbt.

Behavior:

```text
save approved mapping snapshot
generate/run dbt staging
run intermediate
build Dimensional Model
build Data Marts
generate/update data flow evidence
mark ready for analysis
generate post-mart question suggestions from mart catalog
return next route /demo/dashboard
```

If transform succeeds, frontend removes Transform button.

If transform fails, frontend keeps Transform button for retry and displays the clear reason.

## 11. Analysis endpoints

### POST /api/v1/analysis-runs

Creates one analysis run.

Request:

```json
{
  "attached_dataset_id": "dataset_123",
  "question": "How is revenue performing?",
  "force_new": false,
  "save_to_dashboard": true
}
```

MVP supports exactly one attached dataset.

Backend must reject:

```text
missing dataset
dataset not in session
dataset deleted
dataset not ready for analysis
analysis quota reached
dashboard-card quota reached when save_to_dashboard=true
```

Response:

```json
{
  "analysis_run": {},
  "charts": [],
  "insights": [],
  "chart_generation_status": "completed",
  "insight_generation_status": "completed",
  "saved_dashboard_card": {},
  "dashboard_card_created": true,
  "reused": false
}
```

Chart and insight data must come from real completed analysis output, not fake samples.

### GET /api/v1/analysis-runs

Returns compact history rows for the current session.

Optional filters may include dataset id if implemented.

### GET /api/v1/analysis-runs/{analysis_run_id}

Returns full evidence for Analysis Detail drawer:

```text
generated SQL
output schema
preview rows
ChartSpecs
charts
insights
AI run details
errors/warnings
```

Only session-owned runs may be returned.

## 12. Dashboard endpoints

### GET /api/v1/dashboard

Returns one dashboard canvas for the current session:

```json
{
  "dashboard_count": 1,
  "cards": [],
  "cards_used": 1,
  "cards_limit": 8,
  "visible_card_count": 1
}
```

### POST /api/v1/dashboard/cards

Creates a result-group dashboard card from a completed analysis run.

Request:

```json
{
  "analysis_run_id": "an_run_xxx"
}
```

Rules:

```text
analysis run must belong to session
analysis run must be completed
analysis run must have real charts
dashboard-card quota must be available
card stores a renderable snapshot
usage increments only after successful card persistence
```

### DELETE /api/v1/dashboard/cards/{card_id}

Archives/removes a card from the visible dashboard.

Rule:

```text
Deleting a successful card does not decrement usage quota.
```

Dashboard card reorder is not a required API unless separately implemented.

## 13. Health endpoints

```text
GET /api/v1/health
GET /api/v1/health/db
```

Additional readiness checks may be service-level or endpoint-backed as implemented.

Health endpoints must not expose secrets.

## 14. Frontend behavior contract

Frontend must not:

```text
show fake successful dataset
show fake successful chart
show fake insights
invent fallback data when API fails
silently switch datasets for AI prompts
show semantic_preparation.suggested_questions
```

Frontend must:

```text
show honest failures
keep Data Flow visible even with no dataset
attach dataset explicitly in analysis requests
read post-mart suggestions from question_suggestions
show dataset deleted badges for preserved outputs
collapse technical analysis details by default
```
