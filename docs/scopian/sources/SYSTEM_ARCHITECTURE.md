# MeshFlow v2 System Architecture

Status: Final approved Phase 0 source document.

This document defines the approved system architecture for the new MeshFlow v2 repository.

## 1. Architecture goal

Build a simple, maintainable, warehouse-first AI analytics engineering demo.

Prioritize:

```text
clarity over feature breadth
small services over broad abstractions
honest failure over fake fallback
explicit dataset attachment over hidden global state
one dashboard over dashboard management
one workspace source of truth over scattered frontend state
```

## 2. High-level architecture

```text
Frontend: Next.js + TypeScript + Tailwind + Recharts
Backend: FastAPI + SQLAlchemy + Alembic
Metadata DB: PostgreSQL / Supabase-compatible Postgres
Storage: AWS S3
Warehouse: Snowflake
dbt: dbt project generation and dbt execution against Snowflake
AI: OpenAI + Gemini task-based router
```

Removed from architecture:

```text
DuckDB
local analytics execution
mock dbt success
mock pipeline success
deterministic fake AI fallback
Plotly as primary dashboard renderer
```

## 3. Runtime data flow

Dataset preparation:

```text
Raw Input
→ S3 object
→ Snowflake Warehouse Raw table
→ warehouse profiling
→ AI semantic column suggestions
→ user schema review
→ dbt Staging
→ dbt Intermediate
→ Dimensional Model
→ Data Marts
→ dataset ready for analysis
```

Analysis workflow:

```text
attached dataset + user question
→ OpenAI analysis plan
→ Gemini fallback if needed
→ backend validates plan
→ backend creates safe Snowflake SELECT
→ Snowflake returns result rows
→ backend validates/generates ChartSpec
→ Gemini insight generation
→ OpenAI fallback if needed
→ dashboard card/result group
→ history/evidence snapshot
```

## 4. Repository shape

```text
meshflow/
  backend/
  frontend/

  docs/
    scopian/
      sources/
        PRODUCT_SCOPE.md
        SYSTEM_ARCHITECTURE.md
        DATA_MODEL.md
        API_CONTRACT.md
        AI_WORKFLOW.md
        WAREHOUSE_DBT_EXECUTION.md
        FRONTEND_UX_SCOPE.md
        DATA_SELECTION_UX.md
        SESSION_LIMITS_AND_NAVIGATION.md
        BUILD_PHASES.md
        MAINTENANCE_RULES.md
        LEGACY_REFERENCE_RULES.md

    prompts/       # local only, gitignored
    progress/      # local only, gitignored
    audit/         # local only, gitignored

  _reference/      # local only, gitignored
    legacy_meshflow/

  README.md
  .gitignore
```

Tracked source-of-truth docs live in:

```text
docs/scopian/sources/
```

Local-only files must stay untracked:

```text
docs/prompts/
docs/progress/
docs/audit/
_reference/
```

## 5. Backend architecture

Codex owns the backend.

Recommended initial backend shape:

```text
backend/
  app/
    main.py
    api/
      v1/
        router.py
        demo_sessions.py
        workspace.py
        datasets.py
        data_flow.py
        analysis_runs.py
        dashboard.py
        history.py
        limits.py
        health.py
    core/
      config.py
      errors.py
      limits.py
      security.py
    db/
      base.py
      session.py
      models/
    schemas/
      common.py
      workspace.py
      dataset.py
      data_flow.py
      analysis.py
      chart.py
      dashboard.py
      provider.py
    services/
      demo_session_service.py
      workspace_service.py
      dataset_service.py
      storage_service.py
      snowflake_service.py
      dbt_service.py
      profile_service.py
      semantic_column_service.py
      data_flow_service.py
      analysis_service.py
      chart_spec_service.py
      insight_service.py
      dashboard_service.py
      provider_router.py
      cleanup_service.py
    providers/
      openai_provider.py
      gemini_provider.py
    tests/
  alembic/
  requirements.txt
```

Do not over-split into too many services early. Start compact and split only when maintenance requires it.

## 6. Frontend architecture

Claude Code owns frontend UI.

Recommended initial frontend shape:

```text
frontend/
  src/
    app/
      page.tsx
      demo/
        upload/page.tsx
        data-flow/page.tsx
        dashboard/page.tsx
        history/page.tsx
    components/
      layout/
      landing/
      upload/
      data-flow/
      dashboard/
      history/
      charts/
      evidence/
      ui/
    lib/
      api.ts
      session.ts
      chartSpec.ts
      theme.ts
    types/
      workspace.ts
      dataset.ts
      dataFlow.ts
      analysis.ts
      chart.ts
```

Do not create a separate frontend route for Analysis Detail in MVP. Use a drawer/modal.

## 7. Main workspace source of truth

The frontend should primarily load:

```text
GET /api/v1/workspace
```

This endpoint should return enough state for:

```text
session
quota
available datasets
ready datasets
dashboard card summary
recent history summary
provider/warehouse readiness summary
navigation continuation
```

This prevents UI state from becoming scattered across too many endpoints.

Detail endpoints are allowed but should not replace the workspace contract as the shell source of truth.

## 8. External service responsibilities

### S3

S3 stores uploaded raw files and any required raw demo file object.

S3 must be checked before upload is enabled.

### Snowflake

Snowflake is the analytical warehouse.

Snowflake handles:

```text
Warehouse Raw tables
dbt model execution
analysis SELECT queries
```

If Snowflake is unavailable, the workflow fails honestly.

### dbt

dbt builds:

```text
Staging
Intermediate
Dimensional Model
Data Marts
```

There is no mock dbt success.

### Metadata DB

PostgreSQL stores:

```text
sessions
datasets
profiles
semantic suggestions
preparation status
analysis runs
chart snapshots
dashboard cards
history
provider runs
usage limits
cleanup runs
```

PostgreSQL is not the analytical warehouse.

## 9. Failure architecture

All failure responses use a consistent shape:

```json
{
  "status": "failed",
  "error_code": "SNOWFLAKE_NOT_READY",
  "failed_step": "warehouse_readiness",
  "message": "Snowflake is not configured, so MeshFlow cannot upload this dataset to Warehouse Raw.",
  "next_action": "Check Snowflake environment variables and try again."
}
```

The system must never convert failure into fake success.

## 10. Agent boundary architecture

Codex owns:

```text
backend
schema
API contract
warehouse/dbt execution
provider routing
analysis workflow
integration
tests
deployment wiring
```

Claude Code owns:

```text
frontend UI
layout
theme
pages
components
Recharts rendering
cards
drawers
states
visual polish
```

Claude Code should not alter backend logic or API contract without approval. If UI needs data not in the API, Claude should report the missing contract.

## 11. Maintainability architecture

MeshFlow v2 should optimize for fast but correct building:

```text
small phases
small commits
simple service boundaries
clear error model
clear page ownership
strict source docs
Scopian for implementation-time revisions
CrossHelix for repo complexity awareness
```

The impressive part should be the product clarity, not repo complexity.
