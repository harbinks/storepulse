"""
Data loading, validation, and preprocessing module for StorePulse.
Handles CSV uploads, strict schema checks, duplicate detection, and missing/invalid value remediation.
"""

from io import BytesIO, StringIO
import os
from typing import Tuple, List, Optional
import pandas as pd
from src.config import REQUIRED_COLUMNS, EXPENSE_COLUMNS


class DataValidationError(Exception):
    """Raised when uploaded CSV fails fundamental schema or structure validation."""
    pass


def get_default_sample_path() -> str:
    """Return absolute path to bundled sample CSV file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", "sample_store_pnl.csv")


def validate_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that dataframe conforms to StorePulse expected column schema.
    Returns (is_valid, list_of_error_messages).
    """
    issues = []
    if df is None or df.empty:
        issues.append("Dataset is empty. At least one row of store P&L data is required.")
        return False, issues

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        issues.append(f"Missing required columns: {', '.join(missing_cols)}")

    return len(issues) == 0, issues


def clean_and_preprocess(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Clean and sanitize raw P&L dataframe.
    - Strips whitespace
    - Casts numeric fields
    - Deduplicates (store_id, month)
    - Validates missing / zero / negative values
    Returns:
        (cleaned_df, warnings_list, errors_list)
    """
    warnings = []
    errors = []

    if df is None or df.empty:
        errors.append("Empty dataset provided.")
        return pd.DataFrame(), warnings, errors

    # Check schema
    valid, schema_issues = validate_schema(df)
    if not valid:
        return df, warnings, schema_issues

    cleaned = df.copy()

    # Normalize text columns
    text_cols = ["month", "store_id", "store_name", "city", "tier", "store_format"]
    for col in text_cols:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].astype(str).str.strip()

    # Format month if needed (ensure YYYY-MM)
    cleaned["month"] = cleaned["month"].astype(str).str.slice(0, 7)

    # Cast numeric columns
    numeric_cols = ["revenue"] + EXPENSE_COLUMNS
    for col in numeric_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
            nan_count = cleaned[col].isna().sum()
            if nan_count > 0:
                warnings.append(
                    f"Column '{col}' contained {nan_count} non-numeric or missing entries; imputed with 0.0."
                )
                cleaned[col] = cleaned[col].fillna(0.0)

            # Check for negative values
            neg_count = (cleaned[col] < 0).sum()
            if neg_count > 0:
                warnings.append(
                    f"Column '{col}' contained {neg_count} negative values; floored to 0.0."
                )
                cleaned[col] = cleaned[col].clip(lower=0.0)

    # Check duplicate records for same store and month
    dup_mask = cleaned.duplicated(subset=["store_id", "month"], keep="first")
    dup_count = dup_mask.sum()
    if dup_count > 0:
        warnings.append(
            f"Detected {dup_count} duplicate (store_id, month) rows. Kept first occurrence and discarded duplicates."
        )
        cleaned = cleaned[~dup_mask].copy()

    # Sort deterministically
    cleaned = cleaned.sort_values(by=["store_id", "month"]).reset_index(drop=True)

    return cleaned, warnings, errors


def load_dataset_from_source(source) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Load dataset from a file path, file-like buffer, or Streamlit UploadedFile.
    """
    try:
        if isinstance(source, (str, os.PathLike)):
            if not os.path.exists(source):
                return pd.DataFrame(), [], [f"File not found: {source}"]
            raw_df = pd.read_csv(source)
        elif hasattr(source, "read"):
            source.seek(0)
            raw_df = pd.read_csv(source)
        elif isinstance(source, (StringIO, BytesIO)):
            raw_df = pd.read_csv(source)
        else:
            return pd.DataFrame(), [], ["Unsupported data source type."]
    except Exception as e:
        return pd.DataFrame(), [], [f"Failed to parse CSV file: {str(e)}"]

    return clean_and_preprocess(raw_df)
