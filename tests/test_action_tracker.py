"""
Unit tests for StorePulse Action Tracker and CSV Exporter.
Verifies action generation, owner mapping, session exports, and empty handling.
"""

import pytest
import pandas as pd
from src.action_tracker import (
    generate_initial_actions_from_alerts,
    export_dataframe_to_csv_bytes,
    export_actions_to_csv_bytes,
)


def test_generate_initial_actions_from_alerts():
    """Verify conversion from anomaly alerts to operational action items."""
    alerts_df = pd.DataFrame([
        {
            "alert_id": "ALT-001",
            "month": "2026-02",
            "store_id": "ST-04",
            "store_name": "Mumbai Andheri",
            "category": "Utilities",
            "severity": "High",
            "explanation": "Utilities surged +140%",
            "recommended_investigation": "Check energy logbooks and DG meter slips.",
        },
        {
            "alert_id": "ALT-002",
            "month": "2026-01",
            "store_id": "ST-06",
            "store_name": "Gurgaon Sec 29",
            "category": "Marketing",
            "severity": "Medium",
            "explanation": "Marketing surged +110%",
            "recommended_investigation": "Audit local marketing spend.",
        },
    ])
    
    actions = generate_initial_actions_from_alerts(alerts_df)
    assert len(actions) == 2
    assert actions[0]["action_id"] == "ACT-001"
    assert actions[0]["status"] == "Open"
    assert "Facilities" in actions[0]["owner"]
    assert "Marketing" in actions[1]["owner"]


def test_export_actions_to_csv_bytes():
    """Verify CSV export serialization produces valid UTF-8 CSV content."""
    actions = [
        {
            "action_id": "ACT-001",
            "store_name": "Indiranagar Flagship",
            "category": "Rent",
            "status": "In Progress",
            "owner": "Real Estate Head",
            "due_date": "2026-04-15",
        }
    ]
    csv_bytes = export_actions_to_csv_bytes(actions)
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0
    text = csv_bytes.decode("utf-8")
    assert "Indiranagar Flagship" in text
    assert "In Progress" in text


def test_export_dataframe_to_csv_bytes_empty():
    """Verify empty DataFrame export yields empty bytes safely."""
    res = export_dataframe_to_csv_bytes(pd.DataFrame())
    assert res == b""
