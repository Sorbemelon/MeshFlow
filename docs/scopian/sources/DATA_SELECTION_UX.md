# MeshFlow v2 Data Selection UX

Status: Final approved Phase 0 source document.

This document defines dataset selection, deletion, attachment, dashboard card preservation, and page-specific data behavior.

## 1. Core model

A workspace session can have multiple datasets.

Different pages use datasets differently:

```text
Upload Dataset creates datasets.
Data Flow selects one dataset for preparation/evidence.
Dashboard AI panel explicitly attaches one dataset per prompt.
Dashboard canvas can contain cards from multiple datasets.
History lists outputs across datasets.
```

This replaces the earlier idea that one active dataset controls all pages.

## 2. Dataset lifecycle

Common statuses:

```text
created
raw_loaded
schema_review
transforming
ready
failed
deleted
```

Meaning:

```text
created: dataset record exists
raw_loaded: file/demo is loaded to Warehouse Raw
schema_review: profile and semantic suggestions are ready for review
transforming: dbt transformation is running
ready: Data Marts are ready for analysis
failed: latest preparation step failed
deleted: removed from active management but historical snapshots remain
```

## 3. Upload Dataset page behavior

Upload Dataset page creates datasets.

Raw Retail Demo:

```text
can be added once per session
button disabled after added
```

Uploaded CSV:

```text
MVP supports one uploaded CSV dataset per session
button is Browse first
button changes to Upload after file selection
Upload stays disabled until file validation + S3 readiness + Snowflake readiness pass
```

After successful upload/demo add:

```text
navigate to /demo/data-flow
show Schema Preview for the new dataset
```

## 4. Data Flow dataset selector

The dataset selector belongs in the Data Flow left rail.

Purpose:

```text
make it obvious which dataset the preparation status belongs to
```

Selector states:

```text
No dataset available
Raw Retail Transactions Demo
uploaded datasets
deleted datasets only where historical context requires showing them
```

If no dataset exists:

```text
show Upload Dataset button
keep Data Flow page visible
show Schema Preview empty state
keep later tabs disabled/inactive
```

## 5. Dataset dropdown delete/bin action

Each dataset item in the Data Flow selector should include a bin icon.

Deleting a dataset means archiving/removing it from active management, not erasing generated outputs.

Correct deletion behavior:

```text
dataset status becomes deleted
dataset no longer appears as a normal active option
Data Flow cannot transform it further
Dashboard cards remain visible
History records remain visible
chart data snapshots remain visible
dataset badge changes to Dataset deleted
rerun/refine/follow-up from that dataset is disabled
```

Do not delete:

```text
already generated dashboard cards
analysis runs
analysis insights
chart snapshots
history evidence snapshots
```

## 6. Snapshot requirement

To preserve outputs after dataset deletion:

```text
analysis runs store dataset/source model snapshots
analysis charts store chart data snapshots
dashboard cards store card snapshots
history displays snapshots, not live dataset-only fields
```

This is required for maintainability and predictable UX.

## 7. Dashboard dataset behavior

Dashboard has one canvas per session.

The canvas can contain cards from multiple datasets.

Every card/result group must show:

```text
dataset badge
source model badge
```

If source dataset was deleted:

```text
show Dataset deleted badge
keep chart visible from snapshot
disable rerun/refine actions
```

## 8. AI Analytics Engineer dataset attachment

AI prompt must explicitly attach a dataset.

UI:

```text
Attach dataset:
[ Raw Retail Transactions Demo ▼ ]

Question:
[ How is revenue performing? ]
```

Request:

```json
{
  "attached_dataset_id": "dataset_123",
  "question": "How is revenue performing?"
}
```

MVP supports one attached dataset per analysis.

Future-ready shape:

```json
{
  "attached_dataset_ids": ["dataset_123"],
  "question": "How is revenue performing?"
}
```

Backend must reject:

```text
missing dataset
deleted dataset
dataset not ready for analysis
dataset from another session
```

This avoids hidden selected-dataset bugs.

## 9. Suggested questions

Suggested questions are generated per dataset during preparation.

Example:

```text
Raw Retail Transactions Demo:
- How is revenue performing?
- Show revenue by product category.
- What products are driving sales?
- Compare customer segments.
- Show monthly sales trend.
```

Dashboard AI panel shows suggestions for the currently attached dataset.

If suggestion generation failed:

```text
No AI-generated suggestions are available for this dataset.
You can still type a question manually after the dataset is ready.
```

No fake suggestions.

## 10. History dataset behavior

History shows analysis outputs across datasets.

Each item must show:

```text
dataset badge
status
question
chart count
source model
provider mode
created time
```

Filters may include:

```text
All datasets
Specific dataset
Status
```

Deleted dataset output remains readable with a Dataset deleted badge.

## 11. Quota and deletion

Deleting a dataset or card does not reduce successful usage counts.

Examples:

```text
User successfully uploads one dataset.
User deletes it.
Uploaded dataset quota remains used.
```

```text
User creates 8 dashboard cards.
User deletes 3.
Visible cards = 5.
Used dashboard card quota = 8.
```

## 12. Page empty states

### Data Flow with no dataset

```text
No dataset available yet.
Upload a dataset or use the Raw Retail Demo to start.
[Upload Dataset]
```

### Dashboard with no ready dataset

```text
Prepare a dataset before asking the AI Analytics Engineer.
[Upload Dataset]
```

### History with no analysis

```text
Analysis outputs will appear here after you ask the AI Analytics Engineer.
```

No fake sample output in empty states.
