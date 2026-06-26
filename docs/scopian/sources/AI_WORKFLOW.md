# MeshFlow v2 AI Workflow

Status: Final approved Phase 0 source document, aligned with approved Phase 10 implementation decisions.

This document defines the AI workflow, provider routing, call counts, temperature strategy, validation rules, and failure behavior.

## 1. Core AI principle

AI proposes. MeshFlow validates and decides.

AI must not directly create final trusted product state without backend validation.

No AI task may produce fake successful output when providers fail.

No deterministic fallback is allowed for semantic preparation, question suggestions, analysis plans, modeling proposals, charts, or insights.

## 2. Active provider configuration

The active app surface uses two Gemini API key slots and two Gemini model slots:

```text
GEMINI_API_KEY_1
GEMINI_API_KEY_2
GEMINI_MODEL_1
GEMINI_MODEL_2
OPENAI_API_KEY
OPENAI_MODEL
```

Removed from the active app surface:

```text
GEMINI_API_KEY_3
GEMINI_MODEL_3
```

For each Gemini model in a provider route, MeshFlow should try key 1 and key 2 before moving to the next provider/model step.

Provider keys must never be exposed to the frontend or stored in provider evidence.

## 3. Approved AI task routing

Use task-based routing.

For semantic preparation, post-mart question suggestions, analysis plans, and insights:

```text
GEMINI_MODEL_1 with key 1/2
-> OpenAI
-> GEMINI_MODEL_2 with key 1/2
-> honest failure
```

For uploaded CSV modeling proposals:

```text
GEMINI_MODEL_1 with key 1/2
-> GEMINI_MODEL_2 with key 1/2
-> OpenAI
-> honest failure
```

Fallback means a provider/model/key failed, was unavailable, hit a rate limit, or returned invalid structured output. Fallback does not mean accepting weaker or unvalidated product output.

## 4. Semantic preparation

Semantic preparation is column mapping only.

Temperature:

```text
0.1
```

Tasks:

```text
suggest model-friendly column names
suggest semantic roles
provide confidence and reason
mark needs_review when ambiguous
```

Semantic preparation must not generate dataset-specific suggested questions.

Semantic preparation output is exposed under:

```text
semantic_preparation
  status
  semantic_columns
  provider_runs
  errors/warnings if any
```

## 5. Post-mart question suggestions

Dataset-specific suggested questions are generated only after dbt successfully builds Data Marts.

Question suggestions are generated from the backend-known mart catalog, including available marts, metrics, dimensions, and grains. They are not generated from raw schema prep.

Temperature:

```text
0.1
```

Question suggestions are exposed separately from semantic preparation:

```text
question_suggestions
  status
  suggestions
  generated_from: data_marts
  provider_runs
  errors/warnings if any
```

Frontend consumers should read `question_suggestions`, not `semantic_preparation.suggested_questions`.

## 6. Uploaded CSV modeling proposals

Uploaded CSV transformation may use an AI-assisted modeling proposal when the backend needs help choosing a conservative modeling approach.

AI proposal input may include:

```text
dataset profile
approved semantic mappings
column roles
candidate identifiers
candidate dates
candidate measures
sample value summaries
known warnings
```

AI proposal output may describe:

```text
suggested fact grain
candidate dimensions
candidate measures
candidate marts
unsupported/needs-review reasons
```

The backend remains the owner of dbt SQL generation and validation.

AI must not provide trusted executable dbt or Snowflake SQL without backend validation.

If the proposal is invalid, insufficient, or unsupported, MeshFlow returns an honest needs-review/unsupported state instead of fake marts.

## 7. Normal AI call counts

### Dataset preparation before transform

Normal calls:

```text
1 AI call
```

Purpose:

```text
semantic column mapping suggestions only
```

Provider order:

```text
GEMINI_MODEL_1 key 1/2 -> OpenAI -> GEMINI_MODEL_2 key 1/2
```

### Dataset question suggestions after Data Marts

Normal calls:

```text
1 AI call
```

Purpose:

```text
suggest useful analysis questions from the mart catalog
```

