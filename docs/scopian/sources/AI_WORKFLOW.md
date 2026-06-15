# MeshFlow v2 AI Workflow

Status: Final approved Phase 0 source document.

This document defines the AI workflow, provider routing, call counts, temperature strategy, validation rules, and failure behavior.

## 1. Core AI principle

AI proposes. MeshFlow validates and decides.

AI must not directly create final trusted product state without backend validation.

No AI task may produce fake successful output when providers fail.

## 2. Approved AI task routing

Use task-based routing.

### Semantic column suggestions and suggested questions

```text
Gemini
→ OpenAI fallback
→ honest failure
```

Temperature:

```text
0.1
```

Tasks:

```text
suggest column names
suggest semantic roles
provide confidence and reason
mark needs_review when ambiguous
generate dataset-specific suggested questions
```

### Analysis plan generation

```text
OpenAI
→ Gemini fallback
→ honest failure
```

Temperature:

```text
0.1
```

Task:

```text
turn attached dataset + user question into a structured analysis plan
```

### Insight generation

```text
Gemini
→ OpenAI fallback
→ honest failure
```

Temperature:

```text
0.2
```

Task:

```text
generate insight from actual Snowflake result preview
```

Insight generation must happen after the Snowflake query succeeds.

## 3. Gemini model lanes

Use CentralDocs-style Gemini configuration:

```text
GEMINI_API_KEY_1
GEMINI_API_KEY_2
GEMINI_API_KEY_3

GEMINI_MODEL_1
GEMINI_MODEL_2
GEMINI_MODEL_3
```

Gemini-owned tasks use:

```text
Gemini lane 1
→ Gemini lane 2
→ Gemini lane 3
→ OpenAI fallback
→ honest failure
```

For analysis plan generation:

```text
OpenAI
→ Gemini lane 1
→ Gemini lane 2
→ Gemini lane 3
→ honest failure
```

Provider keys must never be exposed to frontend.

## 4. Normal AI call counts

### Dataset preparation

Normal calls:

```text
1 AI call
```

Purpose:

```text
semantic column suggestions + dataset-specific suggested questions
```

Provider order:

```text
Gemini → OpenAI fallback
```

### One new analysis question

Normal calls:

```text
2 AI calls
```

| Call | Provider order | Purpose |
|---|---|---|
| 1 | OpenAI → Gemini | Structured analysis plan |
| 2 | Gemini → OpenAI | Insight from Snowflake result |

Snowflake execution is not an AI call.

ChartSpec generation should be backend-controlled and validated.

## 5. Preparation AI input

Send compact profile information, not full raw datasets.

Input should include:

```text
dataset name
source type
raw table name
column profiles
sample values per column
null rate
unique count
detected type
parse success scores
known warnings
```

Example semantic output:

```json
{
  "columns": [
    {
      "raw_column": "cust_seg",
      "suggested_name": "customer_segment",
      "semantic_role": "dimension",
      "confidence": 0.92,
      "needs_review": false,
      "reason": "Values look like common customer segment labels."
    },
    {
      "raw_column": "amt",
      "suggested_name": "amount",
      "semantic_role": "metric_candidate",
      "confidence": 0.58,
      "needs_review": true,
      "reason": "Numeric values detected, but business meaning is unclear."
    }
  ],
  "suggested_questions": [
    "How is revenue performing?",
    "Show revenue by product category."
  ]
}
```

Rules:

```text
Low-confidence suggestions require review.
Suggestions are stored after success.
Do not regenerate on every page load.
Regenerate only if profile/schema changes or user explicitly refreshes suggestions.
```

## 6. Analysis plan input

Send compact analysis context:

```text
attached dataset id and name
dataset source type
data marts available
source model schemas
metrics and dimensions
grain definitions
semantic mapping summary
suggested questions
recent analysis summary
hard limits
known warnings
user question
```

Do not send full raw datasets.

## 7. Analysis plan output

The AI must return structured JSON.

Example:

```json
{
  "question": "How is revenue performing?",
  "intent": "performance_overview",
  "source_model": "mart_sales_performance",
  "grain": "one row per month per product category",
  "metrics": [
    {
      "name": "total_revenue",
      "expression": "SUM(revenue)"
    }
  ],
  "dimensions": ["order_month", "product_category"],
  "charts": [
    {
      "type": "line",
      "title": "Monthly Revenue Trend",
      "x": "order_month",
      "y": "total_revenue"
    }
  ],
  "warnings": []
}
```

Default chart count:

```text
1 chart
```

Maximum chart count:

```text
3 charts
```

Use more than one chart only when one chart cannot fully answer the prompt.

## 8. Backend validation rules

Before executing anything, backend validates:

```text
attached dataset exists
attached dataset belongs to session
attached dataset is not deleted
attached dataset is ready for analysis
source model exists
columns exist
metrics are allowed
dimensions are allowed
chart count <= 3
chart type is supported
grain is known or marked uncertain
SQL is SELECT-only if SQL exists
no unknown table references
no unsafe commands
provider output matches schema
no secrets in output
```

If validation fails, try fallback provider for the same task. If fallback fails, return honest failure.

## 9. SQL generation

Backend should generate safe SQL from validated plan where possible.

The AI should not be trusted to supply final executable SQL without validation.

Snowflake SELECT execution happens only after plan validation.

## 10. ChartSpec generation

Backend ChartSpec service generates or validates final ChartSpec.

AI can suggest chart intent, but frontend receives validated ChartSpec.

ChartSpec must not include Recharts component code.

## 11. Insight generation input

Insight call happens after Snowflake result exists.

Input includes:

```text
question
source model
metric definitions
dimensions
grain
chart titles
small result preview
known limitations
warnings
```

## 12. Insight output

Example:

```json
{
  "summary": "Revenue increased steadily across the selected period.",
  "key_findings": [
    "March had the highest revenue in the previewed period.",
    "The monthly trend shows consistent growth."
  ],
  "tags": ["trend", "revenue"],
  "confidence": "medium"
}
```

No insight may be guessed before result data exists.

## 13. Failure behavior

If all providers fail for a task:

```text
mark task failed
store provider run evidence
return clear error
show no fake success
```

Example:

```text
Analysis could not be generated because OpenAI failed and all Gemini fallback lanes returned invalid plan output. No chart was generated.
```

## 14. Provider evidence

Provider runs should store:

```text
task type
provider
model
lane
temperature
status
error code/message
latency
created time
```

Frontend compact badges:

```text
Gemini
OpenAI fallback
Failed
```

Full provider chain belongs in Analysis Detail or History detail.

## 15. AI Analytics Engineer UI requirement

The question input must explicitly attach a dataset.

Frontend request:

```json
{
  "attached_dataset_id": "dataset_123",
  "question": "How is revenue performing?"
}
```

Do not rely on hidden selected dataset state.

This prevents dataset mismatch bugs.
