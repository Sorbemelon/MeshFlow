# MeshFlow v2 Frontend UX Scope

Status: Final approved Phase 0 source document.

This document defines the approved frontend UX scope. Claude Code owns frontend UI implementation only.

## 1. Frontend goal

Build a compact, polished, maintainable portfolio-grade UI.

The UI should make the workflow obvious:

```text
Upload raw data
-> review schema
-> transform with warehouse/dbt
-> ask AI Analytics Engineer
-> add results to one dashboard
-> inspect history/evidence
```

Do not overbuild.

## 2. Theme direction

Use the actual old MeshFlow theme direction:

```text
dark slate shell/sidebar
indigo primary accent
white/light cards
slate borders
slate text
multi-color data-flow stage accents
emerald/blue/amber/red/indigo status colors
```

Do not use a blue/cyan/teal-only theme.

Recommended tokens:

```text
shell: slate-900 / slate-800
primary: indigo
surface: white / slate-50
border: slate-200 / slate-800
text: slate-900 / slate-700 / slate-500
success: emerald
running: blue
warning: amber
danger: red
provider/auto: indigo
archived: slate
```

## 3. Routes

Final frontend routes:

```text
/
/demo/upload
/demo/data-flow
/demo/dashboard
/demo/history
```

Do not create primary routes for:

```text
AI Analytics Engineer
Dashboard list
Dashboard edit
Pipeline
Lineage Explorer
Snowflake Readiness
dbt Artifacts
Analysis Detail
```

Analysis Detail should be a drawer/modal.

## 4. Landing page

Route:

```text
/
```

Landing should be one compact page similar in spirit to CentralDocs.

Sections:

```text
Hero
Compact architecture strip
Key capabilities
4-step workflow
Tech stack
Launch / Continue Session CTA
```

Architecture strip:

```text
Raw Input
-> S3
-> Snowflake
-> dbt
-> Dimensional Model
-> Data Marts
-> AI Analysis
-> Dashboard
```

CTA behavior:

```text
No session: Launch Demo
Active session: Continue Session
Reset pending: show Resetting... and disable CTA
Reset complete: Launch Demo
Expired session: Start New Session
```

After Reset Demo is confirmed from the workspace, the UI should navigate to the Landing page immediately. Landing shows reset-pending status while the backend reset is running. When reset completes, Launch Demo should reuse the valid reset/empty session and route to `/demo/upload`; it must not create a fresh quota-bypassing session.

## 5. Workspace shell

Use a shared left sidebar for workspace pages.

Sidebar:

```text
MeshFlow
Workspace Session

Upload Dataset
Data Flow
Dashboard
History

Session status
Reset Demo
```

The sidebar should be compact, clear, and persistent across workspace pages.

## 6. Upload Dataset page

Route:

```text
/demo/upload
```

Purpose:

```text
workspace home + raw demo selection + CSV upload
```

Sections:

```text
Raw Retail Demo card
Upload CSV card
Demo Walkthrough/right-side guidance
storage-based limits/status where useful
```

### Raw Retail Demo card

Name:

```text
Raw Retail Transactions Demo
```

Button states:

```text
Before added: Use Demo Dataset
After added: Demo Dataset Added, disabled
Optional secondary action: Open Data Flow
```

### Upload CSV card

Button behavior:

```text
Initial: Browse
After selecting file: Upload
Checking: Upload disabled + loading icon
Ready: Upload enabled
Failed validation/readiness: Upload disabled + clear error
Uploading: Uploading... disabled
```

After successful upload:

```text
navigate to /demo/data-flow
show Schema Preview
```

## 7. Data Flow page

Route:

```text
/demo/data-flow
```

Layout:

```text
Left narrow rail:
  Dataset selector
  Preparation status

Right main area:
  Data Flow tabs/details
```

Dataset selector belongs in the left rail so users clearly see which dataset the status belongs to.

If no dataset exists:

```text
show no-dataset empty state
offer navigation back to /demo/upload outside the selector
keep page visible
keep tabs visible but disabled/inactive where appropriate
```

Preparation status rail steps:

```text
Raw Input
Warehouse Raw
Staging
Intermediate
Dimensional Model
Data Marts
```

Do not show Analysis Outputs or Dashboard in the preparation status rail.

Data Flow tabs:

```text
Schema Preview
Warehouse Raw
Transformations
Dimensional Model & Data Marts
```

Default tab:

```text
not processed: Schema Preview
ready: Dimensional Model & Data Marts
no dataset: Schema Preview empty state
```

Schema Preview is the only tab with active preparation editing.

Transform button rules:

```text
Show when schema review is required.
Show when previous transformation failed.
Disable while transforming.
Remove after successful transformation.
```

Automated tabs should be compact evidence only. No processing buttons.

## 8. Dashboard page

Route:

```text
/demo/dashboard
```

The dashboard page contains one dashboard only.

No dashboard management:

```text
no dashboard list
no create dashboard flow
no delete dashboard flow
no separate edit route
```

Layout:

```text
Left panel:
  AI Analytics Engineer

Right panel:
  Editable dashboard canvas
```

If no ready dataset exists:

```text
show Upload Dataset button
AI panel disabled
message: Prepare a dataset before asking the AI Analytics Engineer.
```

AI input must explicitly attach a dataset:

```text
Attach dataset: [dataset dropdown]
Question input
Suggested questions for attached ready dataset after Data Marts exist
```

Do not rely on hidden global selected dataset.

Dashboard cards can come from multiple datasets. Each card must show a dataset badge.

Visible by default:

```text
title
chart
direct insight
dataset badge
source model badge
metric/dimension short footer
primary actions
```

Collapsed by default:

```text
SQL
ChartSpec JSON
provider chain
lineage
grain explanation
warehouse/dbt details
raw preview rows
column mapping details
```

## 9. History page

Route:

```text
/demo/history
```

Each history item shows:

```text
question
dataset badge
status
decision type
chart count
source model
provider mode
created time
View Detail
```

Analysis detail opens as drawer/modal.

If source dataset was deleted, show:

```text
Dataset deleted
```

History remains readable because snapshots are stored.

## 10. Chart renderer

Use:

```text
ChartSpec
-> Recharts renderer
-> Tailwind/shadcn-style chart cards
```

Do not use Plotly as the main renderer.

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

## 11. Status colors

Use consistent status colors:

```text
Completed / ready: emerald
Running / checking: blue
Waiting / not started: slate
Needs review: amber
Setup required: amber or indigo
Failed: red
Provider/AI generated: indigo
Deleted/archived: slate
Current/selected: indigo
```

## 12. Claude Code boundaries

Claude Code owns:

```text
frontend UI
pages
layout
theme
Recharts components
loading/error/empty states
cards
drawers
visual polish
```

Claude Code must not modify:

```text
backend service logic
database schema
provider router
Snowflake/dbt logic
API contract without approval
Scopian source docs unless explicitly asked
```

If API data is missing, Claude should report the missing contract rather than invent fake frontend data.

## 13. No fake UI success

Frontend must not show:

```text
fake successful dataset
fake chart data
fake insight
fake fallback dashboard
fake generated suggestions
```

Show honest failures and setup-required messages.
