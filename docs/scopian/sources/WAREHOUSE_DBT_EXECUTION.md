# MeshFlow v2 Warehouse and dbt Execution

Status: Final approved Phase 0 source document, aligned with approved Phase 10 implementation decisions.

This document defines the warehouse-only execution model for MeshFlow v2.

## 1. Core rule

MeshFlow v2 uses real warehouse-backed execution.

Required execution path:

```text
Raw Input
-> S3
-> Snowflake Warehouse Raw
-> Schema Profile
-> Semantic Column Mapping
-> dbt Staging
-> dbt Intermediate
-> dbt Dimensional Model
-> dbt Data Marts
-> Question Suggestions
-> Snowflake analysis SELECT
-> ChartSpec
-> Dashboard
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
file size <= configured safety limit
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
total upload storage quota is available
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
check total upload storage quota
check S3 readiness
check Snowflake readiness
enable Upload only if all pass
```

When Upload is clicked:

```text
upload to S3 under a session-scoped key
record s3_uri and object metadata
increment stored upload size only after successful stored upload/load
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
create/use session-scoped schema or safe session-scoped table names
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

## 8. Semantic column mapping

After profiling, MeshFlow may call AI for column-mapping suggestions:

```text
GEMINI_MODEL_1 with key 1/2
-> OpenAI
-> GEMINI_MODEL_2 with key 1/2
-> honest failure
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
```

The user reviews mappings in Schema Preview before Transform.

Semantic preparation is column mapping only. It must not generate dataset-specific suggested questions.

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
raw_retail_transactions -> stg_retail_transactions
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

Do not call the main layer "Star Schema." Use "Dimensional Model."

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

## 10. Uploaded CSV modeling

Generic uploaded CSV transformation remains conservative.

When deterministic mapping is insufficient, MeshFlow may request an AI-assisted modeling proposal:

```text
GEMINI_MODEL_1 with key 1/2
-> GEMINI_MODEL_2 with key 1/2
-> OpenAI
-> honest failure
```

The backend owns dbt SQL generation and validation.

The AI proposal is not trusted executable SQL.

If a generic uploaded CSV lacks enough semantic mapping for meaningful Data Marts, return a clear needs-review/unsupported state instead of fake marts.

## 11. Transform button behavior

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

## 12. dbt execution evidence

Data Flow tabs should show compact evidence:

```text
model name
layer
status
short explanation
collapsed SQL/schema.yml/details
selected columns and approved mappings
source -> staging -> intermediate -> dimensional model -> marts flow
```

No processing buttons inside automated tabs.

Automated evidence tabs:

```text
Warehouse Raw
Transformations
Dimensional Model & Data Marts
```

## 13. Data Marts ready state

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

## 14. Question suggestions

Dataset-specific suggested questions are generated after Data Marts exist.

Input:

```text
backend-known mart catalog
available metrics
available dimensions
grain definitions
known limitations
```

Provider route:

```text
GEMINI_MODEL_1 with key 1/2
-> OpenAI
-> GEMINI_MODEL_2 with key 1/2
-> honest failure
```

Question suggestions are exposed as `question_suggestions`, not as part of semantic preparation.

## 15. Analysis execution

Analysis plans query Data Marts by default.

Flow:

```text
validated analysis plan
-> backend generates safe Snowflake SELECT
-> Snowflake executes query
-> result preview and output schema stored
-> ChartSpec generated
-> insight generated from result preview
```

Most analysis questions should use existing marts, not create new dbt models.

Rules:

```text
one-off chart query -> Snowflake SELECT only
reusable business logic -> dbt model only if explicitly added to scope
complex logic in MVP -> avoid or return clear unsupported message
```

## 16. Cleanup

Expired session cleanup should remove:

```text
S3 objects under session prefix
Snowflake session schemas/tables or dataset tables
generated dbt artifacts/metadata
metadata DB workspace data
temporary files
```

Production quota/abuse logs may remain for the quota window.

## 17. Configuration and readiness

Readiness should check:

```text
S3 credentials/bucket access
Snowflake connection and warehouse availability
Snowflake stage access
dbt project/profile readiness
AI provider readiness where needed
```

Upload button specifically requires:

```text
valid file
storage quota available
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

dbt runtime must use a Python version compatible with the configured dbt line. The live smoke path validated dbt 1.11 with a Python 3.11 runtime; Python versions that break dbt dependencies should return setup-required/failed, not fake dbt success.
