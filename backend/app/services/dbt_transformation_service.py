from __future__ import annotations

import os
import json
import hashlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, settings
from app.core.errors import AppError
from app.models.dataset import (
    ColumnProfile,
    DataFlowEdge,
    DataFlowNode,
    Dataset,
    DatasetTransformationRun,
    DbtArtifact,
    SemanticColumn,
)
from app.schemas.dataset import (
    DataFlowEdgeSummary,
    DataFlowNodeSummary,
    DatasetDataFlowResponse,
    DatasetTransformResponse,
    DatasetTransformationRunSummary,
    DbtArtifactSummary,
    RawTablePreviewResponse,
)
from app.schemas.upload_preflight import ReadinessCheck
from app.services import readiness_service, snowflake_service
from app.services.dataset_service import RAW_RETAIL_DEMO_SOURCE_TYPE, dataset_summary
from app.services.demo_session_service import get_required_session
from app.services.modeling_proposal_service import (
    ValidatedModelDimension,
    ValidatedModelingProposal,
    create_modeling_proposal,
    proposal_analysis_catalog,
    proposal_to_json,
)
from app.services.question_suggestion_service import generate_dataset_question_suggestions
from app.services.question_suggestion_summary_service import (
    question_suggestions_summary_from_dataset,
)


SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
TRANSFORMATION_LAYERS = ["staging", "intermediate", "dimensional_model", "data_marts"]
DBT_LAYER_RUN_SPECS = [
    ("staging", "staging", "models/staging"),
    ("intermediate", "intermediate", "models/intermediate"),
    ("dimensional_model", "dimensional_model", "models/dimensional"),
    ("data_marts", "data_mart", "models/marts"),
]
PREP_NODE_SPECS = [
    ("raw_input", "Raw Input"),
    ("warehouse_raw", "Warehouse Raw"),
    ("staging", "Staging"),
    ("intermediate", "Intermediate"),
    ("dimensional_model", "Dimensional Model"),
    ("data_mart", "Data Marts"),
]
RAW_RETAIL_MODELS = {
    "staging": ["stg_retail_transactions"],
    "intermediate": ["int_retail_sales_enriched"],
    "dimensional_model": [
        "fact_sales",
        "dim_customer",
        "dim_product",
        "dim_store",
        "dim_date",
    ],
    "data_marts": [
        "mart_sales_performance",
        "mart_product_performance",
        "mart_customer_segments",
        "mart_store_performance",
    ],
}
KNOWN_DBT_MODEL_TABLES = {
    model_name
    for model_group in RAW_RETAIL_MODELS.values()
    for model_name in model_group
}
GENERATED_MODEL_PREFIXES = ("stg_", "int_", "fact_", "dim_", "mart_")


