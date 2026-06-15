# MeshFlow v2 Build Phases

Status: Final approved Phase 0 source document.

This document defines the approved build sequence. Move fast while maintaining quality, correctness, and maintainability.

## 1. Operating loop

For each phase:

```text
1. Confirm Scopian source scope for the phase.
2. Use CrossHelix to inspect current repo map.
3. Give Codex or Claude Code a narrow role-specific prompt.
4. Implement only the phase scope.
5. Run tests/checks.
6. Refresh CrossHelix.
7. Record actual scope conflicts with Scopian buffer.
8. Commit with CentralDocs-style conventional commit.
```

Do not use Scopian buffer for initial source docs. Buffer is for implementation-time changes/conflicts/revisions.

## 2. Commit style

Use CentralDocs-style conventional commits.

Examples:

```text
chore: initialize meshflow v2 repo skeleton
docs: add scopian source scope for warehouse-first rebuild
feat: add demo session workspace contract
feat: add upload readiness validation
feat: add data flow preparation rail
feat: add warehouse-only dbt transformation flow
feat: add chartspec renderer contract
fix: block upload until s3 and snowflake readiness pass
fix: preserve dashboard cards after dataset deletion
test: cover invalid csv upload validation
refactor: simplify dashboard card state model
```

Rules:

```text
small commits
one logical change per commit
commit source docs and code
do not commit prompts/progress/audit/reference repo
```

## 3. Phase 0 — Source docs and repo setup

Owner: user + assistant docs generation.

Deliverables:

```text
new repo created
.gitignore added
docs/scopian/sources/ created
Phase 0 source docs added
old MeshFlow cloned locally into _reference/legacy_meshflow/ if desired
_reference/ remains untracked
CrossHelix initialized after skeleton exists
Scopian source view created from docs/scopian/sources/
```

No product coding.

Acceptance:

```text
prompts/progress/audit/reference paths are ignored
source docs are in docs/scopian/sources/
old repo is not tracked
```

Suggested commit:

```text
docs: add meshflow v2 scopian source docs
```

## 4. Phase 1 — Backend skeleton

Owner: Codex.

Scope:

```text
FastAPI app
settings
health endpoints
error model
database connection
SQLAlchemy/Alembic skeleton
basic test structure
```

No business logic yet.

Acceptance:

```text
backend starts locally
health endpoint passes
config loads from env
basic tests pass
no warehouse/dbt/AI fake success paths
```

Suggested commit:

```text
chore: initialize backend skeleton
```

## 5. Phase 2 — Frontend skeleton

Owner: Claude Code.

Scope:

```text
Next.js + TypeScript + Tailwind
actual MeshFlow slate/indigo theme tokens
compact landing shell
workspace shell
shared left sidebar
four route pages
empty/loading/error states
```

No fake data success.

Acceptance:

```text
landing renders
workspace routes render
theme direction matches old MeshFlow slate/indigo style
sidebar contains only Upload Dataset, Data Flow, Dashboard, History
no dashboard list/edit route
```

Suggested commit:

```text
chore: initialize frontend workspace shell
```

## 6. Phase 3 — Session and workspace contract

Owner: Codex for backend; Claude Code for UI wiring.

Codex scope:

```text
demo session create/current/reset
workspace endpoint
quota summary
expired session handling
cleanup hooks skeleton
```

Claude scope:

```text
Launch/Continue Session CTA
route guard UI
session status in sidebar
reset dialog shell
```

Acceptance:

```text
Launch Demo creates session
Continue Session restores active session
expired session shows Start New Session
workspace endpoint powers shell
production reset does not reset usage
```

Suggested commits:

```text
feat: add demo session workspace contract
feat: wire workspace session shell
```

## 7. Phase 4 — Upload and readiness

Owner: Codex for backend; Claude Code for UI.

Codex scope:

```text
file validation endpoint
S3 readiness check
Snowflake readiness check
upload endpoint skeleton
S3 upload
Snowflake raw load
honest failure model
```

Claude scope:

```text
Upload Dataset page
Raw Retail Demo card
Browse → Upload button behavior
readiness loading state
validation error UI
Demo Dataset Added disabled state
```

Acceptance:

