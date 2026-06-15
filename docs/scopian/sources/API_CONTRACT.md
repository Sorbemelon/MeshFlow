# MeshFlow v2 API Contract

Status: Final approved Phase 0 source document.

This document defines the approved API contract principles for MeshFlow v2. Keep the API small and maintainable.

## 1. API principles

```text
One workspace endpoint powers the app shell.
Backend owns truth and validation.
Frontend does not invent fake successful data.
Analysis requests must explicitly attach a dataset.
Failure responses must be honest and structured.
Deleting datasets preserves generated output snapshots.
```

## 2. Session header

Use a demo session header for workspace API calls:

```text
X-Demo-Session-Id: <public_session_id>
```

This follows the old MeshFlow pattern and keeps frontend session handling simple.

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
DBT_TRANSFORM_FAILED
ANALYSIS_PLAN_FAILED
WAREHOUSE_QUERY_FAILED
INSIGHT_GENERATION_FAILED
CHARTSPEC_VALIDATION_FAILED
LIMIT_REACHED
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
/api/v1/data-flow
/api/v1/analysis-runs
/api/v1/dashboard
/api/v1/history
/api/v1/limits
/api/v1/health
```

Avoid adding many tiny API groups early.

## 5. Demo session endpoints

### POST /api/v1/demo-sessions

Creates a new anonymous demo session.

Response:

```json
{
  "session": {
    "id": "session_internal_id",
    "public_session_id": "mf_demo_xxx",
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

Production rule:

```text
Reset does not reset quota or usage.
```

Development rule:

```text
Reset can reset usage if ALLOW_DEMO_RESET_USAGE=true.
```

## 6. Workspace endpoint

### GET /api/v1/workspace

Primary source of truth for the workspace shell.

Response shape:

```json
{
  "session": {
    "public_session_id": "mf_demo_xxx",
    "status": "active",
    "expires_at": "2026-06-17T00:00:00Z"
  },
  "limits": {
    "uploaded_datasets": {"used": 0, "limit": 1},
    "analysis_runs": {"used": 2, "limit": 10},
    "dashboard_cards": {"used": 3, "limit": 8}
  },
  "datasets": [
    {
      "id": "dataset_123",
      "name": "Raw Retail Transactions Demo",
      "source_type": "raw_retail_demo",
      "status": "ready",
      "is_demo_dataset": true,
      "deleted": false,
      "ready_for_analysis": true
    }
  ],
  "ready_datasets": [],
  "dashboard_summary": {
    "card_count": 0,
    "max_cards": 8
  },
  "recent_analysis_runs": [],
  "readiness": {
    "s3": "ready",
    "snowflake": "ready",
    "dbt": "ready",
    "openai": "unknown",
    "gemini": "unknown"
  },
  "continue_destination": "/demo/upload"
}
```

## 7. Dataset endpoints

### GET /api/v1/datasets

Returns datasets for the current session, including deleted markers where needed.

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
generate semantic suggestions and suggested questions
return dataset in schema_review status
```

If already added:

```text
return clear state so frontend disables button: Demo Dataset Added
```

### POST /api/v1/datasets/validate-upload

Validates a selected CSV before upload.

Request: multipart/form-data or preflight metadata plus sample as implementation allows.

Validation checks:

```text
file type
file size
CSV parse
header row
unique normalized headers
at least 2 columns
at least 1 data row
row width consistency
encoding
Snowflake-safe names
```

### GET /api/v1/datasets/upload-readiness

Checks S3 and Snowflake readiness before enabling upload.

Response:

```json
{
  "status": "ready",
  "checks": {
    "s3": {"status": "ready"},
    "snowflake": {"status": "ready"}
  }
}
```

### POST /api/v1/datasets/upload

Uploads a validated CSV and creates a dataset.

Behavior:

```text
validate file again server-side
upload to S3
load to Snowflake Warehouse Raw
profile schema
generate semantic suggestions and suggested questions
return dataset and next route /demo/data-flow
```

### DELETE /api/v1/datasets/{dataset_id}

Deletes/archives a dataset from active management.

Rules:

```text
Do not delete generated dashboard cards.
Do not delete analysis history snapshots.
Disable rerun/refine for deleted dataset outputs.
```

## 8. Data Flow endpoints

### GET /api/v1/data-flow/{dataset_id}

Returns preparation status, tabs, profiles, mappings, dbt evidence, and lineage for a dataset.

Response shape:

```json
{
  "dataset": {},
  "preparation_status": {
    "overall": "schema_review_required",
    "steps": [
      {"layer": "Raw Input", "status": "completed", "color": "emerald"},
      {"layer": "Warehouse Raw", "status": "completed", "color": "emerald"},
      {"layer": "Staging", "status": "not_started", "color": "slate"},
      {"layer": "Intermediate", "status": "not_started", "color": "slate"},
      {"layer": "Dimensional Model", "status": "not_started", "color": "slate"},
      {"layer": "Data Marts", "status": "not_started", "color": "slate"}
    ]
  },
  "schema_preview": [],
  "warehouse_raw": {},
  "transformations": [],
  "dimensional_model_and_marts": {},
  "lineage": {}
}
```

### PATCH /api/v1/data-flow/{dataset_id}/schema-mapping

Saves user edits to semantic mappings.

### POST /api/v1/data-flow/{dataset_id}/transform

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
generate dataset-specific suggested questions if not already available
return next route /demo/dashboard
```

If transform succeeds, frontend removes Transform button.

If transform fails, frontend keeps Transform button for retry and displays the clear reason.

## 9. Analysis endpoints

### POST /api/v1/analysis-runs

Creates one analysis run.

Request:

```json
{
  "attached_dataset_id": "dataset_123",
  "question": "How is revenue performing?"
}
```

Future-ready shape may support:

```json
{
  "attached_dataset_ids": ["dataset_123"],
  "question": "How is revenue performing?"
}
```

MVP supports exactly one attached dataset.

Backend must reject:

```text
missing dataset
dataset not in session
dataset deleted
dataset not ready for analysis
```

Response:

```json
{
  "analysis_run": {},
  "result_group": {
    "dataset": {},
    "insight_summary": {},
    "charts": []
  },
  "provider_summary": {},
  "evidence_available": true
}
```

### GET /api/v1/analysis-runs/{analysis_run_id}

Returns full evidence for Analysis Detail drawer.

## 10. Dashboard endpoints

### GET /api/v1/dashboard

Returns one dashboard canvas for the current session.

### POST /api/v1/dashboard/cards

Adds a chart card or result group card from an analysis run.

### PATCH /api/v1/dashboard/cards/reorder

Updates card order.

### DELETE /api/v1/dashboard/cards/{card_id}

Removes a card from the visible dashboard.

Rule:

```text
Deleting a successful card does not decrement usage quota.
```

## 11. History endpoints

### GET /api/v1/history

Returns analysis history for the current session.

Supports optional filters:

```text
dataset_id
status
```

### GET /api/v1/history/{analysis_run_id}

May alias Analysis Detail if needed.

## 12. Health endpoints

```text
GET /api/v1/health
GET /api/v1/health/db
GET /api/v1/health/s3
GET /api/v1/health/snowflake
GET /api/v1/health/dbt
GET /api/v1/health/ai
```

Health endpoints should not expose secrets.

## 13. Frontend behavior contract

Frontend must not:

```text
show fake successful dataset
show fake successful chart
show fake insights
invent fallback data when API fails
silently switch datasets for AI prompts
```

Frontend must:

```text
show honest failures
show Upload Dataset button when no dataset exists
keep Data Flow visible even with no dataset
attach dataset explicitly in analysis requests
show dataset deleted badges for preserved outputs
collapse non-analysis technical details by default
```