class DbtExecutionError(Exception):
    def __init__(
        self,
        *,
        error_code: str,
        failed_step: str,
        message: str,
        command_summary: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.failed_step = failed_step
        self.message = message
        self.command_summary = command_summary or {}


@dataclass(frozen=True)
class SemanticMapping:
    profile: ColumnProfile
    approved_name: str
    approved_role: str


@dataclass(frozen=True)
class GeneratedDbtProject:
    project_dir: Path
    profiles_dir: Path
    project_name: str
    profile_name: str
    models: dict[str, list[str]]
    artifacts: list[tuple[str, str, str, str, Path | None]]
    modeling_proposal: dict[str, object] | None = None
    analysis_catalog: dict[str, dict[str, object]] | None = None
    model_metadata: dict[str, object] | None = None


@dataclass(frozen=True)
class CleanupOperationResult:
    status: str
    warning: str | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


def _summary_from_run(run: DatasetTransformationRun) -> DatasetTransformationRunSummary:
    return DatasetTransformationRunSummary(
        id=run.id,
        status=run.status,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        failed_step=run.failed_step,
        error_code=run.error_code,
        error_message=run.error_message,
        dbt_project_path=run.dbt_project_path,
        dbt_target_name=run.dbt_target_name,
        dbt_run_summary=run.dbt_run_summary_json,
    )


def _artifact_summary(artifact: DbtArtifact) -> DbtArtifactSummary:
    return DbtArtifactSummary(
        id=artifact.id,
        artifact_type=artifact.artifact_type,
        layer=artifact.layer,
        name=artifact.name,
        content_redacted=artifact.content_redacted,
        file_path=artifact.file_path,
        created_at=artifact.created_at.isoformat(),
    )


def _node_summary(node: DataFlowNode) -> DataFlowNodeSummary:
    return DataFlowNodeSummary(
        id=node.id,
        node_type=node.node_type,
        name=node.name,
        label=node.label,
        status=node.status,
        metadata=node.metadata_json,
    )


def _edge_summary(edge: DataFlowEdge) -> DataFlowEdgeSummary:
    return DataFlowEdgeSummary(
        id=edge.id,
        from_node_id=edge.from_node_id,
        to_node_id=edge.to_node_id,
        edge_type=edge.edge_type,
        metadata=edge.metadata_json,
    )


def _readiness_error(check: ReadinessCheck) -> AppError:
    return AppError(
        error_code="SNOWFLAKE_NOT_READY",
        failed_step="snowflake_readiness",
        message=check.message,
        next_action=check.next_action,
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _load_dataset(
    db: Session,
    session_id: str | None,
    dataset_id: str,
) -> Dataset:
    session = get_required_session(db, session_id)
    dataset = db.scalar(
        select(Dataset)
        .where(
            Dataset.id == dataset_id,
            Dataset.demo_session_id == session.id,
        )
        .options(
            selectinload(Dataset.files),
            selectinload(Dataset.column_profiles),
            selectinload(Dataset.semantic_columns).selectinload(SemanticColumn.column_profile),
            selectinload(Dataset.question_suggestions),
            selectinload(Dataset.transformation_runs),
            selectinload(Dataset.dbt_artifacts),
            selectinload(Dataset.data_flow_nodes),
            selectinload(Dataset.data_flow_edges),
        )
    )
    if dataset is None:
        raise AppError(
            error_code="DATASET_NOT_FOUND",
            failed_step="dataset",
            message="The requested dataset was not found for this demo session.",
            next_action="Select an available dataset from the workspace.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if dataset.deleted_at is not None or dataset.status == "deleted":
        raise AppError(
            error_code="DATASET_DELETED",
            failed_step="dataset_validation",
            message=(
                "This dataset was deleted from the active workspace. Existing dashboard "
                "cards and history remain available, but transformation cannot run from it."
            ),
            next_action="Upload or prepare another dataset.",
            status_code=status.HTTP_410_GONE,
        )
    return dataset


def _ensure_transformable_dataset(dataset: Dataset) -> None:
    if dataset.deleted_at is not None or dataset.status == "deleted":
        raise AppError(
            error_code="DATASET_DELETED",
            failed_step="dataset_validation",
            message=(
                "This dataset was deleted from the active workspace. Existing dashboard "
                "cards and history remain available, but transformation cannot run from it."
            ),
            next_action="Upload or prepare another dataset.",
            status_code=status.HTTP_410_GONE,
        )
    if not dataset.raw_table_name:
        raise AppError(
            error_code="DATASET_NOT_READY_FOR_TRANSFORM",
            failed_step="warehouse_raw",
            message="This dataset has no Warehouse Raw table to transform.",
            next_action="Upload and load the dataset into Snowflake Warehouse Raw first.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not dataset.column_profiles:
        raise AppError(
            error_code="DATASET_NOT_READY_FOR_TRANSFORM",
            failed_step="schema_profile",
            message="This dataset has no schema profile to transform.",
            next_action="Upload and profile the dataset before running dbt.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


def _effective_mappings(dataset: Dataset) -> list[SemanticMapping]:
    mappings: list[SemanticMapping] = []
    for semantic in dataset.semantic_columns:
        if not semantic.include_in_model:
            continue
        approved_name = semantic.approved_name or semantic.suggested_name
        approved_role = semantic.approved_role or semantic.semantic_role
        if not SAFE_NAME_RE.fullmatch(approved_name):
            continue
        if approved_role == "unknown":
            continue
        mappings.append(
            SemanticMapping(
                profile=semantic.column_profile,
                approved_name=approved_name,
                approved_role=approved_role,
            )
        )
    return mappings


def _ensure_semantic_mappings(dataset: Dataset) -> list[SemanticMapping]:
    mappings = _effective_mappings(dataset)
    if not mappings:
        raise AppError(
            error_code="SEMANTIC_MAPPING_REQUIRED",
            failed_step="semantic_mapping",
            message="This dataset needs reviewed semantic mappings before dbt transformation.",
            next_action="Generate AI suggestions or save manual schema mappings, then retry Transform.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return mappings


def _ensure_uploaded_csv_support(dataset: Dataset, mappings: list[SemanticMapping]) -> None:
    if dataset.source_type == RAW_RETAIL_DEMO_SOURCE_TYPE:
        return

    has_measure = any(
        mapping.approved_role in {"measure_column", "metric_candidate"} for mapping in mappings
    )
    has_dimension = any(
        mapping.approved_role in {"dimension", "date_time", "identifier"} for mapping in mappings
    )
    if not has_measure or not has_dimension:
        raise AppError(
            error_code="TRANSFORMATION_NEEDS_REVIEW",
            failed_step="semantic_mapping",
            message=(
                "This uploaded CSV needs clearer semantic mappings before MeshFlow can build "
                "Data Marts."
            ),
            next_action=(
                "Review mappings so at least one measure and one dimension or date are included."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )


def _ensure_snowflake_ready(config: Settings) -> None:
    check = readiness_service.check_snowflake_readiness(config)
    if check.status != "ready":
        raise _readiness_error(check)


def _dbt_executable() -> str:
    script_name = "dbt.exe" if os.name == "nt" else "dbt"
    adjacent = Path(sys.executable).with_name(script_name)
    if adjacent.exists():
        return str(adjacent)

    discovered = shutil.which("dbt")
    if discovered:
        return discovered

    raise DbtExecutionError(
        error_code="DBT_DEPENDENCY_MISSING",
        failed_step="dbt_dependency",
        message="The dbt CLI is not installed in the active backend environment.",
    )


def _dbt_environment(config: Settings) -> dict[str, str]:
    env = os.environ.copy()
    for key, value in {
        "SNOWFLAKE_ACCOUNT": config.snowflake_account,
        "SNOWFLAKE_USER": config.snowflake_user,
        "SNOWFLAKE_PASSWORD": config.snowflake_password,
        "SNOWFLAKE_ROLE": config.snowflake_role,
        "SNOWFLAKE_WAREHOUSE": config.snowflake_warehouse,
        "SNOWFLAKE_DATABASE": config.snowflake_database,
        "SNOWFLAKE_SCHEMA": config.snowflake_schema,
    }.items():
        if value is not None:
            env[key] = value
    return env


def _redact(text: str, config: Settings) -> str:
    redacted = text
    secret_values = [
        config.snowflake_password,
        config.aws_secret_access_key,
        config.openai_api_key,
        config.gemini_api_key_1,
        config.gemini_api_key_2,
    ]
    for secret in secret_values:
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def _run_command(
    args: list[str],
    *,
    project_dir: Path,
    config: Settings,
    failed_step: str,
) -> dict[str, object]:
    completed = subprocess.run(
        args,
        cwd=project_dir,
        env=_dbt_environment(config),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    stdout = _redact(completed.stdout[-4000:], config)
    stderr = _redact(completed.stderr[-4000:], config)
    summary = {
        "command": " ".join(args[:2]),
        "returncode": completed.returncode,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
    }
    if completed.returncode != 0:
        raise DbtExecutionError(
            error_code="DBT_RUN_FAILED",
            failed_step=failed_step,
            message="dbt could not build the Data Marts for this dataset.",
            command_summary=summary,
        )
    return summary


def run_dbt_commands(
    *,
    project_dir: Path,
    profiles_dir: Path,
    target_name: str,
    config: Settings = settings,
    on_layer_status: Callable[[str, str], None] | None = None,
) -> dict[str, object]:
    dbt = _dbt_executable()
    project_dir = project_dir.resolve()
    profiles_dir = profiles_dir.resolve()
    common_args = [
        "--project-dir",
        str(project_dir),
        "--profiles-dir",
        str(profiles_dir),
        "--target",
        target_name,
    ]
    debug_summary = _run_command(
        [dbt, "debug", *common_args],
        project_dir=project_dir,
        config=config,
        failed_step="dbt_debug",
    )
    layer_summaries: dict[str, object] = {}
    for layer_key, node_type, model_path in DBT_LAYER_RUN_SPECS:
        if on_layer_status:
            on_layer_status(node_type, "running")
        try:
            layer_summaries[layer_key] = _run_command(
                [dbt, "run", *common_args, "--select", f"path:{model_path}"],
                project_dir=project_dir,
                config=config,
                failed_step=layer_key,
            )
        except DbtExecutionError:
            if on_layer_status:
                on_layer_status(node_type, "failed")
            raise
        if on_layer_status:
            on_layer_status(node_type, "completed")

    return {
        "debug": debug_summary,
        "run": {
            "returncode": 0,
            "stdout_tail": "dbt layer runs completed.",
            "stderr_tail": "",
            "layers": layer_summaries,
        },
        "layers": layer_summaries,
    }


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _profile_yml(profile_name: str, target_name: str, threads: int) -> str:
    return f"""
{profile_name}:
  target: {target_name}
  outputs:
    {target_name}:
      type: snowflake
      account: "{{{{ env_var('SNOWFLAKE_ACCOUNT') }}}}"
      user: "{{{{ env_var('SNOWFLAKE_USER') }}}}"
      password: "{{{{ env_var('SNOWFLAKE_PASSWORD') }}}}"
      role: "{{{{ env_var('SNOWFLAKE_ROLE') }}}}"
      warehouse: "{{{{ env_var('SNOWFLAKE_WAREHOUSE') }}}}"
      database: "{{{{ env_var('SNOWFLAKE_DATABASE') }}}}"
      schema: "{{{{ env_var('SNOWFLAKE_SCHEMA') }}}}"
      threads: {threads}
      client_session_keep_alive: false
"""


def _project_yml(project_name: str, profile_name: str) -> str:
    return f"""
name: {project_name}
version: "1.0.0"
config-version: 2
profile: {profile_name}

models:
  {project_name}:
    +materialized: table
"""


def _schema_yml(models: dict[str, list[str]]) -> str:
    model_lines = []
    for layer_models in models.values():
        for model_name in layer_models:
            model_lines.append(f"  - name: {model_name}")
    return "version: 2\n\nmodels:\n" + "\n".join(model_lines)


def _raw_relation(dataset: Dataset) -> str:
    return snowflake_service.quote_identifier(dataset.raw_table_name)


def _retail_sql(raw_relation: str) -> dict[str, str]:
    return {
        "models/staging/stg_retail_transactions.sql": f"""
select
  nullif(trim("ORDER_ID"), '') as order_id,
  nullif(trim("ORDER_LINE_ID"), '') as order_line_id,
  try_to_date("ORDER_DATE") as order_date,
  nullif(trim("CUSTOMER_ID"), '') as customer_id,
  nullif(trim("CUSTOMER_NAME"), '') as customer_name,
  nullif(trim("CUSTOMER_SEGMENT"), '') as customer_segment,
  nullif(trim("PRODUCT_ID"), '') as product_id,
  nullif(trim("PRODUCT_NAME"), '') as product_name,
  nullif(trim("PRODUCT_CATEGORY"), '') as product_category,
  nullif(trim("STORE_ID"), '') as store_id,
  nullif(trim("STORE_NAME"), '') as store_name,
  nullif(trim("STORE_REGION"), '') as store_region,
  try_to_number("QUANTITY") as quantity,
  try_to_decimal("UNIT_PRICE", 18, 2) as unit_price,
  try_to_decimal("DISCOUNT_AMOUNT", 18, 2) as discount_amount,
  try_to_decimal("REVENUE", 18, 2) as revenue,
  try_to_decimal("COST", 18, 2) as cost,
  nullif(trim("PAYMENT_METHOD"), '') as payment_method
from {raw_relation}
""",
        "models/intermediate/int_retail_sales_enriched.sql": """
select
  *,
  date_trunc('month', order_date)::date as order_month,
  coalesce(revenue, quantity * unit_price - coalesce(discount_amount, 0)) as net_revenue,
  coalesce(revenue, quantity * unit_price - coalesce(discount_amount, 0)) - coalesce(cost, 0) as gross_margin
from {{ ref('stg_retail_transactions') }}
""",
        "models/dimensional/dim_customer.sql": """
select distinct
  customer_id,
  customer_name,
  customer_segment
from {{ ref('int_retail_sales_enriched') }}
where customer_id is not null
""",
        "models/dimensional/dim_product.sql": """
select distinct
  product_id,
  product_name,
  product_category
from {{ ref('int_retail_sales_enriched') }}
where product_id is not null
""",
        "models/dimensional/dim_store.sql": """
select distinct
  store_id,
  store_name,
  store_region
from {{ ref('int_retail_sales_enriched') }}
where store_id is not null
""",
        "models/dimensional/dim_date.sql": """
select distinct
  order_date,
  order_month,
  extract(year from order_date) as order_year,
  extract(month from order_date) as order_month_number
from {{ ref('int_retail_sales_enriched') }}
where order_date is not null
""",
        "models/dimensional/fact_sales.sql": """
select
  order_line_id,
  order_id,
  order_date,
  date_trunc('month', order_date)::date as order_month,
  customer_id,
  product_id,
  store_id,
  payment_method,
  quantity,
  unit_price,
  discount_amount,
  net_revenue,
  cost,
  gross_margin
from {{ ref('int_retail_sales_enriched') }}
""",
        "models/marts/mart_sales_performance.sql": """
select
  order_month,
  count(distinct order_id) as orders,
  sum(quantity) as quantity,
  sum(net_revenue) as revenue,
  sum(gross_margin) as gross_margin
from {{ ref('fact_sales') }}
group by 1
""",
        "models/marts/mart_product_performance.sql": """
select
  p.product_category,
  p.product_name,
  sum(f.quantity) as quantity,
  sum(f.net_revenue) as revenue,
  sum(f.gross_margin) as gross_margin
from {{ ref('fact_sales') }} f
left join {{ ref('dim_product') }} p on f.product_id = p.product_id
group by 1, 2
""",
        "models/marts/mart_customer_segments.sql": """
select
  c.customer_segment,
  count(distinct f.order_id) as orders,
  sum(f.net_revenue) as revenue,
  sum(f.net_revenue) / nullif(count(distinct f.order_id), 0) as average_order_value
from {{ ref('fact_sales') }} f
left join {{ ref('dim_customer') }} c on f.customer_id = c.customer_id
group by 1
""",
        "models/marts/mart_store_performance.sql": """
select
  s.store_region,
  s.store_name,
  count(distinct f.order_id) as orders,
  sum(f.net_revenue) as revenue
from {{ ref('fact_sales') }} f
left join {{ ref('dim_store') }} s on f.store_id = s.store_id
group by 1, 2
""",
    }


def _dataset_model_slug(dataset: Dataset, *, max_length: int) -> str:
    stem = Path(dataset.name or dataset.id).stem
    tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9]+", stem)
        if token.lower() != "raw"
    ]
    slug = "_".join(tokens) or "dataset"
    if not re.match(r"^[a-z_]", slug):
        slug = f"dataset_{slug}"
    return slug[:max_length].strip("_") or "dataset"


def _dataset_model_suffix(dataset: Dataset) -> str:
    return hashlib.sha1(dataset.id.encode("utf-8")).hexdigest()[:8]


def _uploaded_base_model_names(dataset: Dataset) -> tuple[str, str]:
    suffix = _dataset_model_suffix(dataset)
    max_slug_length = min(
        64 - len("stg_") - len("_") - len(suffix),
        64 - len("int_") - len("_") - len(suffix) - len("_enriched"),
    )
    slug = _dataset_model_slug(dataset, max_length=max_slug_length)
    return f"stg_{slug}_{suffix}", f"int_{slug}_{suffix}_enriched"


def _generic_models(
    dataset: Dataset,
    proposal: ValidatedModelingProposal,
) -> dict[str, list[str]]:
    staging_model, intermediate_model = _uploaded_base_model_names(dataset)
    return {
        "staging": [staging_model],
        "intermediate": [intermediate_model],
        "dimensional_model": [
            proposal.fact_table_name,
            *[dimension.name for dimension in proposal.dimensions],
        ],
        "data_marts": [mart.name for mart in proposal.marts],
    }


def _relationship(
    *,
    from_model: str,
    to_model: str,
    relationship_type: str,
    join_fields: list[str],
) -> dict[str, object]:
    return {
        "from_model": from_model,
        "to_model": to_model,
        "relationship_type": relationship_type,
        "join_fields": join_fields,
    }


def _retail_model_metadata() -> dict[str, object]:
    dimensions = [
        {
            "name": "dim_customer",
            "grain": "one row per customer",
            "key_column": "customer_id",
            "columns": ["customer_id", "customer_name", "customer_segment"],
        },
        {
            "name": "dim_product",
            "grain": "one row per product",
            "key_column": "product_id",
            "columns": ["product_id", "product_name", "product_category"],
        },
        {
            "name": "dim_store",
            "grain": "one row per store",
            "key_column": "store_id",
            "columns": ["store_id", "store_name", "store_region"],
        },
        {
            "name": "dim_date",
            "grain": "one row per order date",
            "key_column": "order_date",
            "columns": ["order_date", "order_month", "order_year", "order_month_number"],
        },
    ]
    marts = [
        {
            "name": "mart_sales_performance",
            "grain": "one row per month",
            "dimensions": ["order_month"],
            "metrics": ["orders", "quantity", "revenue", "gross_margin"],
            "related_dimensions": ["dim_date"],
        },
        {
            "name": "mart_product_performance",
            "grain": "one row per product category and product",
            "dimensions": ["product_category", "product_name"],
            "metrics": ["quantity", "revenue", "gross_margin"],
            "related_dimensions": ["dim_product"],
        },
        {
            "name": "mart_customer_segments",
            "grain": "one row per customer segment",
            "dimensions": ["customer_segment"],
            "metrics": ["orders", "revenue", "average_order_value"],
            "related_dimensions": ["dim_customer"],
        },
        {
            "name": "mart_store_performance",
            "grain": "one row per store region and store",
            "dimensions": ["store_region", "store_name"],
            "metrics": ["orders", "revenue"],
            "related_dimensions": ["dim_store"],
        },
    ]
    relationships = [
        _relationship(
            from_model="fact_sales",
            to_model="dim_customer",
            relationship_type="fact_to_dimension",
            join_fields=["customer_id"],
        ),
        _relationship(
            from_model="fact_sales",
            to_model="dim_product",
            relationship_type="fact_to_dimension",
            join_fields=["product_id"],
        ),
        _relationship(
            from_model="fact_sales",
            to_model="dim_store",
            relationship_type="fact_to_dimension",
            join_fields=["store_id"],
        ),
        _relationship(
            from_model="fact_sales",
            to_model="dim_date",
            relationship_type="fact_to_dimension",
            join_fields=["order_date"],
        ),
        _relationship(
            from_model="mart_sales_performance",
            to_model="dim_date",
            relationship_type="mart_to_dimension",
            join_fields=["order_month"],
        ),
        _relationship(
            from_model="mart_product_performance",
            to_model="dim_product",
            relationship_type="mart_to_dimension",
            join_fields=["product_category", "product_name"],
        ),
        _relationship(
            from_model="mart_customer_segments",
            to_model="dim_customer",
            relationship_type="mart_to_dimension",
            join_fields=["customer_segment"],
        ),
        _relationship(
            from_model="mart_store_performance",
            to_model="dim_store",
            relationship_type="mart_to_dimension",
            join_fields=["store_region", "store_name"],
        ),
    ]
    return {
        "generated_from": "raw_retail_contract",
        "fact": {
            "name": "fact_sales",
            "grain": "one row per order line",
            "keys": [
                "order_line_id",
                "order_id",
                "customer_id",
                "product_id",
                "store_id",
                "order_date",
            ],
            "metrics": ["quantity", "revenue", "cost", "gross_margin"],
            "date_columns": ["order_date"],
            "degenerate_dimensions": ["payment_method"],
        },
        "dimensions": dimensions,
        "marts": marts,
        "relationships": relationships,
    }


def _dimension_grain(dimension: ValidatedModelDimension) -> str:
    entity_name = dimension.name.removeprefix("dim_").replace("_", " ")
    return f"one row per {entity_name}"


def _related_dimension_names(
    mart: ValidatedModelMart,
    dimensions: list[ValidatedModelDimension],
) -> list[str]:
    related: list[str] = []
    mart_dimension_set = set(mart.dimensions)
    for dimension in dimensions:
        if mart_dimension_set.intersection(dimension.columns):
            related.append(dimension.name)
    return related


def _model_metadata_from_proposal(
    proposal: ValidatedModelingProposal,
) -> dict[str, object]:
    dimensions = [
        {
            "name": dimension.name,
            "grain": _dimension_grain(dimension),
            "key_column": dimension.key_column,
            "columns": dimension.columns,
        }
        for dimension in proposal.dimensions
    ]
    marts = [
        {
            "name": mart.name,
            "grain": mart.grain,
            "dimensions": mart.dimensions,
            "metrics": mart.metrics,
            "related_dimensions": _related_dimension_names(mart, proposal.dimensions),
        }
        for mart in proposal.marts
    ]
    relationships = [
        _relationship(
            from_model=proposal.fact_table_name,
            to_model=dimension.name,
            relationship_type="fact_to_dimension",
            join_fields=[dimension.key_column],
        )
        for dimension in proposal.dimensions
    ]
    for mart in proposal.marts:
        for dimension in proposal.dimensions:
            join_fields = [
                field for field in mart.dimensions if field in set(dimension.columns)
            ]
            if not join_fields:
                continue
            relationships.append(
                _relationship(
                    from_model=mart.name,
                    to_model=dimension.name,
                    relationship_type="mart_to_dimension",
                    join_fields=join_fields,
                )
            )
    return {
        "generated_from": "modeling_proposal",
        "fact": {
            "name": proposal.fact_table_name,
            "grain": proposal.fact_grain,
            "keys": proposal.fact_dimension_keys,
            "metrics": proposal.fact_measures,
            "date_columns": proposal.fact_date_columns,
            "degenerate_dimensions": proposal.fact_degenerate_dimensions,
        },
        "dimensions": dimensions,
        "marts": marts,
        "relationships": relationships,
    }


def _unique_names(names: list[str]) -> list[str]:
    return list(dict.fromkeys(names))


def _sql_select_line(name: str, *, source: str | None = None) -> str:
    source_name = source or name
    return f"  {source_name} as {name}"


def _date_month_name(date_column: str) -> str:
    return f"{date_column}_month"


def _numeric_mapping_names(mappings: list[SemanticMapping]) -> set[str]:
    return {
        mapping.approved_name
        for mapping in mappings
        if mapping.approved_role in {"measure_column", "metric_candidate"}
        or mapping.profile.detected_type in {"integer", "decimal"}
    }


def _date_mapping_names(mappings: list[SemanticMapping]) -> set[str]:
    return {
        mapping.approved_name
        for mapping in mappings
        if mapping.approved_role == "date_time" or mapping.profile.detected_type == "date"
    }


def _generic_sql(
    dataset: Dataset,
    mappings: list[SemanticMapping],
    proposal: ValidatedModelingProposal,
) -> dict[str, str]:
    raw_relation = _raw_relation(dataset)
    staging_model, intermediate_model = _uploaded_base_model_names(dataset)
    select_lines = [
        f"  nullif(trim({snowflake_service.quote_identifier(mapping.profile.snowflake_column_name)}), '') "
        f"as {mapping.approved_name}"
        for mapping in mappings
    ]
    numeric_names = _numeric_mapping_names(mappings)
    date_names = _date_mapping_names(mappings)
    intermediate_lines: list[str] = []
    for mapping in mappings:
        if mapping.approved_name in numeric_names:
            intermediate_lines.append(
                f"  try_to_decimal({mapping.approved_name}, 18, 2) as {mapping.approved_name}"
            )
        elif mapping.approved_name in date_names:
            intermediate_lines.append(
                f"  try_to_date({mapping.approved_name}) as {mapping.approved_name}"
            )
        else:
            intermediate_lines.append(
                f"  nullif(trim({mapping.approved_name}), '') as {mapping.approved_name}"
            )
    for date_column in proposal.fact_date_columns:
        intermediate_lines.append(
            "  date_trunc('month', "
            f"{date_column})::date as {_date_month_name(date_column)}"
        )

    fact_columns = _unique_names(
        [
            *proposal.fact_keys,
            *proposal.fact_dimension_keys,
            *proposal.fact_degenerate_dimensions,
            *proposal.fact_date_columns,
            *[_date_month_name(date_column) for date_column in proposal.fact_date_columns],
            *proposal.fact_measures,
        ]
    )
    fact_select_lines = [_sql_select_line(column) for column in fact_columns]
    sql_files = {
        f"models/staging/{staging_model}.sql": (
            "select\n"
            + ",\n".join(select_lines)
            + f"\nfrom {raw_relation}"
        ),
        f"models/intermediate/{intermediate_model}.sql": (
            "select\n"
            + ",\n".join(intermediate_lines)
            + f"\nfrom {{{{ ref('{staging_model}') }}}}"
        ),
        f"models/dimensional/{proposal.fact_table_name}.sql": (
            "select\n"
            + ",\n".join(fact_select_lines)
            + f"\nfrom {{{{ ref('{intermediate_model}') }}}}"
        ),
    }
    for dimension in proposal.dimensions:
        dimension_lines = [_sql_select_line(column) for column in dimension.columns]
        sql_files[f"models/dimensional/{dimension.name}.sql"] = (
            "select distinct\n"
            + ",\n".join(dimension_lines)
            + f"\nfrom {{{{ ref('{intermediate_model}') }}}}\n"
            f"where {dimension.key_column} is not null"
        )

    dimension_by_column: dict[str, ValidatedModelDimension] = {}
    for dimension in proposal.dimensions:
        for column in dimension.columns:
            dimension_by_column.setdefault(column, dimension)
    fact_column_set = set(fact_columns)
    for mart in proposal.marts:
        joins: dict[str, tuple[str, str]] = {}
        dimension_exprs: list[str] = []
        for dimension_name in mart.dimensions:
            if dimension_name in fact_column_set:
                dimension_exprs.append(f"  f.{dimension_name} as {dimension_name}")
                continue
            dimension = dimension_by_column.get(dimension_name)
            if dimension is None:
                continue
            alias = f"d_{dimension.name[4:]}"
            joins[dimension.name] = (alias, dimension.key_column)
            dimension_exprs.append(f"  {alias}.{dimension_name} as {dimension_name}")

        metric_exprs = [f"  sum(f.{metric}) as {metric}" for metric in mart.metrics]
        join_lines = [
            f"left join {{{{ ref('{dimension_name}') }}}} {alias} "
            f"on f.{key_column} = {alias}.{key_column}"
            for dimension_name, (alias, key_column) in joins.items()
        ]
        group_by = ", ".join(str(index) for index in range(1, len(dimension_exprs) + 1))
        sql_files[f"models/marts/{mart.name}.sql"] = (
            "select\n"
            + ",\n".join([*dimension_exprs, *metric_exprs])
            + f"\nfrom {{{{ ref('{proposal.fact_table_name}') }}}} f"
            + ("\n" + "\n".join(join_lines) if join_lines else "")
            + f"\ngroup by {group_by}"
        )

    return sql_files


def _generated_project(
    *,
    dataset: Dataset,
    transformation_run: DatasetTransformationRun,
    mappings: list[SemanticMapping],
    config: Settings,
    modeling_proposal: ValidatedModelingProposal | None = None,
) -> GeneratedDbtProject:
    project_name = f"meshflow_{re.sub(r'[^A-Za-z0-9_]+', '_', dataset.id).lower()}"
    profile_name = f"{project_name}_profile"
    project_dir = Path(config.dbt_projects_dir) / dataset.id / transformation_run.id
    profiles_dir = project_dir / "profiles"

    if dataset.source_type == RAW_RETAIL_DEMO_SOURCE_TYPE:
        models = RAW_RETAIL_MODELS
        sql_files = _retail_sql(_raw_relation(dataset))
        modeling_proposal_json = (
            proposal_to_json(modeling_proposal)
            if modeling_proposal is not None
            else None
        )
        analysis_catalog = None
        model_metadata = _retail_model_metadata()
    else:
        if modeling_proposal is None:
            raise AppError(
                error_code="MODELING_PROPOSAL_FAILED",
                failed_step="modeling_proposal",
                message="Uploaded CSV transformation requires a validated modeling proposal.",
                next_action="Generate or retry the modeling proposal before dbt transformation.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        models = _generic_models(dataset, modeling_proposal)
        sql_files = _generic_sql(dataset, mappings, modeling_proposal)
        modeling_proposal_json = proposal_to_json(modeling_proposal)
        analysis_catalog = proposal_analysis_catalog(modeling_proposal)
        model_metadata = _model_metadata_from_proposal(modeling_proposal)

    project_yml = _project_yml(project_name, profile_name)
    profiles_yml = _profile_yml(profile_name, config.dbt_target_name, config.dbt_threads)
    schema_yml = _schema_yml(models)

    files: list[tuple[str, str, str, str, Path | None]] = []
    project_file = project_dir / "dbt_project.yml"
    profile_file = profiles_dir / "profiles.yml"
    schema_file = project_dir / "models/schema.yml"
    _write_file(project_file, project_yml)
    _write_file(profile_file, profiles_yml)
    _write_file(schema_file, schema_yml)
    files.append(("project_yml", "project", "dbt_project.yml", project_yml, project_file))
    files.append(("profiles_yml_redacted", "project", "profiles.yml", profiles_yml, profile_file))
    files.append(("schema_yml", "project", "schema.yml", schema_yml, schema_file))
    if modeling_proposal_json is not None:
        files.append(
            (
                "modeling_proposal_json",
                "project",
                "modeling_proposal",
                json.dumps(modeling_proposal_json, separators=(",", ":")),
                None,
            )
        )

    for relative_path, content in sql_files.items():
        file_path = project_dir / relative_path
        _write_file(file_path, content)
        layer = relative_path.split("/")[1]
        files.append(("model_sql", layer, file_path.stem, content, file_path))

    return GeneratedDbtProject(
        project_dir=project_dir,
        profiles_dir=profiles_dir,
        project_name=project_name,
        profile_name=profile_name,
        models=models,
        artifacts=files,
        modeling_proposal=modeling_proposal_json,
        analysis_catalog=analysis_catalog,
        model_metadata=model_metadata,
    )


def _store_generated_artifacts(
    *,
    db: Session,
    dataset: Dataset,
    transformation_run: DatasetTransformationRun,
    project: GeneratedDbtProject,
    config: Settings,
) -> None:
    for artifact_type, layer, name, content, file_path in project.artifacts:
        db.add(
            DbtArtifact(
                dataset=dataset,
                transformation_run=transformation_run,
                artifact_type=artifact_type,
                layer=layer,
                name=name,
                content_redacted=_redact(content, config),
                file_path=str(file_path) if file_path else None,
            )
        )


def _clear_previous_data_flow(db: Session, dataset: Dataset) -> None:
    for edge in list(dataset.data_flow_edges):
        db.delete(edge)
    for node in list(dataset.data_flow_nodes):
        db.delete(node)


def _initial_node_status(node_type: str) -> str:
    if node_type in {"raw_input", "warehouse_raw"}:
        return "completed"
    return "waiting"


def _initialize_data_flow_progress(
    *,
    db: Session,
    dataset: Dataset,
    models: dict[str, list[str]],
) -> None:
    _clear_previous_data_flow(db, dataset)
    nodes: list[DataFlowNode] = []
    for node_type, label in PREP_NODE_SPECS:
        layer_key = "data_marts" if node_type == "data_mart" else node_type
        model_names = models.get(layer_key, [])
        node = DataFlowNode(
            dataset=dataset,
            node_type=node_type,
            name=node_type,
            label=label,
            status=_initial_node_status(node_type),
            metadata_json={"models": model_names} if model_names else None,
        )
        db.add(node)
        nodes.append(node)

    db.flush()
    for from_node, to_node in zip(nodes, nodes[1:], strict=False):
        db.add(
            DataFlowEdge(
                dataset=dataset,
                from_node=from_node,
                to_node=to_node,
                edge_type="prepares",
                metadata_json=None,
            )
        )


def _set_data_flow_node_status(
    *,
    db: Session,
    dataset: Dataset,
    node_type: str,
    node_status: str,
) -> None:
    for node in dataset.data_flow_nodes:
        if node.node_type == node_type:
            node.status = node_status
            db.commit()
            return


def _store_data_flow(
    *,
    db: Session,
    dataset: Dataset,
    models: dict[str, list[str]],
) -> None:
    nodes: list[DataFlowNode] = []
    for node_type, label in PREP_NODE_SPECS:
        layer_key = "data_marts" if node_type == "data_mart" else node_type
        model_names = models.get(layer_key, [])
        node = DataFlowNode(
            dataset=dataset,
            node_type=node_type,
            name=node_type,
            label=label,
            status="completed",
            metadata_json={"models": model_names} if model_names else None,
        )
        db.add(node)
        nodes.append(node)

    db.flush()
    for from_node, to_node in zip(nodes, nodes[1:], strict=False):
        db.add(
            DataFlowEdge(
                dataset=dataset,
                from_node=from_node,
                to_node=to_node,
                edge_type="prepares",
                metadata_json=None,
            )
        )


def _store_run_result_artifact(
    *,
    db: Session,
    dataset: Dataset,
    transformation_run: DatasetTransformationRun,
    summary: dict[str, object],
) -> None:
    db.add(
        DbtArtifact(
            dataset=dataset,
            transformation_run=transformation_run,
            artifact_type="run_result_summary",
            layer="project",
            name="dbt_run_summary",
            content_redacted=str(summary),
            file_path=None,
        )
    )


def _completed_transform_response(
    dataset: Dataset,
    transformation_run: DatasetTransformationRun,
    models: dict[str, list[str]],
    model_metadata: dict[str, object] | None = None,
) -> DatasetTransformResponse:
    return DatasetTransformResponse(
        status="completed",
        dataset=dataset_summary(dataset),
        transformation_run=_summary_from_run(transformation_run),
        layers_completed=TRANSFORMATION_LAYERS,
        models=models,
        model_metadata=model_metadata,
        next_route="/demo/dashboard",
    )


def transform_dataset(
    db: Session,
    session_id: str | None,
    dataset_id: str,
    *,
    force: bool = False,
    config: Settings = settings,
) -> DatasetTransformResponse:
    dataset = _load_dataset(db, session_id, dataset_id)
    _ensure_transformable_dataset(dataset)

    latest_success = next(
        (
            run
            for run in reversed(dataset.transformation_runs)
            if run.status == "completed" and run.dbt_run_summary_json
        ),
        None,
    )
    if dataset.status == "ready_for_analysis" and latest_success is not None and not force:
        return _completed_transform_response(
            dataset,
            latest_success,
            latest_success.dbt_run_summary_json.get("models", {}) if latest_success.dbt_run_summary_json else {},
            _model_metadata_from_run(latest_success),
        )

    mappings = _ensure_semantic_mappings(dataset)
    _ensure_uploaded_csv_support(dataset, mappings)

    transformation_run = DatasetTransformationRun(
        dataset=dataset,
        status="running",
        started_at=utc_now(),
        dbt_target_name=config.dbt_target_name,
    )
    dataset.status = "transforming"
    db.add(transformation_run)
    db.commit()
    db.refresh(dataset)
    db.refresh(transformation_run)

    try:
        _ensure_snowflake_ready(config)
        modeling_proposal = create_modeling_proposal(
            db,
            dataset,
            mappings,
            config=config,
        )
        project = _generated_project(
            dataset=dataset,
            transformation_run=transformation_run,
            mappings=mappings,
            config=config,
            modeling_proposal=modeling_proposal,
        )
        transformation_run.dbt_project_path = str(project.project_dir)
        _store_generated_artifacts(
            db=db,
            dataset=dataset,
            transformation_run=transformation_run,
            project=project,
            config=config,
        )
        _initialize_data_flow_progress(db=db, dataset=dataset, models=project.models)
        db.commit()
        db.refresh(dataset)

        def mark_layer_status(node_type: str, node_status: str) -> None:
            _set_data_flow_node_status(
                db=db,
                dataset=dataset,
                node_type=node_type,
                node_status=node_status,
            )

        command_summary = run_dbt_commands(
            project_dir=project.project_dir,
            profiles_dir=project.profiles_dir,
            target_name=config.dbt_target_name,
            config=config,
            on_layer_status=mark_layer_status,
        )
        transformation_run.status = "completed"
        transformation_run.completed_at = utc_now()
        run_summary_json = {
            "models": project.models,
            "commands": command_summary,
            "model_metadata": project.model_metadata,
        }
        if project.modeling_proposal is not None:
            run_summary_json["modeling_proposal"] = project.modeling_proposal
        if project.analysis_catalog is not None:
            run_summary_json["analysis_catalog"] = project.analysis_catalog
        transformation_run.dbt_run_summary_json = run_summary_json
        dataset.status = "ready_for_analysis"
        _clear_previous_data_flow(db, dataset)
        _store_data_flow(db=db, dataset=dataset, models=project.models)
        try:
            question_result = generate_dataset_question_suggestions(
                db,
                dataset,
                force=True,
                config=config,
            )
            run_summary_json["question_suggestions"] = {
                "status": question_result.status,
                "message": question_result.message,
                "question_count": question_result.question_count,
            }
        except Exception as exc:
            run_summary_json["question_suggestions"] = {
                "status": "failed",
                "message": (
                    "Question suggestion generation failed after dbt success: "
                    f"{exc.__class__.__name__}."
                ),
                "question_count": 0,
            }
        transformation_run.dbt_run_summary_json = run_summary_json
        _store_run_result_artifact(
            db=db,
            dataset=dataset,
            transformation_run=transformation_run,
            summary=run_summary_json,
        )
        db.commit()
        db.refresh(dataset)
        db.refresh(transformation_run)
        return _completed_transform_response(
            dataset,
            transformation_run,
            project.models,
            project.model_metadata,
        )
    except AppError as exc:
        transformation_run.status = "failed"
        transformation_run.completed_at = utc_now()
        transformation_run.failed_step = exc.failed_step
        transformation_run.error_code = exc.error_code
        transformation_run.error_message = exc.message
        transformation_run.dbt_run_summary_json = {"error": exc.error_code}
        dataset.status = "transform_failed"
        db.commit()
        raise
    except DbtExecutionError as exc:
        transformation_run.status = "failed"
        transformation_run.completed_at = utc_now()
        transformation_run.failed_step = exc.failed_step
        transformation_run.error_code = exc.error_code
        transformation_run.error_message = exc.message
        transformation_run.dbt_run_summary_json = exc.command_summary
        dataset.status = "transform_failed"
        db.commit()
        raise AppError(
            error_code=exc.error_code,
            failed_step=exc.failed_step,
            message=exc.message,
            next_action="Review dbt setup, schema mappings, and run evidence, then retry Transform.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc
    except OSError as exc:
        transformation_run.status = "failed"
        transformation_run.completed_at = utc_now()
        transformation_run.failed_step = "dbt_project_generation"
        transformation_run.error_code = "DBT_PROJECT_GENERATION_FAILED"
        transformation_run.error_message = "MeshFlow could not generate the dbt project files."
        transformation_run.dbt_run_summary_json = {"error": "DBT_PROJECT_GENERATION_FAILED"}
        dataset.status = "transform_failed"
        db.commit()
        raise AppError(
            error_code="DBT_PROJECT_GENERATION_FAILED",
            failed_step="dbt_project_generation",
            message="MeshFlow could not generate the dbt project files.",
            next_action="Check backend local runtime directory permissions, then retry.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


def _synthetic_data_flow(dataset: Dataset) -> tuple[list[DataFlowNodeSummary], list[DataFlowEdgeSummary]]:
    if dataset.status == "ready_for_analysis":
        statuses = ["completed"] * len(PREP_NODE_SPECS)
    elif dataset.status == "transforming":
        statuses = ["completed", "completed", "waiting", "waiting", "waiting", "waiting"]
    else:
        statuses = ["completed", "completed", "not_started", "not_started", "not_started", "not_started"]

    nodes = [
        DataFlowNodeSummary(
            id=f"{dataset.id}:{node_type}",
            node_type=node_type,
            name=node_type,
            label=label,
            status=node_status,
            metadata=None,
        )
        for (node_type, label), node_status in zip(PREP_NODE_SPECS, statuses, strict=True)
    ]
    edges = [
        DataFlowEdgeSummary(
            id=f"{nodes[index].id}->{nodes[index + 1].id}",
            from_node_id=nodes[index].id,
            to_node_id=nodes[index + 1].id,
            edge_type="prepares",
            metadata=None,
        )
        for index in range(len(nodes) - 1)
    ]
    return nodes, edges


def _models_from_run(run: DatasetTransformationRun | None) -> dict[str, list[str]]:
    if not run or not run.dbt_run_summary_json:
        return {}
    models = run.dbt_run_summary_json.get("models")
    if not isinstance(models, dict):
        return {}
    return {
        str(layer): [str(model) for model in model_list]
        for layer, model_list in models.items()
        if isinstance(model_list, list)
    }


def _model_metadata_from_run(run: DatasetTransformationRun | None) -> dict[str, object] | None:
    if not run or not run.dbt_run_summary_json:
        return None
    model_metadata = run.dbt_run_summary_json.get("model_metadata")
    if not isinstance(model_metadata, dict):
        return None
    return model_metadata


def _snowflake_configured(config: Settings) -> bool:
    return bool(
        config.snowflake_account
        and config.snowflake_user
        and config.snowflake_password
        and config.snowflake_warehouse
        and config.snowflake_database
        and config.snowflake_schema
    )


def _raw_preview_from_dataset(
    dataset: Dataset,
    *,
    config: Settings = settings,
) -> RawTablePreviewResponse:
    columns = [profile.raw_column_name for profile in dataset.column_profiles]
    snowflake_columns = [
        (profile.snowflake_column_name, profile.raw_column_name)
        for profile in dataset.column_profiles
    ]

    if not _snowflake_configured(config):
        return RawTablePreviewResponse(
            status="not_configured",
            columns=columns,
            rows=[],
            row_count_previewed=0,
            message="Snowflake is not configured, so raw row preview is unavailable.",
        )

    try:
        result = snowflake_service.execute_raw_table_preview(
            raw_table_name=dataset.raw_table_name,
            columns=snowflake_columns,
            preview_limit=10,
            config=config,
        )
    except snowflake_service.SnowflakeServiceError:
        return RawTablePreviewResponse(
            status="failed",
            columns=columns,
            rows=[],
            row_count_previewed=0,
            message="MeshFlow could not read the first 10 rows from the Snowflake raw table.",
        )

    return RawTablePreviewResponse(
        status="completed",
        columns=columns,
        rows=result.preview_rows,
        row_count_previewed=result.row_count,
        message=None,
    )


def get_dataset_data_flow(
    db: Session,
    session_id: str | None,
    dataset_id: str,
    config: Settings = settings,
) -> DatasetDataFlowResponse:
    dataset = _load_dataset(db, session_id, dataset_id)
    latest_run = dataset.transformation_runs[-1] if dataset.transformation_runs else None
    latest_run_artifacts = [
        artifact
        for artifact in dataset.dbt_artifacts
        if latest_run and artifact.transformation_run_id == latest_run.id
    ]
    if dataset.data_flow_nodes:
        nodes = [_node_summary(node) for node in dataset.data_flow_nodes]
        edges = [_edge_summary(edge) for edge in dataset.data_flow_edges]
    else:
        nodes, edges = _synthetic_data_flow(dataset)

    return DatasetDataFlowResponse(
        dataset=dataset_summary(dataset),
        transformation=_summary_from_run(latest_run) if latest_run else None,
        nodes=nodes,
        edges=edges,
        artifacts=[_artifact_summary(artifact) for artifact in latest_run_artifacts],
        models=_models_from_run(latest_run),
        model_metadata=_model_metadata_from_run(latest_run),
        raw_preview=_raw_preview_from_dataset(dataset, config=config),
        question_suggestions=question_suggestions_summary_from_dataset(dataset),
    )


def cleanup_dataset_runtime_artifacts(
    *,
    dataset_id: str,
    config: Settings = settings,
) -> CleanupOperationResult:
    base_dir = Path(config.dbt_projects_dir).resolve()
    target_dir = (base_dir / dataset_id).resolve()
    if not target_dir.exists():
        return CleanupOperationResult(status="skipped")
    if target_dir == base_dir or not target_dir.is_relative_to(base_dir):
        return CleanupOperationResult(
            status="failed",
            warning="dbt runtime cleanup refused to remove a path outside DBT_PROJECTS_DIR.",
        )

    try:
        shutil.rmtree(target_dir)
    except OSError as exc:
        return CleanupOperationResult(
            status="failed",
            warning=f"dbt runtime cleanup failed for dataset {dataset_id}: {exc.__class__.__name__}.",
        )

    return CleanupOperationResult(status="completed")


def cleanup_dataset_model_tables(
    *,
    dataset: Dataset,
    config: Settings = settings,
) -> CleanupOperationResult:
    model_names: set[str] = set()
    for run in dataset.transformation_runs:
        summary = run.dbt_run_summary_json or {}
        models = summary.get("models")
        if not isinstance(models, dict):
            continue
        for layer_models in models.values():
            if not isinstance(layer_models, list):
                continue
            model_names.update(str(model_name) for model_name in layer_models)

    if not model_names:
        return CleanupOperationResult(status="skipped")

    unexpected = sorted(
        model_name
        for model_name in model_names
        if model_name not in KNOWN_DBT_MODEL_TABLES
        and not (
            SAFE_NAME_RE.fullmatch(model_name)
            and model_name.startswith(GENERATED_MODEL_PREFIXES)
        )
    )
    unsafe = sorted(model_name for model_name in model_names if not SAFE_NAME_RE.fullmatch(model_name))
    if unexpected or unsafe:
        return CleanupOperationResult(
            status="failed",
            warning=(
                "Snowflake dbt model cleanup skipped because the model list included "
                "unexpected or unsafe names."
            ),
        )

    return snowflake_service.drop_tables_for_cleanup(
        table_names=sorted(model_names),
        config=config,
    )
