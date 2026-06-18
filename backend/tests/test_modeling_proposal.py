import json
from types import SimpleNamespace

import pytest

from app.models.dataset import ColumnProfile
from app.services.modeling_proposal_service import (
    ModelingProposalValidationError,
    validate_modeling_proposal_output,
)


def mapping(name: str, role: str, detected_type: str):
    return SimpleNamespace(
        profile=ColumnProfile(
            raw_column_name=name,
            normalized_column_name=name.upper(),
            snowflake_column_name=name.upper(),
            detected_type=detected_type,
            null_count=0,
            null_rate=0,
            unique_count=4,
            sample_values_json=["sample"],
        ),
        approved_name=name,
        approved_role=role,
    )


def mappings():
    return [
        mapping("invoice_line_id", "identifier", "identifier"),
        mapping("invoice_date", "date_time", "date"),
        mapping("customer_id", "identifier", "identifier"),
        mapping("customer_segment", "dimension", "string"),
        mapping("product_id", "identifier", "identifier"),
        mapping("product_category", "dimension", "string"),
        mapping("net_revenue", "measure_column", "decimal"),
        mapping("gross_margin", "measure_column", "decimal"),
    ]


def proposal_payload(metric: str = "net_revenue") -> str:
    return json.dumps(
        {
            "grain": "one row per invoice line",
            "fact_table": {
                "name": "fact_invoice_lines",
                "grain": "one row per invoice line",
                "keys": ["invoice_line_id"],
                "measures": [metric, "gross_margin"],
                "date_columns": ["invoice_date"],
            },
            "dimensions": [
                {
                    "name": "dim_customer",
                    "key_column": "customer_id",
                    "columns": ["customer_id", "customer_segment"],
                },
                {
                    "name": "dim_product",
                    "key_column": "product_id",
                    "columns": ["product_id", "product_category"],
                },
            ],
            "marts": [
                {
                    "name": "mart_customer_segments",
                    "grain": "one row per customer segment",
                    "dimensions": ["customer_segment"],
                    "metrics": [metric],
                }
            ],
            "warnings": [],
        }
    )


def test_validate_modeling_proposal_accepts_star_schema() -> None:
    proposal = validate_modeling_proposal_output(proposal_payload(), mappings=mappings())

    assert proposal.fact_table_name == "fact_invoice_lines"
    assert proposal.dimensions[0].name == "dim_customer"
    assert proposal.marts[0].dimensions == ["customer_segment"]


def test_validate_modeling_proposal_rejects_unknown_metric() -> None:
    with pytest.raises(ModelingProposalValidationError):
        validate_modeling_proposal_output(
            proposal_payload(metric="fake_profit"),
            mappings=mappings(),
        )
