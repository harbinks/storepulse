"""
Operational Action Tracker and CSV Export Engine for StorePulse.
Manages issue ownership, resolution workflows, and audit exports with explicit session disclosure.
"""

from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Dict, Any, Optional
import pandas as pd

SESSION_PERSISTENCE_NOTICE = (
    "SESSION PERSISTENCE NOTICE: Action items and workflow status modifications are maintained "
    "in your active browser session state only. They are not persisted to a permanent database server. "
    "Please download the Action Tracker CSV export before navigating away or resetting the session."
)

STATUS_OPTIONS = ["Open", "In Review", "In Progress", "Resolved"]

DEFAULT_OWNER_MAP = {
    "Utilities": "National Facilities & Energy Manager",
    "Marketing": "Regional Retail Marketing Lead",
    "Payroll": "Retail People Operations (HRBP)",
    "Rent": "Corporate Real Estate & Lease Admin",
    "Other Expenses": "Store Maintenance & Facilities Lead",
    "Revenue": "Area Retail Operations Manager",
    "Operating Margin": "Retail Strategy & Commercial Finance MT",
    "Operating Contribution": "Head of Retail Operations",
}


def generate_initial_actions_from_alerts(alerts_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Generate initial structured action tracker records from detected anomalies.
    Assigns sensible MT/Ops owners, default target due dates, and suggested next steps.
    """
    if alerts_df is None or alerts_df.empty:
        return []

    actions: List[Dict[str, Any]] = []
    base_date = datetime(2026, 4, 5)

    for i, (_, row) in enumerate(alerts_df.iterrows(), start=1):
        cat_key = row.get("category", "General")
        for key in DEFAULT_OWNER_MAP:
            if key.lower() in cat_key.lower():
                owner = DEFAULT_OWNER_MAP[key]
                break
        else:
            owner = "Retail Operations Management Trainee"

        # High severity gets 5 days, Medium gets 12 days
        days_ahead = 5 if row.get("severity") == "High" else 12
        due_date = (base_date + timedelta(days=days_ahead + (i % 7))).strftime("%Y-%m-%d")

        actions.append({
            "action_id": f"ACT-{i:03d}",
            "alert_id": row.get("alert_id", ""),
            "month": row.get("month", ""),
            "store_id": row.get("store_id", ""),
            "store_name": row.get("store_name", ""),
            "category": row.get("category", ""),
            "severity": row.get("severity", "Medium"),
            "issue": row.get("explanation", ""),
            "suggested_next_step": row.get("recommended_investigation", ""),
            "owner": owner,
            "due_date": due_date,
            "status": "Open",
            "notes": "System-generated based on automated P&L variance rule trigger.",
        })

    return actions


def export_dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Safely serialize DataFrame to UTF-8 encoded CSV bytes for Streamlit download."""
    if df is None or df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")


def export_actions_to_csv_bytes(actions: List[Dict[str, Any]]) -> bytes:
    """Serialize action items list to CSV bytes."""
    if not actions:
        return b""
    df = pd.DataFrame(actions)
    return export_dataframe_to_csv_bytes(df)
