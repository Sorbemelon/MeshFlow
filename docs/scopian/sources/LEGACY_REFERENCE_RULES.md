# MeshFlow v2 Legacy Reference Rules

Status: Final approved Phase 0 source document.

This document defines how the old MeshFlow repo may be used as reference.

## 1. Core rule

The old MeshFlow repo is reference-only.

It must not become active source-of-truth.

Recommended local path:

```text
_reference/legacy_meshflow/
```

This folder must be gitignored.

Do not commit:

```text
_reference/
legacy repo files
reference repo snapshots
prompt/progress/audit files
```

## 2. Why v2 uses a new repo

The old MeshFlow prototype contains assumptions rejected by v2:

```text
Retail Star Schema Demo as input
local/mock execution paths
dbt mock mode
deterministic fake fallback
Plotly as primary chart renderer
too many primary pages
separate AI Analytics Engineer page
separate dashboard management/edit routes
separate readiness/tool pages
```

These assumptions can confuse implementation if copied directly.

## 3. What may be reused conceptually

The old repo can be referenced for:

```text
FastAPI + Next.js split idea
demo session idea
session header pattern
reset demo idea
quota/limits idea
cleanup/retention idea
old visual theme direction
deployment lessons
selected health check patterns
selected S3/Snowflake/dbt snippets after review
```

Conceptual reuse does not mean copying architecture wholesale.

## 4. What must not be copied as-is

Do not carry forward:

```text
Retail Star Schema Demo wording
local storage as successful path
local analytics engine
DuckDB
mock pipeline success
mock dbt success
deterministic fallback provider
fake chart data
fake insight
Plotly-first chart model
many-route workspace structure
separate AI Analytics Engineer page
dashboard list/detail/edit route structure
pipeline/readiness page structure
```

## 5. Actual old MeshFlow theme reference

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

Do not use the previously incorrect blue/cyan/teal-only theme.

## 6. New frontend structure replaces old routes

v2 routes:

```text
/
/demo/upload
/demo/data-flow
/demo/dashboard
/demo/history
```

Do not recreate old route sprawl.

## 7. Reference review method

When using old code as reference:

```text
1. Identify the exact old behavior.
2. Check whether it conflicts with v2 source docs.
3. Reuse only if it supports approved scope.
4. Rewrite into v2 architecture instead of copy-pasting blindly.
5. If uncertain, ask or record a Scopian buffer decision during implementation.
```

## 8. CrossHelix and Scopian exclusion

CrossHelix should not map `_reference/legacy_meshflow/` as active source.

Scopian source docs should not include the old repo as source-of-truth.

The old repo is evidence/reference only.

## 9. Safe reference examples

Safe:

```text
Use old status badge color idea.
Use old reset demo UX copy as inspiration.
Use old deployment config lessons after checking v2 constraints.
Use old health endpoint idea.
```

Unsafe:

```text
Copy old mock data fallback.
Copy old dashboard route design.
Copy old Plotly renderer.
Copy old Retail Star Schema Demo language.
Copy old local execution logic.
```

## 10. Final rule

If old code conflicts with v2 source docs, v2 source docs win.
