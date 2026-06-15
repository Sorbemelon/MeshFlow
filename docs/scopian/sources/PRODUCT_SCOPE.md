# MeshFlow v2 Product Scope

Status: Final approved Phase 0 source document.

This document is a Scopian source. It defines the approved product scope for MeshFlow v2 and supersedes older MeshFlow prototype assumptions.

## 1. Product identity

MeshFlow v2 is a warehouse-first AI analytics engineering demo workspace.

It turns raw dataset files into explainable analytical outputs through:

```text
Raw Input
→ Warehouse Raw
→ Staging
→ Intermediate
→ Dimensional Model
→ Data Marts
→ AI-generated analysis
→ Dashboard charts with evidence
```

Correct positioning:

```text
MeshFlow is a warehouse-first AI analytics engineering demo workspace that prepares raw datasets through S3, Snowflake, and dbt, then uses an AI Analytics Engineer to generate validated analysis outputs, modern dashboard cards, insights, and explainable evidence.
```

MeshFlow v2 is not positioned as a production SaaS yet. It is a portfolio-grade demo product that demonstrates AI engineering, analytics engineering, data lineage, warehouse-backed execution, dbt-style modeling, and maintainable full-stack architecture.

## 2. Rebuild reason

MeshFlow v2 uses a new repository because the previous MeshFlow prototype contains assumptions that are now rejected:

```text
Retail Star Schema Demo as input
local/demo execution paths
mock dbt success
mock pipeline success
deterministic fake fallback
Plotly-first chart rendering
too many primary pages
separate AI Analytics Engineer page
separate dashboard management pages
readiness-only Snowflake/dbt UX
```

The old repo is reference-only and must not become active source-of-truth.

## 3. Core product promise

MeshFlow should show that AI analytics can be:

```text
useful
visual
warehouse-backed
validated
explainable
connected to a real data preparation flow
```

It should not feel like:

```text
Upload CSV → ask chatbot → random chart
```

It should feel like:

```text
Raw dataset → warehouse/dbt model → data mart → AI analysis plan → Snowflake result → ChartSpec → dashboard → evidence
```

## 4. Final data preparation layers

Use these exact layer names in the Data Flow preparation rail:

```text
Raw Input
→ Warehouse Raw
→ Staging
→ Intermediate
→ Dimensional Model
→ Data Marts
```

Do not include these in the preparation rail:

```text
Analysis Outputs
Dashboard
```

Those are not data preparation steps. They may appear in History, Dashboard, or evidence drawers, but not in the preparation status flow.

## 5. Dataset scope

### 5.1 Raw Retail Transactions Demo

The curated demo dataset is a raw input file, not a prebuilt star schema.

Approved name:

```text
Raw Retail Transactions Demo
```

Rejected name:

```text
Retail Star Schema Demo
```

The demo should show MeshFlow transforming raw retail transactions into a Dimensional Model and Data Marts.

Expected raw file shape may include denormalized business columns such as:

```text
order_id
order_date
customer_id
customer_name
customer_segment
product_id
product_name
product_category
store_id
store_name
store_region
quantity
unit_price
discount_amount
revenue
cost
payment_method
```

The demo dataset can be added only once per session.

### 5.2 Uploaded CSV MVP

The first upload MVP supports one CSV file per uploaded dataset.

The architecture may remain future-ready for multiple files, but the UI must be honest:

```text
MVP: one CSV file
Future: up to three files per dataset
```

## 6. Workspace scope

MeshFlow v2 has a compact landing page and a workspace session with four pages.

Routes:

```text
/
/demo/upload
/demo/data-flow
/demo/dashboard
/demo/history
```

Workspace pages:

```text
Upload Dataset
Data Flow
Dashboard
History
```

Do not create separate primary pages for:

```text
AI Analytics Engineer
Dashboard list
Dashboard detail
Dashboard edit
Pipeline
Lineage Explorer
Snowflake Readiness
dbt Artifacts
Analysis Detail
```

Analysis detail should be a drawer or modal.

## 7. Dashboard scope

There is one dashboard per session.

No dashboard management in MVP:

```text
no dashboard list
no create dashboard flow
no delete dashboard flow
no separate edit page
```

The dashboard can contain cards from multiple datasets. Each card or generated result group belongs to exactly one dataset in MVP and must display a dataset badge.

AI analysis generation must explicitly attach a dataset. It must not rely on hidden global selected dataset state.

## 8. AI scope

AI is used for three task groups:

```text
semantic column suggestions and dataset-specific suggested questions
analysis plan generation
insight generation after result data exists
```

AI must return structured output where applicable.

AI must not directly control final product behavior. Backend validation decides what is accepted.

## 9. Chart scope

Use a neutral backend-owned ChartSpec rendered by frontend Recharts components.

MVP chart types:

```text
KPI
Line
Bar
Horizontal Bar
Table
```

Optional later:

```text
Area
Donut
Scatter
```

Prefer one chart per analysis. Generate up to three charts only when one chart cannot fully answer the prompt.

## 10. Strict non-goals

Do not build:

```text
user auth
team accounts
billing
multi-tenant SaaS hardening
DuckDB/local analytics execution
mock success fallback
production sensitive-data support
advanced lineage graph engine
multi-dataset analysis in MVP
background worker system unless required
complex multi-file relationship editor in MVP
provider billing dashboard
```

## 11. Success criteria

MeshFlow v2 is successful if:

```text
The repo is easy to maintain.
The workflow is easy to understand.
The UI is compact and polished.
Raw retail data becomes warehouse/dbt models.
Data Flow clearly shows preparation evidence.
Dashboard stays focused on charts and insights.
History preserves evidence.
AI outputs are validated.
Failures are honest.
No fake success path exists.
Codex and Claude roles stay separated.
```
