# MeshFlow v2 Phase 0 Starter Pack

This starter pack contains the approved Phase 0 source-of-truth docs for building MeshFlow v2 in a new repository.

## Required tracked source docs

Place these files under:

```text
docs/scopian/sources/
```

These source docs are intended to be committed to the new MeshFlow v2 repo and used as Scopian sources.

## Required local-only folders

Create these folders locally if needed, but do not commit them:

```text
docs/prompts/
docs/progress/
docs/audit/
_reference/
```

The legacy MeshFlow repo may be cloned locally under:

```text
_reference/legacy_meshflow/
```

It must remain untracked and reference-only.

## Phase 0 rule

Phase 0 is docs and repo setup only. Do not implement backend or frontend product logic yet.

## Agent ownership

Codex owns backend, data model, API, S3, Snowflake, dbt, AI provider routing, integration, tests, and deployment wiring.

Claude Code owns frontend UI only: landing, workspace shell, sidebar, Upload Dataset, Data Flow, Dashboard, History, chart cards, Recharts renderer, drawers, states, and visual polish.
