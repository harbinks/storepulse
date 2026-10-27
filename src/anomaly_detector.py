"""
Explainable, Rule-Based Anomaly Detection Engine for StorePulse.
Flags expense surges, revenue declines, margin deterioration, and peer ratio outliers
with strict factual baselines, deltas, and zero hallucinated root causes.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from src.config import (
    DEFAULT_ALERT_THRESHOLDS,
    EXPENSE_COLUMNS,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)
from src.financial_engine import compute_peer_benchmarks


def detect_anomalies(
    df: pd.DataFrame,
    thresholds: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Run deterministic, explainable rule checks on store financial records.
    Returns a DataFrame of structured anomaly alerts with:
    - alert_id
    - month
    - store_id
    - store_name
    - tier
    - category
    - rule_name
    - severity
    - baseline_value
    - current_value
    - absolute_variance
    - percentage_variance
    - explanation
    - recommended_investigation
    """
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "alert_id",
                "month",
                "store_id",
                "store_name",
                "tier",
                "category",
                "rule_name",
                "severity",
                "baseline_value",
                "current_value",
                "absolute_variance",
                "percentage_variance",
                "explanation",
                "recommended_investigation",
            ]
        )

    # Use default thresholds if not specified
    cfg = DEFAULT_ALERT_THRESHOLDS.copy()
    if thresholds:
        cfg.update(thresholds)

    # Ensure financial metrics, MoM shifts, and peer benchmarks are calculated
    data = compute_peer_benchmarks(df)

    alerts: List[Dict[str, Any]] = []

    for idx, row in data.iterrows():
        sid = row["store_id"]
        sname = row["store_name"]
        m = row["month"]
        tier = row["tier"]

        # -------------------------------------------------------------
        # Rule 1: MoM Expense Surge (Evaluated per expense category)
        # -------------------------------------------------------------
        for cat in EXPENSE_COLUMNS:
            prev_val = row.get(f"{cat}_prev")
            curr_val = row.get(cat)
            mom_pct = row.get(f"{cat}_mom_pct")
            mom_abs = row.get(f"{cat}_mom_abs")

            if pd.notna(mom_pct) and pd.notna(mom_abs):
                if mom_pct >= cfg["mom_expense_growth_pct"] and mom_abs >= cfg["mom_expense_min_abs_inr"]:
                    severity = (
                        SEVERITY_HIGH
                        if (mom_pct >= 60.0 or mom_abs >= 150_000)
                        else SEVERITY_MEDIUM
                    )
                    cat_title = cat.replace("_", " ").title()
                    alert_id = f"ALT-{sid}-{m}-{cat[:4].upper()}-SURGE"
                    alerts.append({
                        "alert_id": alert_id,
                        "month": m,
                        "store_id": sid,
                        "store_name": sname,
                        "tier": tier,
                        "category": cat_title,
                        "rule_name": "MoM Expense Surge",
                        "severity": severity,
                        "baseline_value": float(prev_val),
                        "current_value": float(curr_val),
                        "absolute_variance": float(mom_abs),
                        "percentage_variance": float(mom_pct),
                        "explanation": (
                            f"{cat_title} increased by ₹{mom_abs:,.0f} (+{mom_pct:.1f}% MoM), "
                            f"exceeding threshold (+{cfg['mom_expense_growth_pct']:.1f}% & ₹{cfg['mom_expense_min_abs_inr']:,.0f}). "
                            f"Prior month baseline: ₹{prev_val:,.0f}, Current: ₹{curr_val:,.0f}."
                        ),
                        "recommended_investigation": (
                            f"Request {cat_title} general ledger ledger entries and vendor invoices for {m}. "
                            f"Cross-reference approval authorisations with regional operations head."
                        ),
                    })

        # -------------------------------------------------------------
        # Rule 2: Material Revenue Decline
        # -------------------------------------------------------------
        rev_prev = row.get("revenue_prev")
        rev_curr = row.get("revenue")
        rev_mom_pct = row.get("revenue_mom_pct")
        rev_mom_abs = row.get("revenue_mom_abs")

        if pd.notna(rev_mom_pct) and pd.notna(rev_mom_abs):
            # Check if revenue dropped beyond threshold percentage
            if rev_mom_pct <= -abs(cfg["revenue_drop_pct"]):
                severity = SEVERITY_HIGH if rev_mom_pct <= -30.0 else SEVERITY_MEDIUM
                alert_id = f"ALT-{sid}-{m}-REV-DECLINE"
                alerts.append({
                    "alert_id": alert_id,
                    "month": m,
                    "store_id": sid,
                    "store_name": sname,
                    "tier": tier,
                    "category": "Revenue",
                    "rule_name": "Material Revenue Decline",
                    "severity": severity,
                    "baseline_value": float(rev_prev),
                    "current_value": float(rev_curr),
                    "absolute_variance": float(rev_mom_abs),
                    "percentage_variance": float(rev_mom_pct),
                    "explanation": (
                        f"Store revenue declined by ₹{abs(rev_mom_abs):,.0f} ({rev_mom_pct:.1f}% MoM), "
                        f"breaching the -{cfg['revenue_drop_pct']:.1f}% decline threshold. "
                        f"Prior month baseline: ₹{rev_prev:,.0f}, Current: ₹{rev_curr:,.0f}."
                    ),
                    "recommended_investigation": (
                        f"Review daily footfall logs, average order value (AOV), conversion rates, and external "
                        f"factors (e.g. local road closures, competitor entry, localized logistics delays)."
                    ),
                })

        # -------------------------------------------------------------
        # Rule 3: Operating Margin Deterioration (MoM Compression)
        # -------------------------------------------------------------
        margin_prev = row.get("operating_margin_prev")
        margin_curr = row.get("operating_margin_pct")
        margin_pp = row.get("operating_margin_mom_pp")

        if pd.notna(margin_pp):
            if margin_pp <= -abs(cfg["margin_deterioration_pp"]):
                severity = SEVERITY_HIGH if margin_pp <= -12.0 else SEVERITY_MEDIUM
                alert_id = f"ALT-{sid}-{m}-MARGIN-DROP"
                alerts.append({
                    "alert_id": alert_id,
                    "month": m,
                    "store_id": sid,
                    "store_name": sname,
                    "tier": tier,
                    "category": "Operating Margin",
                    "rule_name": "Margin Deterioration",
                    "severity": severity,
                    "baseline_value": float(margin_prev),
                    "current_value": float(margin_curr),
                    "absolute_variance": float(margin_pp),  # in percentage points
                    "percentage_variance": float(
                        ((margin_curr - margin_prev) / abs(margin_prev) * 100.0)
                        if margin_prev != 0 else 0.0
                    ),
                    "explanation": (
                        f"Store Operating Margin compressed by {abs(margin_pp):.1f} percentage points MoM "
                        f"(from {margin_prev:.1f}% to {margin_curr:.1f}%), exceeding the {cfg['margin_deterioration_pp']:.1f} pp threshold."
                    ),
                    "recommended_investigation": (
                        f"Examine store 4-wall cost structure to isolate whether deterioration was driven by "
                        f"unplanned fixed expense inflation or top-line volume de-leveraging."
                    ),
                })

        # -------------------------------------------------------------
        # Rule 4: Negative Store Operating Contribution (Loss-Making)
        # -------------------------------------------------------------
        op_profit = row.get("operating_profit_proxy")
        if pd.notna(op_profit) and op_profit < cfg["negative_margin_trigger"]:
            alert_id = f"ALT-{sid}-{m}-NEGATIVE-CONTRIB"
            alerts.append({
                "alert_id": alert_id,
                "month": m,
                "store_id": sid,
                "store_name": sname,
                "tier": tier,
                "category": "Operating Contribution",
                "rule_name": "Negative Store Contribution",
                "severity": SEVERITY_HIGH,
                "baseline_value": 0.0,
                "current_value": float(op_profit),
                "absolute_variance": float(op_profit),
                "percentage_variance": float(row.get("operating_margin_pct", 0.0)),
                "explanation": (
                    f"Store incurred negative operating contribution of -₹{abs(op_profit):,.0f} "
                    f"(Operating margin: {row.get('operating_margin_pct', 0.0):.1f}%). 4-wall store expenses "
                    f"(₹{row.get('total_expenses', 0.0):,.0f}) exceeded revenue (₹{row.get('revenue', 0.0):,.0f})."
                ),
                "recommended_investigation": (
                    f"Schedule urgent store unit-economics review with Area Retail Manager. "
                    f"Evaluate immediate temporary cost reduction measures."
                ),
            })

        # -------------------------------------------------------------
        # Rule 5: Expense-Ratio Peer Outlier (vs Tier Peer Median)
        # -------------------------------------------------------------
        if row.get("revenue", 0) > 0:
            for cat in EXPENSE_COLUMNS:
                store_ratio = row.get(f"{cat}_ratio_pct")
                peer_ratio = row.get(f"peer_median_{cat}_ratio_pct")

                if pd.notna(store_ratio) and pd.notna(peer_ratio) and peer_ratio > 0:
                    mult = cfg["peer_ratio_outlier_mult"]
                    # If store ratio is > 1.5x peer median and at least 3 percentage points higher
                    if store_ratio >= (peer_ratio * mult) and (store_ratio - peer_ratio) >= 3.0:
                        cat_title = cat.replace("_", " ").title()
                        alert_id = f"ALT-{sid}-{m}-{cat[:4].upper()}-PEER-OUTLIER"
                        alerts.append({
                            "alert_id": alert_id,
                            "month": m,
                            "store_id": sid,
                            "store_name": sname,
                            "tier": tier,
                            "category": f"{cat_title} Ratio",
                            "rule_name": "Expense-Ratio Peer Outlier",
                            "severity": SEVERITY_MEDIUM,
                            "baseline_value": float(peer_ratio),
                            "current_value": float(store_ratio),
                            "absolute_variance": float(store_ratio - peer_ratio),
                            "percentage_variance": float(((store_ratio - peer_ratio) / peer_ratio) * 100.0),
                            "explanation": (
                                f"{cat_title} consumes {store_ratio:.1f}% of revenue vs peer {tier} median of "
                                f"{peer_ratio:.1f}% (+{store_ratio - peer_ratio:.1f} pp higher, {store_ratio / peer_ratio:.2f}x peer benchmark)."
                            ),
                            "recommended_investigation": (
                                f"Benchmark {cat_title} allocation against comparable {tier} stores to determine "
                                f"if showroom size or local contracting terms explain the disparity."
                            ),
                        })

    ALERT_COLUMNS = [
        "alert_id",
        "month",
        "store_id",
        "store_name",
        "tier",
        "category",
        "rule_name",
        "severity",
        "baseline_value",
        "current_value",
        "absolute_variance",
        "percentage_variance",
        "explanation",
        "recommended_investigation",
    ]

    if not alerts:
        return pd.DataFrame(columns=ALERT_COLUMNS)

    alerts_df = pd.DataFrame(alerts)
    # Sort by month desc, severity High first
    severity_order = {SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 1, SEVERITY_LOW: 2}
    alerts_df["sev_rank"] = alerts_df["severity"].map(severity_order)
    alerts_df = alerts_df.sort_values(by=["month", "sev_rank", "store_id"], ascending=[False, True, True])
    alerts_df = alerts_df.drop(columns=["sev_rank"]).reset_index(drop=True)

    return alerts_df