```text
Upload button starts as Browse
button becomes Upload after file selection
Upload disabled during validation/readiness
invalid CSV shows clear reason
S3/Snowflake failure blocks upload honestly
Raw Retail Demo can be added once
successful upload navigates to Data Flow
```

Suggested commits:

```text
feat: add upload validation and warehouse readiness
feat: build upload dataset page
```

## 8. Phase 5 — Schema preview and semantic suggestions

Owner: Codex + Claude Code.

Codex scope:

```text
warehouse raw profiling
column_profiles storage
Gemini three-lane provider setup
OpenAI fallback
semantic suggestions at temperature 0.1
suggested dataset questions
schema mapping API
```

Claude scope:

```text
Schema Preview tab
editable mappings
confidence/status badges
Transform button states
```

Acceptance:

```text
profile displays raw column, detected type, suggested name, semantic role, confidence, sample values
user can edit mapping
low-confidence fields show Needs review
no fake suggestions if providers fail
```

Suggested commits:

```text
feat: add semantic schema suggestions
feat: build schema preview mapping UI
```

## 9. Phase 6 — dbt transformation and Data Flow

Owner: Codex + Claude Code.

Codex scope:

```text
dbt generation/execution for Staging
Intermediate
Dimensional Model
Data Marts
preparation run status
lineage nodes/edges
honest dbt failure
```

Claude scope:

```text
Data Flow left rail
dataset selector with bin icons
status colors
automated evidence tabs
Dimensional Model & Data Marts tab
Upload Dataset button when no dataset
```

Acceptance:

```text
Data Flow status rail has only Raw Input through Data Marts
dataset selector is in left rail
no Analysis Outputs/Dashboard in prep status
Transform removed after success
Transform remains after failure for retry
ready dataset defaults to Dimensional Model & Data Marts tab
```

Suggested commits:

```text
feat: add warehouse dbt transformation flow
feat: build data flow preparation rail
```

## 10. Phase 7 — Analysis workflow

Owner: Codex + Claude Code.

Codex scope:

```text
analysis run endpoint
attached_dataset_id required
OpenAI analysis plan → Gemini fallback
plan validation
Snowflake SELECT
ChartSpec generation/validation
Gemini insight → OpenAI fallback
provider runs
analysis/chart/insight snapshots
```

Claude scope:

```text
AI Analytics Engineer panel
explicit attached dataset selector
suggested questions
analysis state UI
generated result group display
```

Acceptance:

```text
AI request includes attached_dataset_id
backend rejects missing/deleted/not-ready dataset
one chart preferred, max three
insight generated only after Snowflake result
no mock output on provider/query failure
```

Suggested commits:

```text
feat: add analysis run orchestration
feat: build ai analytics engineer panel
```

## 11. Phase 8 — Dashboard and History

Owner: Codex + Claude Code.

Codex scope:

```text
one dashboard canvas
card snapshots
dashboard card add/remove/reorder
history endpoint
analysis detail evidence
dataset deletion preservation behavior
```

Claude scope:

```text
editable dashboard canvas
chart cards
result group cards
collapsed details
History page
Analysis Detail drawer
Dataset deleted badges
```

Acceptance:

```text
dashboard has no list/edit routes
cards can come from multiple datasets
each card shows dataset badge
technical details collapse by default
deleting dataset preserves cards/history
history detail shows evidence
```

Suggested commits:

```text
feat: add dashboard card snapshots
feat: build dashboard and history evidence UI
```

## 12. Phase 9 — Polish and portfolio package

Owner: Codex + Claude Code + user.

Scope:

```text
README
screenshots
demo script
architecture explanation
deployment notes
resume bullets
LinkedIn copy
final cleanup
```

Acceptance:

```text
README accurately states warehouse-only architecture
no fake success claims
screenshots show compact workflow
portfolio copy is clear
```

Suggested commit:

```text
docs: add meshflow v2 portfolio package
```

## 13. Quality gates

Minimum checks by phase:

```text
backend tests pass
frontend build/lint passes when available
workspace route behavior manually checked
no ignored local files accidentally tracked
CrossHelix map refreshed
Scopian buffer used only if actual implementation conflict appears
```

## 14. Speed principle

Move fast by keeping phases narrow.

Maintain quality by enforcing:

```text
no fake success
no hidden dataset state
no unnecessary primary pages
no over-complex service split
clear error model
small commits
role boundaries
```
