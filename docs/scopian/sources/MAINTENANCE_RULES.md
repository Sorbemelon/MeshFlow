# MeshFlow v2 Maintenance Rules

Status: Final approved Phase 0 source document.

This document defines maintainability rules for MeshFlow v2. The repo should be easy to understand and maintain in the future.

## 1. Primary maintenance goal

Build MeshFlow v2 as a small, boring, high-quality product repo.

The impressive part should be product clarity:

```text
raw data
→ warehouse/dbt preparation
→ dimensional model
→ data marts
→ validated AI analysis
→ dashboard
→ evidence
```

Not repo complexity.

## 2. Complexity budget

Keep the MVP inside this budget:

```text
Primary frontend routes: 5 total
Workspace pages: 4
Dashboard count: 1
MVP uploaded dataset: 1 CSV
MVP chart types: 5
Main backend API groups: about 8-9
No auth
No billing
No teams
No advanced lineage graph engine
No multi-dataset analysis in MVP
No local analytics engine
No worker queue unless truly required
```

Add complexity only when a real requirement appears.

## 3. Source-of-truth docs

Tracked source docs live in:

```text
docs/scopian/sources/
```

These docs define approved scope.

Local-only files must stay untracked:

```text
docs/prompts/
docs/progress/
docs/audit/
_reference/
```

## 4. Scopian usage

Initial source docs are not added via buffer commands.

Use Scopian buffer only during implementation/run for:

```text
scope revision
new decision
conflict
implementation-time clarification
approved deviation from source docs
```

Examples:

```text
Codex discovers Snowflake constraint requiring API adjustment.
Claude Code needs a frontend field not in API contract.
A proposed UI route conflicts with the four-page workspace rule.
Provider behavior needs clarification.
```

Do not use buffer for:

```text
bulk adding PRODUCT_SCOPE.md
bulk adding API_CONTRACT.md
bulk adding all initial docs
```

## 5. CrossHelix usage

CrossHelix should map active repo only:

```text
backend/
frontend/
docs/scopian/sources/
```

Exclude:

```text
_reference/
docs/prompts/
docs/progress/
docs/audit/
node_modules/
.venv/
.next/
__pycache__/
```

Use CrossHelix:

```text
before starting a phase
after implementation
to check repo complexity
to support handoff between Codex and Claude Code
```

## 6. Codex role boundaries

Codex owns:

```text
repo setup
backend
database schema
Alembic migrations
API contract
S3 integration
Snowflake integration
dbt integration
warehouse execution
provider router
OpenAI/Gemini wiring
analysis workflow
ChartSpec validation
backend tests
integration
deployment wiring
```

Codex should not redesign frontend UI.

Codex may add minimal frontend wiring only if needed for integration, but visual UI belongs to Claude Code.

## 7. Claude Code role boundaries

Claude Code owns frontend UI only:

```text
landing page
workspace shell
shared left sidebar
Upload Dataset page
Data Flow page
Dashboard page
History page
AI Analytics Engineer panel UI
Recharts chart renderer
dashboard cards
evidence drawers
theme implementation
responsive layout
loading states
empty states
error states
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

If API is missing data, Claude should report the missing contract instead of inventing fake frontend data.

## 8. Commit rules

Use CentralDocs-style conventional commits.

Examples:

```text
chore: initialize meshflow v2 repo skeleton
docs: add scopian source scope for warehouse-first rebuild
feat: add upload readiness validation
fix: preserve dashboard cards after dataset deletion
test: cover invalid csv upload validation
refactor: simplify dashboard card state model
```

Rules:

```text
small commits
one logical change per commit
clear commit message
no prompts/progress/audit/reference repo committed
```

## 9. Failure rules

Never show fake success.

Allowed:

```text
honest failure
clear setup-required message
provider fallback
validation failure
warehouse unavailable error
dbt failure error
```

Not allowed:

```text
mock chart success
mock insight success
deterministic fake analysis
local DuckDB fallback
fake dbt run
fake Snowflake result
fake provider success
```

## 10. Frontend state rules

Frontend should not rely on hidden dataset state for AI prompts.

AI requests must explicitly attach dataset:

```json
{
  "attached_dataset_id": "dataset_123",
  "question": "How is revenue performing?"
}
```

Do not silently mix dataset outputs.

Each dashboard card must carry dataset/source snapshot data.

## 11. API rules

Keep API groups small.

Core groups:

```text
/demo-sessions
/workspace
/datasets
/data-flow
/analysis-runs
/dashboard
/history
/limits
/health
```

The frontend shell should primarily use:

```text
GET /api/v1/workspace
```

Do not create many endpoint groups for tiny features unless the product clearly needs it.

## 12. Testing expectations

Critical flows must have tests/checks:

```text
session create/continue/expiry
workspace endpoint shape
file validation
readiness failure
schema mapping save
transform success/failure
analysis requires attached dataset
analysis rejects deleted/not-ready dataset
ChartSpec validation
dataset deletion preserves card/history snapshots
reset does not reset production usage
```

Frontend should cover or manually verify:

```text
route guards
Browse → Upload states
no dataset empty states
Data Flow rail statuses
Transform button behavior
Dashboard disabled state with no ready dataset
Analysis Detail drawer
Dataset deleted badges
```

## 13. Documentation update rule

If implementation changes approved scope, update source docs or add Scopian buffer decision.

Do not let code drift away from docs.

## 14. Fast-but-correct build style

Move fast by:

```text
using narrow prompts
small phases
small commits
clear role boundaries
minimal architecture
```

Maintain correctness by:

```text
validating provider outputs
validating ChartSpecs
using honest failures
checking scopes with Scopian
checking repo complexity with CrossHelix
running tests/checks at each phase
```
