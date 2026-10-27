"""
Visual styling and interactive Plotly charting components for StorePulse.
Applies a restrained, professional visual palette:
Warm neutral linen background, charcoal typography, muted sage accents, terracotta alert warnings.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.config import THEME_COLORS, EXPENSE_COLUMNS


def get_custom_css() -> str:
    """Inject custom executive styling for StorePulse."""
    return f"""
    <style>
    /* Global Container and Typography */
    .main .block-container {{
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1300px;
    }}
    
    h1, h2, h3, h4 {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: {THEME_COLORS['text_main']};
        font-weight: 600;
        letter-spacing: -0.02em;
    }}
    
    /* Header Container */
    .storepulse-header {{
        padding: 1.25rem 1.5rem;
        background: linear-gradient(135deg, #FAF7F2 0%, #F4EFE6 100%);
        border: 1px solid {THEME_COLORS['border']};
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }}
    
    .storepulse-title {{
        font-size: 1.85rem;
        font-weight: 700;
        color: {THEME_COLORS['text_main']};
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    
    .storepulse-tagline {{
        font-size: 0.95rem;
        color: {THEME_COLORS['text_muted']};
        margin-top: 0.35rem;
        margin-bottom: 0;
    }}
    
    /* Synthetic Data Disclosure Pill */
    .disclosure-banner {{
        background-color: #F8F5EE;
        border-left: 4px solid {THEME_COLORS['primary']};
        padding: 0.65rem 1rem;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #55585B;
        margin-bottom: 1.25rem;
    }}
    
    /* Executive Metric Card */
    .metric-card {{
        background: #FFFFFF;
        border: 1px solid {THEME_COLORS['border']};
        border-radius: 8px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .metric-card:hover {{
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }}
    .metric-label {{
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        color: {THEME_COLORS['text_muted']};
        margin-bottom: 0.35rem;
    }}
    .metric-value {{
        font-size: 1.65rem;
        font-weight: 700;
        color: {THEME_COLORS['text_main']};
        line-height: 1.2;
    }}
    .metric-subtext {{
        font-size: 0.8rem;
        margin-top: 0.35rem;
        color: {THEME_COLORS['text_muted']};
    }}
    
    /* Severity Badges */
    .badge {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    .badge-high {{
        background-color: #FBEBE8;
        color: {THEME_COLORS['danger']};
        border: 1px solid #F5C6BE;
    }}
    .badge-med {{
        background-color: #FDF4ED;
        color: {THEME_COLORS['warning']};
        border: 1px solid #F6D6BE;
    }}
    .badge-low {{
        background-color: #EFF3F6;
        color: {THEME_COLORS['info']};
        border: 1px solid #D5E1E8;
    }}
    .badge-profit {{
        background-color: #EBF3EE;
        color: {THEME_COLORS['success']};
        border: 1px solid #C4DCCF;
    }}
    .badge-loss {{
        background-color: #FBEBE8;
        color: {THEME_COLORS['danger']};
        border: 1px solid #F5C6BE;
    }}
    
    /* Anomaly Card */
    .anomaly-card {{
        background: #FFFFFF;
        border: 1px solid {THEME_COLORS['border']};
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.85rem;
    }}
    .anomaly-card-high {{
        border-left: 4px solid {THEME_COLORS['danger']};
    }}
    .anomaly-card-med {{
        border-left: 4px solid {THEME_COLORS['warning']};
    }}
    .anomaly-card-low {{
        border-left: 4px solid {THEME_COLORS['info']};
    }}
    </style>
    """


def format_inr_lakhs(val: float) -> str:
    """Format numeric INR value into Indian Lakhs (₹X.XX L) or Crores."""
    if pd.isna(val):
        return "₹0.00 L"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 10_000_000:
        return f"{sign}₹{abs_val / 10_000_000:.2f} Cr"
    return f"{sign}₹{abs_val / 100_000:.2f} L"


def render_metric_card(label: str, value: str, subtext: str = "", delta_color: str = "normal") -> str:
    """Return HTML string for an executive metric card."""
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-subtext">{subtext}</div>
    </div>
    """


def create_pnl_bridge_waterfall(row: pd.Series) -> go.Figure:
    """
    Render a clean Waterfall chart bridging Revenue to Store Operating Contribution Proxy.
    Shows 4-wall unit economics clearly.
    """
    rev = row.get("revenue", 0.0)
    rent = row.get("rent", 0.0)
    payroll = row.get("payroll", 0.0)
    mkt = row.get("marketing", 0.0)
    util = row.get("utilities", 0.0)
    other = row.get("other_expenses", 0.0)
    profit = row.get("operating_profit_proxy", 0.0)

    categories = [
        "Store Revenue",
        "Rent",
        "Payroll",
        "Marketing",
        "Utilities",
        "Other / Maint.",
        "Store Operating Contribution",
    ]
    
    measures = ["absolute", "relative", "relative", "relative", "relative", "relative", "total"]
    y_values = [rev, -rent, -payroll, -mkt, -util, -other, profit]
    text_values = [
        format_inr_lakhs(rev),
        f"-{format_inr_lakhs(rent)}",
        f"-{format_inr_lakhs(payroll)}",
        f"-{format_inr_lakhs(mkt)}",
        f"-{format_inr_lakhs(util)}",
        f"-{format_inr_lakhs(other)}",
        format_inr_lakhs(profit),
    ]

    fig = go.Figure(
        go.Waterfall(
            name="Store P&L Bridge",
            orientation="v",
            measure=measures,
            x=categories,
            textposition="outside",
            text=text_values,
            y=y_values,
            connector={"line": {"color": THEME_COLORS["border"], "width": 1.5}},
            increasing={"marker": {"color": THEME_COLORS["primary"]}},
            decreasing={"marker": {"color": THEME_COLORS["secondary"]}},
            totals={"marker": {"color": THEME_COLORS["success"] if profit >= 0 else THEME_COLORS["danger"]}},
        )
    )

    fig.update_layout(
        title=f"4-Wall Unit Economics Bridge: {row.get('store_name', '')} ({row.get('month', '')})",
        title_font={"size": 15, "color": THEME_COLORS["text_main"]},
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=50, b=30),
        yaxis=dict(
            title="Amount (INR)",
            showgrid=True,
            gridcolor="#F0EDE6",
            zeroline=True,
            zerolinecolor="#2B2D2F",
        ),
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color=THEME_COLORS["text_main"])),
        height=380,
    )
    return fig


def create_store_ranking_bar(df: pd.DataFrame, metric: str = "operating_profit_proxy") -> go.Figure:
    """
    Render horizontal bar chart ranking stores by chosen metric.
    """
    sorted_df = df.sort_values(by=metric, ascending=True).copy()
    
    is_margin = "margin" in metric or "ratio" in metric
    metric_label = (
        "Operating Margin (%)" if is_margin else "Store Operating Contribution (INR)"
    )

    colors = [
        THEME_COLORS["success"] if val >= 0 else THEME_COLORS["danger"]
        for val in sorted_df[metric]
    ]

    text_vals = (
        [f"{v:.1f}%" for v in sorted_df[metric]]
        if is_margin
        else [format_inr_lakhs(v) for v in sorted_df[metric]]
    )

    fig = go.Figure(
        go.Bar(
            y=sorted_df["store_name"],
            x=sorted_df[metric],
            orientation="h",
            marker_color=colors,
            text=text_vals,
            textposition="auto",
        )
    )

    fig.update_layout(
        title=f"Store Rankings by {metric_label}",
        title_font={"size": 14, "color": THEME_COLORS["text_main"]},
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=45, b=20),
        xaxis=dict(
            title=metric_label,
            showgrid=True,
            gridcolor="#F0EDE6",
            zeroline=True,
            zerolinecolor="#333333",
        ),
        yaxis=dict(autorange="reversed", showgrid=False),
        height=420,
    )
    return fig


def create_monthly_trend_chart(df: pd.DataFrame, store_id: Optional[str] = None) -> go.Figure:
    """
    Render multi-month Revenue and Operating Contribution Proxy trend.
    """
    if store_id:
        data = df[df["store_id"] == store_id].sort_values("month").copy()
        title = f"Monthly Performance Trend: {data['store_name'].iloc[0] if not data.empty else store_id}"
    else:
        # Aggregated network trend
        data = (
            df.groupby("month")[["revenue", "total_expenses", "operating_profit_proxy"]]
            .sum()
            .reset_index()
            .sort_values("month")
        )
        title = "Network-Wide Monthly Performance Trend"

    fig = go.Figure()

    # Revenue Bar
    fig.add_trace(
        go.Bar(
            x=data["month"],
            y=data["revenue"],
            name="Revenue",
            marker_color="#8EA89D",
            opacity=0.75,
        )
    )

    # Total Expenses Bar
    fig.add_trace(
        go.Bar(
            x=data["month"],
            y=data["total_expenses"],
            name="Total Direct Expenses",
            marker_color="#D5A086",
            opacity=0.8,
        )
    )

    # Operating Profit Line
    fig.add_trace(
        go.Scatter(
            x=data["month"],
            y=data["operating_profit_proxy"],
            name="Store Operating Contribution",
            mode="lines+markers",
            line=dict(color=THEME_COLORS["primary"], width=3),
            marker=dict(size=8, color=THEME_COLORS["primary"]),
        )
    )

    fig.update_layout(
        title=title,
        title_font={"size": 14, "color": THEME_COLORS["text_main"]},
        barmode="group",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=45, b=25),
        yaxis=dict(
            title="Amount (INR)",
            showgrid=True,
            gridcolor="#F0EDE6",
            zeroline=True,
        ),
        xaxis=dict(title="Month", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=360,
    )
    return fig


def create_expense_breakdown_pie(row: pd.Series) -> go.Figure:
    """
    Donut chart of expense structure for a store month.
    """
    labels = ["Rent", "Payroll", "Marketing", "Utilities", "Other Expenses"]
    values = [
        row.get("rent", 0.0),
        row.get("payroll", 0.0),
        row.get("marketing", 0.0),
        row.get("utilities", 0.0),
        row.get("other_expenses", 0.0),
    ]

    colors = ["#4A6E82", "#3E6B5C", "#D97746", "#8F5C7E", "#B8860B"]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.48,
            marker=dict(colors=colors),
            textinfo="label+percent",
            hoverinfo="label+value+percent",
        )
    )

    fig.update_layout(
        title=f"Expense Composition: {row.get('store_name', '')}",
        title_font={"size": 14, "color": THEME_COLORS["text_main"]},
        paper_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=45, b=10),
        showlegend=False,
        height=300,
    )
    return fig


def create_peer_scatter_plot(df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot comparing Revenue (x) vs Store Operating Margin % (y),
    sized by Total Expenses, colored by Store Format or Tier.
    """
    fig = px.scatter(
        df,
        x="revenue",
        y="operating_margin_pct",
        color="tier",
        size="total_expenses",
        hover_name="store_name",
        hover_data=["city", "store_format", "rent", "payroll"],
        color_discrete_map={"Tier 1": THEME_COLORS["primary"], "Tier 2": THEME_COLORS["secondary"]},
        title="Revenue vs Operating Margin % (Sized by Total Expenses)",
    )

    # Add zero-margin reference line
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color=THEME_COLORS["danger"],
        annotation_text="Breakeven (0% Margin)",
        annotation_position="bottom right",
    )

    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=45, b=25),
        xaxis=dict(title="Store Monthly Revenue (INR)", showgrid=True, gridcolor="#F0EDE6"),
        yaxis=dict(title="Store Operating Margin (%)", showgrid=True, gridcolor="#F0EDE6"),
        height=380,
    )
    return fig
