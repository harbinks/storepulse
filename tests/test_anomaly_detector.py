"""
Unit tests for StorePulse rule-based anomaly detection engine.
Verifies threshold boundary conditions, explainable baselines, and detection of seeded anomalies.
"""

import pytest
import pandas as pd
from src.anomaly_detector import detect_anomalies
from src.data_loader import load_dataset_from_source, get_default_sample_path


def test_detect_anomalies_empty_df():
    """Verify empty input returns empty structured DataFrame without raising exceptions."""
    alerts = detect_anomalies(pd.DataFrame())
    assert isinstance(alerts, pd.DataFrame)
    assert len(alerts) == 0
    assert "alert_id" in alerts.columns
    assert "rule_name" in alerts.columns


def test_mom_expense_surge_trigger():
    """Verify that an expense surge exceeding percentage and absolute thresholds triggers an alert."""
    df = pd.DataFrame([
        {
            "month": "2025-10",
            "store_id": "ST-01",
            "store_name": "Store 1",
            "city": "Bangalore",
            "tier": "Tier 1",
            "store_format": "Flagship",
            "revenue": 5000000.0,
            "rent": 1000000.0,
            "payroll": 500000.0,
            "marketing": 300000.0,
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
            "revenue": 5000000.0,
            "rent": 1000000.0,
            "payroll": 500000.0,
            "marketing": 300000.0,
            "utilities": 450000.0,  # +125% jump, +250k (exceeds 35% & 75k)
            "other_expenses": 100000.0,
        },
    ])
    
    alerts = detect_anomalies(df)
    util_alerts = alerts[alerts["category"] == "Utilities"]
    assert len(util_alerts) == 1
    a = util_alerts.iloc[0]
    assert a["rule_name"] == "MoM Expense Surge"
    assert a["baseline_value"] == 200000.0
    assert a["current_value"] == 450000.0
    assert a["absolute_variance"] == 250000.0
    assert pytest.approx(a["percentage_variance"], 0.01) == 125.0
    assert a["severity"] == "High"


def test_threshold_boundary_expense_surge():
    """Verify that an expense increase below the minimum threshold does NOT trigger."""
    df = pd.DataFrame([
        {
            "month": "2025-10",
            "store_id": "ST-01",
            "store_name": "Store 1",
            "city": "Bangalore",
            "tier": "Tier 1",
            "store_format": "Flagship",
            "revenue": 5000000.0,
            "rent": 1000000.0,
            "payroll": 500000.0,
            "marketing": 300000.0,
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
            "revenue": 5000000.0,
            "rent": 1000000.0,
            "payroll": 500000.0,
            "marketing": 300000.0,
            "utilities": 240000.0,  # +20% jump, +40k (below 35% and below 75k)
            "other_expenses": 100000.0,
        },
    ])
    alerts = detect_anomalies(df)
    util_alerts = alerts[alerts["category"] == "Utilities"]
    assert len(util_alerts) == 0


def test_revenue_decline_and_negative_contribution():
    """Verify material revenue decline and negative contribution alerts trigger correctly."""
    df = pd.DataFrame([
        {
            "month": "2025-10",
            "store_id": "ST-08",
            "store_name": "Store 8",
            "city": "Hyderabad",
            "tier": "Tier 1",
            "store_format": "Experience Studio",
            "revenue": 4000000.0,
            "rent": 1000000.0,
            "payroll": 800000.0,
            "marketing": 300000.0,
            "utilities": 200000.0,
            "other_expenses": 100000.0,
        },
        {
            "month": "2025-11",
            "store_id": "ST-08",
            "store_name": "Store 8",
            "city": "Hyderabad",
            "tier": "Tier 1",
            "store_format": "Experience Studio",
            "revenue": 2200000.0,  # -45% MoM decline (Total exp = 2.4M > rev 2.2M => negative profit)
            "rent": 1000000.0,
            "payroll": 800000.0,
            "marketing": 300000.0,
            "utilities": 200000.0,
            "other_expenses": 100000.0,
        },
    ])
    alerts = detect_anomalies(df)
    
    rev_alerts = alerts[alerts["rule_name"] == "Material Revenue Decline"]
    assert len(rev_alerts) == 1
    assert pytest.approx(rev_alerts.iloc[0]["percentage_variance"], 0.01) == -45.0
    
    loss_alerts = alerts[alerts["rule_name"] == "Negative Store Contribution"]
    assert len(loss_alerts) == 1
    assert loss_alerts.iloc[0]["current_value"] == -200000.0


def test_sample_dataset_seeded_anomalies_detected():
    """Verify that all intentionally seeded anomalies in sample_store_pnl.csv are caught."""
    path = get_default_sample_path()
    df, _, _ = load_dataset_from_source(path)
    alerts = detect_anomalies(df)
    
    assert len(alerts) >= 5
    
    # 1. Check ST-04 (Utilities surge in 2026-02)
    st04_util = alerts[(alerts["store_id"] == "ST-04") & (alerts["category"] == "Utilities")]
    assert len(st04_util) > 0
    
    # 2. Check ST-06 (Marketing surge in 2026-01)
    st06_mkt = alerts[(alerts["store_id"] == "ST-06") & (alerts["category"] == "Marketing")]
    assert len(st06_mkt) > 0
    
    # 3. Check ST-08 (Revenue decline in 2026-03)
    st08_rev = alerts[(alerts["store_id"] == "ST-08") & (alerts["category"] == "Revenue")]
    assert len(st08_rev) > 0
    
    # 4. Check ST-03 (Payroll surge in 2025-12)
    st03_pay = alerts[(alerts["store_id"] == "ST-03") & (alerts["category"] == "Payroll")]
    assert len(st03_pay) > 0
    
    # 5. Check ST-10 (Other expenses spike in 2025-11)
    st10_oth = alerts[(alerts["store_id"] == "ST-10") & (alerts["category"] == "Other Expenses")]
    assert len(st10_oth) > 0