Provider order:

```text
GEMINI_MODEL_1 key 1/2 -> OpenAI -> GEMINI_MODEL_2 key 1/2
```

### One new analysis question

Normal calls:

```text
2 AI calls
```

| Call | Provider order | Purpose |
|---|---|---|
| 1 | GEMINI_MODEL_1 key 1/2 -> OpenAI -> GEMINI_MODEL_2 key 1/2 | Structured analysis plan |
| 2 | GEMINI_MODEL_1 key 1/2 -> OpenAI -> GEMINI_MODEL_2 key 1/2 | Insight from Snowflake result |

Snowflake execution is not an AI call.

ChartSpec generation is backend-controlled and validated.

## 8. Preparation AI input

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
  ]
}
```

Rules:

```text
Low-confidence suggestions require review.
Suggestions are stored after success.
Do not regenerate on every page load.
Retry is allowed after an honest failure.
```

## 9. Analysis plan input

Send compact analysis context:

```text
attached dataset id and name
dataset source type
data marts available
source model schemas
metrics and dimensions
grain definitions
semantic mapping summary
post-mart suggested questions if available
recent analysis summary
hard limits
known warnings
user question
```

Do not send full raw datasets.

## 10. Analysis plan output

The AI must return structured JSON.

Example:

```json
{
  "decision_type": "create_new",
  "question": "How is revenue performing?",
  "intent": "performance_overview",
  "source_model": "mart_sales_performance",
  "grain": "one row per month per product category",
  "metrics": [
    {
      "name": "total_revenue",
      "aggregation": "sum"
    }
  ],
  "dimensions": ["order_month"],
  "filters": [],
  "sort": [
    {
      "field": "order_month",
      "direction": "asc"
    }
  ],
  "limit": 100,
  "assumptions": [],
  "warnings": []
}
```

The provider must not provide executable SQL as the trusted output. Backend generates the SQL from the validated plan.

## 11. Backend validation rules

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
filters reference allowed fields
limit is bounded
chart count <= 3 if chart hints exist
chart type is supported if chart hints exist
grain is known or marked uncertain
no unknown table references
no unsafe commands
provider output matches schema
no secrets in output
```

If validation fails, try fallback provider for the same task. If fallback fails, return honest failure.

## 12. SQL generation

Backend generates safe SELECT-only SQL from the validated plan.

Snowflake SELECT execution happens only after plan validation.

Provider-generated SQL is not trusted as executable product logic.

## 13. ChartSpec generation

Backend ChartSpec service generates final ChartSpec from stored result schema and preview rows.

AI can suggest chart intent only if validation supports it.

Frontend receives validated ChartSpec and data snapshots.

ChartSpec must not include Recharts component code.

Default chart count:

```text
1 chart
```

Maximum chart count:

```text
3 charts
```

Use more than one chart only when the result shape justifies it.

## 14. Insight generation input

Insight generation happens after Snowflake result data and ChartSpec snapshots exist.

Input includes:

```text
question
source model
metric definitions
dimensions
grain
chart titles
ChartSpecs
small stored result preview
known limitations
warnings
```

## 15. Insight output

Example:

```json
{
  "question_insight": {
    "summary": "Revenue increased steadily across the selected period.",
    "key_findings": [
      "March had the highest revenue in the previewed period.",
      "The monthly trend shows consistent growth."
    ],
    "tags": ["trend", "revenue"],
    "confidence": "medium"
  },
  "chart_insights": []
}
```

No insight may be guessed before result data exists.

If insight generation fails after analysis and charts succeed, the analysis remains completed and insight status is failed/unavailable.

## 16. Failure behavior

If all providers fail for a task:

```text
mark task failed
store provider run evidence
return clear error
show no fake success
```

Example:

```text
Analysis could not be generated because all configured provider attempts returned errors or invalid plan output. No chart was generated.
```

## 17. Provider evidence

Provider runs should store:

```text
task type
provider
model
temperature where tracked
status
error code/message
fallback source where tracked
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

## 18. AI Analytics Engineer UI requirement

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
