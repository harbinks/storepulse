"""
Unit tests for StorePulse financial calculations, metrics, and peer benchmarks.
Validates 4-wall unit economics, zero-revenue safety, negative contribution handling,
and historical variance formulas.
"""

import pytest
import pandas as pd
import numpy as np

from src.financial_engine import (
    compute_store_pnl_metrics,
    compute_historical_variances,
    compute_peer_benchmarks,
    get_executive_kpis,
)


@pytest.fixture
def base_sample_df():
    """Provides a controlled two-month, two-store financial fixture."""
    return pd.DataFrame([
        {
            "month": "2025-10",
            "store_id": "ST-01",
            "store_name": "Store 1",
            "city": "Bangalore",
            "tier": "Tier 1",
            "store_format": "Flagship",
            "revenue": 5000000.0,
            "rent": 1000000.0,
            "payroll": 800000.0,
            "marketing": 400000.0,
            "utilities": 200000.0,
            "other_expenses": 100000.0,
        },
        {
            "month": "2025-11",
            "store_id": "ST-01",
            "store_name": "Store 1",
            "city": "Bangalore",
            "tier": "Tier 1",
            "store_format": "Flagship",
            "revenue": 6000000.0,
            "rent": 1000000.0,
            "payroll": 850000.0,
            "marketing": 500000.0,
            "utilities": 220000.0,
            "other_expenses": 130000.0,
        },
        {
            "month": "2025-10",
            "store_id": "ST-02",
            "store_name": "Store 2",
            "city": "Mumbai",
            "tier": "Tier 1",
            "store_format": "Standard",
            "revenue": 3000000.0,
            "rent": 600000.0,
            "payroll": 500000.0,
            "marketing": 300000.0,
            "utilities": 150000.0,
            "other_expenses": 50000.0,
        },
        {
            "month": "2025-11",
            "store_id": "ST-02",
            "store_name": "Store 2",
            "city": "Mumbai",
            "tier": "Tier 1",
            "store_format": "Standard",
            "revenue": 2000000.0,
            "rent": 600000.0,
            "payroll": 500000.0,
            "marketing": 300000.0,
            "utilities": 150000.0,
            "other_expenses": 500000.0,  # Elevated expenses causing loss
        },
    ])


def test_compute_store_pnl_metrics_standard(base_sample_df):
    """Test standard 4-wall unit economics math."""
    res = compute_store_pnl_metrics(base_sample_df)
    
    # Store 1 Oct: Total Exp = 1000k + 800k + 400k + 200k + 100k = 2,500,000
    st1_oct = res[(res["store_id"] == "ST-01") & (res["month"] == "2025-10")].iloc[0]
    assert st1_oct["total_expenses"] == 2500000.0
    assert st1_oct["operating_profit_proxy"] == 2500000.0
    assert pytest.approx(st1_oct["operating_margin_pct"], 0.01) == 50.0
    assert pytest.approx(st1_oct["rent_ratio_pct"], 0.01) == 20.0
    assert pytest.approx(st1_oct["payroll_ratio_pct"], 0.01) == 16.0


def test_zero_revenue_handling():
    """Verify zero revenue does not raise ZeroDivisionError and yields 0.0 margin."""
    df_zero = pd.DataFrame([{
        "month": "2025-10",
        "store_id": "ST-ZERO",
        "store_name": "Zero Store",
        "city": "Delhi",
        "tier": "Tier 1",
        "store_format": "Standard",
        "revenue": 0.0,
        "rent": 500000.0,
        "payroll": 300000.0,
        "marketing": 100000.0,
        "utilities": 50000.0,
        "other_expenses": 20000.0,
    }])
    
    res = compute_store_pnl_metrics(df_zero)
    assert not res.empty
    row = res.iloc[0]
    assert row["total_expenses"] == 970000.0
    assert row["operating_profit_proxy"] == -970000.0
    assert row["operating_margin_pct"] == 0.0
    assert not np.isnan(row["operating_margin_pct"])
    assert not np.isinf(row["operating_margin_pct"])


def test_negative_profit_contribution(base_sample_df):
    """Verify negative operating contribution is accurately identified."""
    res = compute_store_pnl_metrics(base_sample_df)
    st2_nov = res[(res["store_id"] == "ST-02") & (res["month"] == "2025-11")].iloc[0]
    # Revenue: 2,000,000. Expenses: 600k + 500k + 300k + 150k + 500k = 2,050,000
    assert st2_nov["total_expenses"] == 2050000.0
    assert st2_nov["operating_profit_proxy"] == -50000.0
    assert pytest.approx(st2_nov["operating_margin_pct"], 0.01) == -2.5


def test_compute_historical_variances(base_sample_df):
    """Verify Month-over-Month delta and percentage shifts."""
    res = compute_historical_variances(base_sample_df)
    
    st1_oct = res[(res["store_id"] == "ST-01") & (res["month"] == "2025-10")].iloc[0]
    st1_nov = res[(res["store_id"] == "ST-01") & (res["month"] == "2025-11")].iloc[0]
    
    # First month shift should be NaN
    assert pd.isna(st1_oct["revenue_prev"])
    assert pd.isna(st1_oct["revenue_mom_pct"])
    
    # Second month: Revenue went 5M -> 6M (+1M, +20%)
    assert st1_nov["revenue_prev"] == 5000000.0
    assert st1_nov["revenue_mom_abs"] == 1000000.0
    assert pytest.approx(st1_nov["revenue_mom_pct"], 0.01) == 20.0
    
    # Payroll went 800k -> 850k (+50k, +6.25%)
    assert st1_nov["payroll_mom_abs"] == 50000.0
    assert pytest.approx(st1_nov["payroll_mom_pct"], 0.01) == 6.25


def test_compute_peer_benchmarks(base_sample_df):
    """Verify peer tier median benchmarking and rankings."""
    res = compute_peer_benchmarks(base_sample_df)
    
    oct_rows = res[res["month"] == "2025-10"]
    assert "peer_median_margin_pct" in oct_rows.columns
    assert "store_profit_rank_in_month" in oct_rows.columns
    
    # In 2025-10: ST-01 profit is 2.5M, ST-02 profit is 1.4M
    # ST-01 should be rank 1, ST-02 rank 2
    st1 = oct_rows[oct_rows["store_id"] == "ST-01"].iloc[0]
    st2 = oct_rows[oct_rows["store_id"] == "ST-02"].iloc[0]
    assert st1["store_profit_rank_in_month"] == 1
    assert st2["store_profit_rank_in_month"] == 2


def test_get_executive_kpis_empty():
    """Verify empty dataframe handling in KPI calculations."""
    kpis = get_executive_kpis(pd.DataFrame())
    assert kpis["total_revenue"] == 0.0
    assert kpis["store_count"] == 0
    assert kpis["operating_margin_pct"] == 0.0
