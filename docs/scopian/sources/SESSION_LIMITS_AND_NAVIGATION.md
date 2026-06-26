# MeshFlow v2 Session, Limits, Cleanup, and Navigation

Status: Final approved Phase 0 source document.

This document defines demo session behavior, quota rules, cleanup, reset behavior, and route restrictions.

## 1. Session model

MeshFlow v2 uses anonymous demo sessions.

Session identity is stored in the browser and sent to backend using:

```text
X-Demo-Session-Id
```

The old MeshFlow session pattern can be used as reference, but v2 must keep behavior simple and honest.

## 2. Landing CTA behavior

Landing route:

```text
/
```

CTA labels:

```text
No session: Launch Demo
Active session: Continue Session
Expired session: Start New Session
```

Continue destination:

```text
if dataset is in schema review/transformation -> /demo/data-flow
else if dashboard has cards -> /demo/dashboard
else -> /demo/upload
```

## 3. Workspace routes

Routes requiring an active session:

```text
/demo/upload
/demo/data-flow
/demo/dashboard
/demo/history
```

If no session:

```text
redirect to landing
show Launch Demo
```

If expired:

```text
show expired state
clear local session
show Start New Session
```

## 4. Page access behavior

### Upload Dataset

Accessible whenever session is active.

No dataset required.

### Data Flow

Accessible whenever session is active.

If no dataset:

```text
show no-dataset empty state with a route back to /demo/upload
show empty Schema Preview
keep page visible
keep later tabs disabled/inactive
```

### Dashboard

Accessible whenever session is active.

If no ready dataset:

```text
show Upload Dataset button
AI panel disabled
message: Prepare a dataset before asking the AI Analytics Engineer.
```

### History

Accessible whenever session is active.

If no analysis:

```text
show empty state
```

## 5. Production limits

Recommended production limits:

```text
Retention: 3 days
Raw Retail Demo: can be added once per session
Uploaded CSVs: controlled by storage quota, not public count quota
Files: MVP = 1 CSV file per uploaded dataset
Future files: up to 3 files per dataset
Upload size: 5 MB per file
Total upload size: 10 MB per session
Analysis: 8 successful analysis runs per session
Charts: default 1 chart per analysis, max 3
Dashboard: 1 dashboard per session
Dashboard cards: max 8 successful cards
History: retained until reset or session expiry
```

## 6. Usage counting rules

Successful processing increments product usage.

Examples:

```text
successful upload/load increments stored upload size usage
successful analysis increments analysis usage
successful dashboard card creation increments dashboard card usage
```

Failed validation, preflight, upload, or load does not consume upload storage quota.

Failures do not consume product usage quota.

Failed attempts may still be tracked for abuse/rate-limit protection.

Deleting successful components does not reduce usage.

## 7. Reset Demo behavior

Production:

```text
Reset Demo does not reset quota or usage.
Deleting components does not reduce quota or usage.
```

Development:

```text
Reset Demo can reset quota and usage.
```

Config:

```text
ALLOW_DEMO_RESET_USAGE=true   # development
ALLOW_DEMO_RESET_USAGE=false  # production
```

Reset should clear:

```text
workspace datasets
dataset files metadata
S3 uploaded objects
Snowflake session schemas/tables
generated dbt artifacts/metadata
semantic column mappings
question suggestions
data flow nodes/edges
analysis outputs
dashboard cards
history
selected dataset UI state
```

Reset should not clear in production:

```text
quota usage
abuse/rate-limit attempt logs required for protection
```

After reset:

```text
navigate to /demo/upload
```

## 8. Cleanup after expiry

Use cleanup behavior similar to previous MeshFlow and CentralDocs.

Retention:

```text
3 days
```

Cleanup should remove:

```text
expired demo session workspace data
dataset metadata
S3 uploaded objects
Snowflake session schemas/tables
generated dbt artifacts/metadata
semantic column mappings
question suggestions
data flow nodes/edges
analysis outputs
dashboard cards
history records
temporary files
```

Production quota/abuse logs may remain for the quota window.

Cleanup execution model:

```text
opportunistic cleanup on session create/current-session calls
scheduled cleanup endpoint/script
cleanup logs
safe retries for failed cleanup
```

## 9. Upload navigation behavior

Upload Dataset page flow:

```text
Browse
-> user selects file
-> frontend validates file
-> backend validates file
-> check storage quota
-> check S3 readiness
-> check Snowflake readiness
-> enable Upload
-> Upload clicked
-> S3 upload
-> Snowflake Warehouse Raw load
-> profile schema
-> Schema Preview with deterministic profile
-> navigate to /demo/data-flow
-> show Schema Preview
```

If validation/readiness fails:

```text
stay on Upload Dataset
show clear reason
Upload disabled
```

## 10. Transform navigation behavior

Data Flow Schema Preview flow:

```text
user optionally generates semantic column mapping suggestions
-> user reviews/edits/saves mapping
-> Transform clicked
-> dbt runs all preparation layers
-> question suggestions generated from Data Marts
-> success: navigate to /demo/dashboard
-> failure: stay on /demo/data-flow and keep Transform available for retry
```

If successful:

```text
Transform button removed
Dataset Ready for Analysis shown
Open Dashboard shown
```

## 11. History and deletion behavior

Deleting dataset/card does not remove successful history snapshots.

History can show:

```text
Dataset deleted
```

but still render:

```text
question
chart snapshot
insight snapshot
provider evidence
SQL snapshot
```

## 12. Friendly limit errors

Limit error example:

```json
{
  "status": "failed",
  "error_code": "LIMIT_REACHED",
  "failed_step": "quota_check",
  "message": "This demo session has reached the analysis run limit.",
  "next_action": "You can reset the workspace, but usage quota will not reset in production."
}
```

Do not silently hide limits.
