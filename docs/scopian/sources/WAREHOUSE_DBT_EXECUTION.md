# MeshFlow v2 Warehouse and dbt Execution

Status: Final approved Phase 0 source document.

This document defines the warehouse-only execution model for MeshFlow v2.

## 1. Core rule

MeshFlow v2 uses real warehouse-backed execution.

Required execution path:

```text
Raw Input
→ S3
→ Snowflake Warehouse Raw
→ dbt Staging
→ dbt Intermediate
→ dbt Dimensional Model
→ dbt Data Marts
→ Snowflake analysis SELECT
→ ChartSpec
→ Dashboard
```

Removed completely:

```text
DuckDB
local analytics execution
mock dbt success
mock pipeline success
fake Snowflake result
deterministic fake analysis fallback
```

## 2. Honest failure requirement

If any required infrastructure is unavailable, return a clear failure.

Examples:

```text
S3 is not configured, so MeshFlow cannot store the raw input file.
Snowflake is not configured, so MeshFlow cannot load the file into Warehouse Raw.
dbt failed while building mart_sales_performance. No dashboard chart was generated.
```

No fake success path is allowed.

## 3. Raw Input

Raw Input is the original file selected by the user or the curated demo.

Sources:

```text
Raw Retail Transactions Demo
Uploaded CSV
```

Raw Retail Demo is a raw denormalized retail transaction file, not a star schema.

## 4. File validation

Before upload can proceed, file validation must pass.

Frontend quick validation:

```text
file exists
file size <= 5 MB
extension is .csv
not empty
basic CSV parse succeeds
header row exists
at least 2 columns
at least 1 data row
```

Backend authoritative validation:

```text
file type is allowed
file size is allowed
CSV parser can read it
headers are non-empty
headers are unique after normalization
rows are sufficiently parseable
row widths are not severely inconsistent
column count is within MVP limit
encoding is supported
Snowflake-safe table/column names can be generated
```

Upload button is disabled until validation plus S3/Snowflake readiness pass.

## 5. S3 readiness and upload

After file browse/selection:

```text
validate file
check S3 readiness
check Snowflake readiness
enable Upload only if all pass
```

When Upload is clicked:

```text
upload to S3 under a session-scoped key
record s3_uri and object metadata
continue to Snowflake load
```

Example key pattern:

```text
meshflow-demo/{session_id}/datasets/{dataset_id}/raw/{file_name}
```

## 6. Snowflake Warehouse Raw

After S3 upload, MeshFlow loads data to Snowflake Warehouse Raw.

Expected behavior:

```text
create/use session-scoped schema
create raw table with safe column names
load from S3 stage or configured storage integration
record raw table metadata
profile the raw table from Snowflake
```

No local fallback is allowed.

Suggested namespace pattern:

```text
<database>.<schema_prefix>_<session_short_id>.RAW_<dataset_slug>
```

Keep names deterministic and safe.

## 7. Profiling

Profiling is deterministic and warehouse-backed.

Profile each column:

```text
raw column name
detected type
sample values
null rate
unique count
numeric parse success
date parse success
boolean parse success
identifier pattern/cardinality
value distribution where safe
```

Profiling does not require AI.

## 8. Semantic suggestions

After profiling, call AI:

```text
Gemini → OpenAI fallback → honest failure
```

Temperature:

```text
0.1
```

Output:

```text
suggested column names
semantic roles
confidence
needs_review
reason
dataset-specific suggested questions
```

The user reviews mappings in Schema Preview before Transform.

## 9. dbt transformation layers

The Transform action runs dbt through these approved layers:

```text
Staging
Intermediate
Dimensional Model
Data Marts
```

### Staging

Purpose:

```text
clean raw table
rename columns
cast types
trim strings
normalize nulls
standardize values
```

Example:

```text
raw_retail_transactions → stg_retail_transactions
```

### Intermediate

Purpose:

```text
prepare reusable business logic
join/enrich staged data when needed
derive dates/months
derive revenue/cost/margin fields
```

Example:

```text
int_retail_sales_enriched
```

### Dimensional Model

Purpose:

```text
create fact and dimension models
make analytical grain explicit
prevent double counting
```

Example models:

```text
fact_sales
dim_customer
dim_product
dim_store
dim_date
```

UI note:

```text
Pattern: star-schema-style dimensional model
```

Do not call the main layer “Star Schema.” Use “Dimensional Model.”

### Data Marts

Purpose:

```text
business-ready analytical models for AI analysis
```

Example marts:

```text
mart_sales_performance
mart_product_performance
mart_customer_segments
mart_store_performance
```

## 10. Transform button behavior

Show Transform when:

```text
schema review is required
previous transformation failed
```

Disable Transform when:

```text
required mappings are invalid
transformation is running
```

Remove Transform when:

```text
transformation succeeds and dataset is ready for analysis
```

If transformation fails:

```text
show failed step
show clear reason
keep Transform button for retry
```

## 11. dbt execution evidence

Data Flow tabs should show compact evidence:

```text
model name
layer
status
short explanation
collapsed SQL/schema.yml/details
```

No processing buttons inside automated tabs.

Automated evidence tabs:

```text
Warehouse Raw
Transformations
Dimensional Model & Data Marts
```

## 12. Data Marts ready state

A dataset is ready for analysis only when:

```text
Warehouse Raw loaded
schema mapping approved
Staging built
Intermediate built
Dimensional Model built
Data Marts built
marts registered as available source models
```

Then Dashboard can use the dataset.

## 13. Analysis execution

Analysis plans query Data Marts by default.

Flow:

```text
validated analysis plan
→ backend generates safe Snowflake SELECT
→ Snowflake executes query
→ result preview and output schema stored
→ ChartSpec generated
→ insight generated from result preview
```

Most analysis questions should use existing marts, not create new dbt models.

Rules:

```text
one-off chart query → Snowflake SELECT only
reusable business logic → dbt model only if explicitly added to scope
complex logic in MVP → avoid or return clear unsupported message
```

## 14. Cleanup

Expired session cleanup should remove:

```text
S3 objects under session prefix
Snowflake session schemas/tables or dataset tables
generated dbt artifacts/metadata
metadata DB workspace data
temporary files
```

Production quota/abuse logs may remain for the quota window.

## 15. Configuration and readiness

Readiness should check:

```text
S3 credentials/bucket access
Snowflake connection and warehouse availability
dbt project/profile readiness
AI provider readiness where needed
```

Upload button specifically requires:

```text
valid file
S3 ready
Snowflake ready
```

Transform requires:

```text
valid schema mappings
Snowflake ready
dbt ready
```

Analysis requires:

```text
dataset ready
Snowflake ready
AI provider path available for planning
```
