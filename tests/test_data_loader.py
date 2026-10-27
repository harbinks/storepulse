"""
Unit tests for StorePulse data ingestion, validation, and sanitization.
Validates schema validation, duplicate removal, invalid values coercion, and file buffer loading.
"""

from io import StringIO
import pytest
import pandas as pd
from src.data_loader import (
    validate_schema,
    clean_and_preprocess,
    load_dataset_from_source,
    get_default_sample_path,
)


def test_validate_schema_valid():
    """Verify validation passes when all required columns are present."""
    df = pd.DataFrame([{
        "month": "2025-10",
        "store_id": "ST-01",
        "store_name": "Test Store",
        "city": "Bangalore",
        "tier": "Tier 1",
        "store_format": "Standard",
        "revenue": 100000.0,
        "rent": 10000.0,
        "payroll": 10000.0,
        "marketing": 5000.0,
        "utilities": 2000.0,
        "other_expenses": 1000.0,
    }])
    is_valid, issues = validate_schema(df)
    assert is_valid is True
    assert len(issues) == 0


def test_validate_schema_missing_columns():
    """Verify missing required columns are flagged explicitly."""
    df_missing = pd.DataFrame([{"month": "2025-10", "revenue": 100000.0}])
    is_valid, issues = validate_schema(df_missing)
    assert is_valid is False
    assert any("Missing required columns" in issue for issue in issues)


def test_clean_and_preprocess_deduplication():
    """Verify duplicate (store_id, month) rows are deduplicated with warning."""
    df_dups = pd.DataFrame([
        {
            "month": "2025-10",
            "store_id": "ST-01",
            "store_name": "Test Store",
            "city": "Bangalore",
            "tier": "Tier 1",
            "store_format": "Standard",
            "revenue": 100000.0,
            "rent": 10000.0,
            "payroll": 10000.0,
            "marketing": 5000.0,
            "utilities": 2000.0,
            "other_expenses": 1000.0,
        },
        {
            "month": "2025-10",  # Duplicate row
            "store_id": "ST-01",
            "store_name": "Test Store Duplicate",
            "city": "Bangalore",
            "tier": "Tier 1",
            "store_format": "Standard",
            "revenue": 999999.0,
            "rent": 10000.0,
            "payroll": 10000.0,
            "marketing": 5000.0,
            "utilities": 2000.0,
            "other_expenses": 1000.0,
        },
    ])
    cleaned, warnings, errors = clean_and_preprocess(df_dups)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["revenue"] == 100000.0
    assert any("duplicate" in w.lower() for w in warnings)
    assert len(errors) == 0


def test_clean_and_preprocess_negative_values():
    """Verify negative numbers are floored to 0.0 with warning."""
    df_neg = pd.DataFrame([{
        "month": "2025-10",
        "store_id": "ST-01",
        "store_name": "Test Store",
        "city": "Bangalore",
        "tier": "Tier 1",
        "store_format": "Standard",
        "revenue": -50000.0,
        "rent": 10000.0,
        "payroll": -5000.0,
        "marketing": 5000.0,
        "utilities": 2000.0,
        "other_expenses": 1000.0,
    }])
    cleaned, warnings, errors = clean_and_preprocess(df_neg)
    assert cleaned.iloc[0]["revenue"] == 0.0
    assert cleaned.iloc[0]["payroll"] == 0.0
    assert any("negative" in w.lower() for w in warnings)


def test_clean_and_preprocess_missing_and_corrupt_values():
    """Verify non-numeric values are safely coerced to 0.0 with warning."""
    df_corrupt = pd.DataFrame([{
        "month": "2025-10",
        "store_id": "ST-01",
        "store_name": "Test Store",
        "city": "Bangalore",
        "tier": "Tier 1",
        "store_format": "Standard",
        "revenue": "INVALID_TEXT",
        "rent": 10000.0,
        "payroll": None,
        "marketing": 5000.0,
        "utilities": 2000.0,
        "other_expenses": 1000.0,
    }])
    cleaned, warnings, errors = clean_and_preprocess(df_corrupt)
    assert cleaned.iloc[0]["revenue"] == 0.0
    assert cleaned.iloc[0]["payroll"] == 0.0


def test_load_sample_csv_exists():
    """Verify bundled sample dataset loads cleanly without errors."""
    path = get_default_sample_path()
    df, warnings, errors = load_dataset_from_source(path)
    assert len(errors) == 0
    assert len(df) == 72
    assert df["store_id"].nunique() == 12
    assert df["month"].nunique() == 6
