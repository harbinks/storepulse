"""
Financial calculations and variance engine for StorePulse.
Computes Store Operating Contribution Proxy, expense ratios, MoM variances,
and peer tier benchmarks without misleading corporate accounting terminology.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from src.config import EXPENSE_COLUMNS


def compute_store_pnl_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate store-level 4-wall unit economics:
    - total_expenses
    - operating_profit_proxy (Store Contribution Proxy)
    - operating_margin_pct
    - expense-to-revenue ratios for each category
    Safely handles zero or negative revenue.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    res = df.copy()

    # Ensure numeric columns
    for col in ["revenue"] + EXPENSE_COLUMNS:
        if col in res.columns:
            res[col] = pd.to_numeric(res[col], errors="coerce").fillna(0.0)

    # 1. Total Store Operating Expenses
    res["total_expenses"] = res[EXPENSE_COLUMNS].sum(axis=1)

    # 2. Store Operating Profit Proxy (4-Wall Contribution)
    res["operating_profit_proxy"] = res["revenue"] - res["total_expenses"]

    # 3. Operating Margin % (Safely computed when revenue > 0)
    res["operating_margin_pct"] = np.where(
        res["revenue"] > 0,
        (res["operating_profit_proxy"] / res["revenue"]) * 100.0,
        0.0,
    )

    # 4. Expense category ratios (% of revenue)
    for col in EXPENSE_COLUMNS:
        ratio_col = f"{col}_ratio_pct"
        res[ratio_col] = np.where(
            res["revenue"] > 0,
            (res[col] / res["revenue"]) * 100.0,
            0.0,
        )

    res["total_expense_ratio_pct"] = np.where(
        res["revenue"] > 0,
        (res["total_expenses"] / res["revenue"]) * 100.0,
        0.0,
    )

    return res


def compute_historical_variances(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute sequential Month-over-Month (MoM) variances per store:
    - Absolute and percentage differences for revenue, each expense category,
      total expenses, and operating contribution.
    - Percentage point (pp) shift for margins.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    base = compute_store_pnl_metrics(df)
    base = base.sort_values(by=["store_id", "month"]).reset_index(drop=True)

    metrics_to_diff = ["revenue", "total_expenses", "operating_profit_proxy"] + EXPENSE_COLUMNS

    # Group by store to calculate sequential shifts
    grouped = base.groupby("store_id")

    for m in metrics_to_diff:
        base[f"{m}_prev"] = grouped[m].shift(1)
        base[f"{m}_mom_abs"] = base[m] - base[f"{m}_prev"]
        # Safe percentage change: avoid division by zero or NaN
        prev_val = base[f"{m}_prev"]
        base[f"{m}_mom_pct"] = np.where(
            (prev_val.notna()) & (prev_val != 0),
            ((base[m] - prev_val) / prev_val.abs()) * 100.0,
            np.nan,
        )

    # Margin percentage points change
    base["operating_margin_prev"] = grouped["operating_margin_pct"].shift(1)
    base["operating_margin_mom_pp"] = np.where(
        base["operating_margin_prev"].notna(),
        base["operating_margin_pct"] - base["operating_margin_prev"],
        np.nan,
    )

    return base


def compute_peer_benchmarks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute peer benchmarks across stores within the same month and tier:
    - Tier median margin
    - Tier median expense ratios
    - Store rank by Operating Profit Proxy within month
    - Delta vs peer tier median margin
    """
    if df is None or df.empty:
        return pd.DataFrame()

    data = compute_historical_variances(df)

    # Group by month and tier for granular like-for-like peer grouping
    group_cols = ["month", "tier"]

    # Compute tier medians
    agg_dict = {
        "operating_margin_pct": "median",
        "total_expense_ratio_pct": "median",
        "revenue": "median",
    }
    for col in EXPENSE_COLUMNS:
        agg_dict[f"{col}_ratio_pct"] = "median"

    peer_medians = (
        data.groupby(group_cols)[list(agg_dict.keys())]
        .median()
        .reset_index()
        .rename(
            columns={
                "operating_margin_pct": "peer_median_margin_pct",
                "total_expense_ratio_pct": "peer_median_expense_ratio_pct",
                "revenue": "peer_median_revenue",
                **{f"{c}_ratio_pct": f"peer_median_{c}_ratio_pct" for c in EXPENSE_COLUMNS},
            }
        )
    )

    # Merge peer metrics back
    merged = pd.merge(data, peer_medians, on=group_cols, how="left")

    # Margin delta vs peer median
    merged["margin_delta_vs_peer_pp"] = (
        merged["operating_margin_pct"] - merged["peer_median_margin_pct"]
    )

    # Store rank within the month (1 = highest operating profit proxy)
    merged["store_profit_rank_in_month"] = (
        merged.groupby("month")["operating_profit_proxy"]
        .rank(ascending=False, method="min")
        .astype(int)
    )

    # Store rank by revenue within the month
    merged["store_revenue_rank_in_month"] = (
        merged.groupby("month")["revenue"]
        .rank(ascending=False, method="min")
        .astype(int)
    )

    return merged


def get_executive_kpis(df: pd.DataFrame, selected_month: Optional[str] = None) -> Dict[str, Any]:
    """
    Compute aggregate network-level portfolio KPIs:
    - Total Network Revenue
    - Total Network Expenses
    - Network Operating Contribution Proxy
    - Network Operating Margin %
    - Number of Active Stores
    - Count of Profit-Positive vs Loss-Making Stores
    """
    if df is None or df.empty:
        return {
            "total_revenue": 0.0,
            "total_expenses": 0.0,
            "operating_profit": 0.0,
            "operating_margin_pct": 0.0,
            "store_count": 0,
            "profitable_stores": 0,
            "unprofitable_stores": 0,
        }

    subset = df.copy()
    if selected_month:
        subset = subset[subset["month"] == selected_month]

    metrics = compute_store_pnl_metrics(subset)

    tot_rev = float(metrics["revenue"].sum())
    tot_exp = float(metrics["total_expenses"].sum())
    op_profit = tot_rev - tot_exp
    margin_pct = (op_profit / tot_rev * 100.0) if tot_rev > 0 else 0.0
    store_count = int(metrics["store_id"].nunique())
    profitable = int((metrics["operating_profit_proxy"] >= 0).sum())
    unprofitable = int((metrics["operating_profit_proxy"] < 0).sum())

    return {
        "total_revenue": tot_rev,
        "total_expenses": tot_exp,
        "operating_profit": op_profit,
        "operating_margin_pct": margin_pct,
        "store_count": store_count,
        "profitable_stores": profitable,
        "unprofitable_stores": unprofitable,
    }
