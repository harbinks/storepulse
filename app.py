"""
StorePulse: Retail P&L Intelligence Agent
Recruiter-ready Streamlit application demonstrating store-level unit economics,
explainable anomaly detection, executive KPI dashboards, and operational action tracking.
Designed for a Wakefit Management Trainee (Retail Operations & Strategy) portfolio.
"""

import os
import streamlit as st
import pandas as pd
import numpy as np

from src.config import (
    APP_TITLE,
    APP_SUBTITLE,
    DATA_DISCLOSURE_BANNER,
    ACCOUNTING_NOTE,
    DEFAULT_ALERT_THRESHOLDS,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    EXPENSE_COLUMNS,
)
from src.data_loader import (
    get_default_sample_path,
    load_dataset_from_source,
    validate_schema,
)
from src.financial_engine import (
    compute_store_pnl_metrics,
    compute_historical_variances,
    compute_peer_benchmarks,
    get_executive_kpis,
)
from src.anomaly_detector import detect_anomalies
from src.action_tracker import (
    generate_initial_actions_from_alerts,
    export_dataframe_to_csv_bytes,
    export_actions_to_csv_bytes,
    SESSION_PERSISTENCE_NOTICE,
    STATUS_OPTIONS,
)
from src.visual_components import (
    get_custom_css,
    format_inr_lakhs,
    render_metric_card,
    create_pnl_bridge_waterfall,
    create_store_ranking_bar,
    create_monthly_trend_chart,
    create_expense_breakdown_pie,
    create_peer_scatter_plot,
)

# -----------------------------------------------------------------------------
# Streamlit Page Config & Custom Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="StorePulse | Retail P&L Intelligence",
    page_icon="🏬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_custom_css(), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "data_source" not in st.session_state:
    st.session_state.data_source = "demo"

if "actions_list" not in st.session_state:
    st.session_state.actions_list = []

if "anomalies_cache" not in st.session_state:
    st.session_state.anomalies_cache = None


# -----------------------------------------------------------------------------
# Sidebar: Data Source, Configuration & Filters
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏬 StorePulse Engine")
    st.caption("Retail P&L Intelligence • Wakefit MT Portfolio")
    
    st.markdown("---")
    st.markdown("#### 📂 Dataset Controls")
    
    source_choice = st.radio(
        "Select Data Source:",
        ["Demo Dataset (12 Stores, 6 Mo)", "Upload Custom CSV"],
        index=0 if st.session_state.data_source == "demo" else 1,
    )

    uploaded_file = None
    if source_choice == "Upload Custom CSV":
        st.session_state.data_source = "upload"
        uploaded_file = st.file_uploader(
            "Upload monthly store P&L CSV",
            type=["csv"],
            help="Must include month, store_id, store_name, city, tier, store_format, revenue, rent, payroll, marketing, utilities, other_expenses",
        )
    else:
        st.session_state.data_source = "demo"

    if st.button("🔄 Reset to Default Demo Data", use_container_width=True):
        st.session_state.data_source = "demo"
        st.session_state.actions_list = []
        st.session_state.anomalies_cache = None
        st.rerun()

    st.markdown("---")
    st.markdown("#### ⚙️ Anomaly Rule Thresholds")
    with st.expander("Configure Thresholds", expanded=False):
        t_expense_growth = st.slider(
            "MoM Expense Surge (%)",
            min_value=15.0,
            max_value=100.0,
            value=float(DEFAULT_ALERT_THRESHOLDS["mom_expense_growth_pct"]),
            step=5.0,
        )
        t_min_abs_jump = st.number_input(
            "Min Absolute Expense Jump (₹)",
            min_value=10_000,
            max_value=500_000,
            value=int(DEFAULT_ALERT_THRESHOLDS["mom_expense_min_abs_inr"]),
            step=10_000,
        )
        t_rev_drop = st.slider(
            "Revenue Decline Threshold (%)",
            min_value=10.0,
            max_value=60.0,
            value=float(DEFAULT_ALERT_THRESHOLDS["revenue_drop_pct"]),
            step=5.0,
        )
        t_margin_drop = st.slider(
            "Margin Compression (pp)",
            min_value=3.0,
            max_value=25.0,
            value=float(DEFAULT_ALERT_THRESHOLDS["margin_deterioration_pp"]),
            step=1.0,
        )

    current_thresholds = {
        "mom_expense_growth_pct": t_expense_growth,
        "mom_expense_min_abs_inr": t_min_abs_jump,
        "revenue_drop_pct": t_rev_drop,
        "margin_deterioration_pp": t_margin_drop,
        "negative_margin_trigger": 0.0,
        "peer_ratio_outlier_mult": 1.5,
    }


# -----------------------------------------------------------------------------
# Data Ingestion & Sanitization
# -----------------------------------------------------------------------------
if st.session_state.data_source == "upload" and uploaded_file is not None:
    df_raw, load_warnings, load_errors = load_dataset_from_source(uploaded_file)
else:
    sample_path = get_default_sample_path()
    df_raw, load_warnings, load_errors = load_dataset_from_source(sample_path)

if load_errors:
    st.error(f"❌ Data Validation Error: {'; '.join(load_errors)}")
    st.stop()

if load_warnings:
    with st.sidebar:
        with st.expander(f"⚠️ Data Notices ({len(load_warnings)})", expanded=False):
            for w in load_warnings:
                st.caption(f"• {w}")

# Precompute benchmarked dataset and anomalies
df_benchmarked = compute_peer_benchmarks(df_raw)
anomalies_df = detect_anomalies(df_raw, current_thresholds)

# Sync action tracker if empty
if not st.session_state.actions_list and not anomalies_df.empty:
    st.session_state.actions_list = generate_initial_actions_from_alerts(anomalies_df)


# -----------------------------------------------------------------------------
# Sidebar Filters: Scope & Slice
# -----------------------------------------------------------------------------
available_months = sorted(df_benchmarked["month"].unique().tolist())
available_tiers = ["All Tiers"] + sorted(df_benchmarked["tier"].unique().tolist())
available_formats = ["All Formats"] + sorted(df_benchmarked["store_format"].unique().tolist())
available_stores = ["All Stores"] + sorted(df_benchmarked["store_name"].unique().tolist())

with st.sidebar:
    st.markdown("#### 🎯 Scope & Slice")
    selected_month = st.selectbox("Fiscal Month:", ["All Months (Aggregate)"] + available_months, index=len(available_months))
    selected_tier = st.selectbox("Store Tier:", available_tiers, index=0)
    selected_format = st.selectbox("Store Format:", available_formats, index=0)
    selected_store_name = st.selectbox("Store Filter:", available_stores, index=0)

    st.markdown("---")
    st.caption("Built with Streamlit, Pandas & Plotly.")


# -----------------------------------------------------------------------------
# Filter Application
# -----------------------------------------------------------------------------
filtered_df = df_benchmarked.copy()

if selected_month != "All Months (Aggregate)":
    filtered_df = filtered_df[filtered_df["month"] == selected_month]

if selected_tier != "All Tiers":
    filtered_df = filtered_df[filtered_df["tier"] == selected_tier]

if selected_format != "All Formats":
    filtered_df = filtered_df[filtered_df["store_format"] == selected_format]

if selected_store_name != "All Stores":
    filtered_df = filtered_df[filtered_df["store_name"] == selected_store_name]


# -----------------------------------------------------------------------------
# Header & Compliance Banners
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="storepulse-header">
        <h1 class="storepulse-title">🏬 {APP_TITLE}</h1>
        <p class="storepulse-tagline">{APP_SUBTITLE}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Mandatory Synthetic Data Notice Banner
st.markdown(
    f"""
    <div class="disclosure-banner">
        <strong>⚠️ Synthetic Data Disclosure:</strong> {DATA_DISCLOSURE_BANNER}
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Executive Tabs
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Executive P&L Dashboard",
    "🚨 Anomaly Intelligence",
    "🔍 Store Deep-Dive & Unit Economics",
    "📋 Operational Action Tracker",
    "📖 Methodology & Architecture",
])


# =============================================================================
# TAB 1: EXECUTIVE P&L DASHBOARD
# =============================================================================
with tab1:
    # 1. Executive Top-Level Metric Cards
    m_month = selected_month if selected_month != "All Months (Aggregate)" else None
    kpis = get_executive_kpis(filtered_df, selected_month=None)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(
            render_metric_card(
                "Total Revenue",
                format_inr_lakhs(kpis["total_revenue"]),
                f"{kpis['store_count']} Stores Active",
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            render_metric_card(
                "Direct Store Expenses",
                format_inr_lakhs(kpis["total_expenses"]),
                f"{(kpis['total_expenses']/kpis['total_revenue']*100):.1f}% of Revenue" if kpis["total_revenue"] > 0 else "0%",
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            render_metric_card(
                "Store Operating Profit",
                format_inr_lakhs(kpis["operating_profit"]),
                "4-Wall Cash Contribution",
            ),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            render_metric_card(
                "Blended Operating Margin",
                f"{kpis['operating_margin_pct']:.1f}%",
                "Operating Contribution / Rev",
            ),
            unsafe_allow_html=True,
        )
    with col5:
        high_anomalies = len(anomalies_df[anomalies_df["severity"] == SEVERITY_HIGH])
        total_anomalies = len(anomalies_df)
        st.markdown(
            render_metric_card(
                "Flagged Anomalies",
                f"{total_anomalies}",
                f"{high_anomalies} High Priority Alert(s)",
            ),
            unsafe_allow_html=True,
        )

    st.caption(f"💡 {ACCOUNTING_NOTE}")
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Charts Row
    c_left, c_right = st.columns([6, 5])
    with c_left:
        # If single month selected, show rankings; else show monthly trend
        if selected_month != "All Months (Aggregate)":
            fig_rank = create_store_ranking_bar(filtered_df, metric="operating_profit_proxy")
            st.plotly_chart(fig_rank, use_container_width=True)
        else:
            fig_trend = create_monthly_trend_chart(filtered_df)
            st.plotly_chart(fig_trend, use_container_width=True)

    with c_right:
        fig_scatter = create_peer_scatter_plot(filtered_df)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # 3. Store Performance Summary Table
    st.markdown("#### 📋 Store Performance Scorecard")
    display_cols = [
        "month",
        "store_id",
        "store_name",
        "city",
        "tier",
        "revenue",
        "total_expenses",
        "operating_profit_proxy",
        "operating_margin_pct",
    ]
    if "store_profit_rank_in_month" in filtered_df.columns:
        display_cols.append("store_profit_rank_in_month")

    table_data = filtered_df[display_cols].copy()
    table_data["Revenue (₹ Lakhs)"] = table_data["revenue"] / 100_000
    table_data["Direct Expenses (₹ Lakhs)"] = table_data["total_expenses"] / 100_000
    table_data["Operating Contribution (₹ Lakhs)"] = table_data["operating_profit_proxy"] / 100_000
    table_data["Margin %"] = table_data["operating_margin_pct"].round(1)

    cols_to_show = [
        "month",
        "store_id",
        "store_name",
        "city",
        "tier",
        "Revenue (₹ Lakhs)",
        "Direct Expenses (₹ Lakhs)",
        "Operating Contribution (₹ Lakhs)",
        "Margin %",
    ]

    st.dataframe(
        table_data[cols_to_show].sort_values(by=["month", "Operating Contribution (₹ Lakhs)"], ascending=[False, False]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue (₹ Lakhs)": st.column_config.NumberColumn(format="₹%.2f L"),
            "Direct Expenses (₹ Lakhs)": st.column_config.NumberColumn(format="₹%.2f L"),
            "Operating Contribution (₹ Lakhs)": st.column_config.NumberColumn(format="₹%.2f L"),
            "Margin %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )


# =============================================================================
# TAB 2: ANOMALY INTELLIGENCE
# =============================================================================
with tab2:
    st.markdown("### 🚨 Rule-Based Anomaly Intelligence Engine")
    st.markdown(
        "Deterministic, explainable audit flags generated using strict mathematical rules. "
        "Each alert exposes its exact baseline, current observed value, variance, and the triggering rule."
    )

    # Filter anomalies based on page selection
    active_anomalies = anomalies_df.copy()
    if selected_month != "All Months (Aggregate)":
        active_anomalies = active_anomalies[active_anomalies["month"] == selected_month]
    if selected_store_name != "All Stores":
        active_anomalies = active_anomalies[active_anomalies["store_name"] == selected_store_name]

    # Metrics row for alerts
    a_col1, a_col2, a_col3, a_col4 = st.columns(4)
    with a_col1:
        st.metric("Total Alerts Triggered", len(active_anomalies))
    with a_col2:
        st.metric("🔴 High Severity", len(active_anomalies[active_anomalies["severity"] == SEVERITY_HIGH]))
    with a_col3:
        st.metric("🟠 Medium Severity", len(active_anomalies[active_anomalies["severity"] == SEVERITY_MEDIUM]))
    with a_col4:
        st.metric("Active Rule Count", 5)

    st.markdown("---")

    # Severity Filter & Export Row
    f_col1, f_col2, f_col3 = st.columns([4, 4, 3])
    with f_col1:
        sev_filter = st.multiselect(
            "Filter by Severity:",
            [SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW],
            default=[SEVERITY_HIGH, SEVERITY_MEDIUM],
        )
    with f_col2:
        cat_filter = st.multiselect(
            "Filter by Category:",
            sorted(active_anomalies["category"].unique().tolist()) if not active_anomalies.empty else [],
            default=[],
        )
    with f_col3:
        st.write("")
        st.write("")
        csv_anomalies_bytes = export_dataframe_to_csv_bytes(active_anomalies)
        st.download_button(
            "📥 Export Anomalies to CSV",
            data=csv_anomalies_bytes,
            file_name="storepulse_pnl_anomalies.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Apply local filters
    if sev_filter:
        active_anomalies = active_anomalies[active_anomalies["severity"].isin(sev_filter)]
    if cat_filter:
        active_anomalies = active_anomalies[active_anomalies["category"].isin(cat_filter)]

    if active_anomalies.empty:
        st.info("✅ No anomalies detected for the current filter criteria.")
    else:
        for _, alert in active_anomalies.iterrows():
            sev = alert["severity"]
            sev_class = "anomaly-card-high" if sev == SEVERITY_HIGH else "anomaly-card-med"
            badge_class = "badge-high" if sev == SEVERITY_HIGH else "badge-med"

            is_pp = "Margin" in alert["category"]
            var_format = f"{alert['absolute_variance']:+.1f} pp" if is_pp else format_inr_lakhs(alert['absolute_variance'])

            st.markdown(
                f"""
                <div class="anomaly-card {sev_class}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                        <span style="font-weight: 700; font-size: 1.05rem; color: #2B2D2F;">
                            {alert['store_name']} ({alert['store_id']}) • {alert['month']}
                        </span>
                        <span>
                            <span class="badge {badge_class}">{sev} Severity</span>
                            <span class="badge" style="background: #FAF7F2; border: 1px solid #E5E1D8; color: #555;">{alert['category']}</span>
                        </span>
                    </div>
                    <div style="font-size: 0.9rem; color: #3E4144; margin-bottom: 0.5rem;">
                        <strong>Triggered Rule:</strong> {alert['rule_name']} &nbsp;|&nbsp;
                        <strong>Baseline:</strong> {format_inr_lakhs(alert['baseline_value']) if not is_pp else f"{alert['baseline_value']:.1f}%"} &nbsp;|&nbsp;
                        <strong>Current:</strong> {format_inr_lakhs(alert['current_value']) if not is_pp else f"{alert['current_value']:.1f}%"} &nbsp;|&nbsp;
                        <strong>Variance:</strong> {var_format} ({alert['percentage_variance']:+.1f}%)
                    </div>
                    <div style="font-size: 0.88rem; color: #2B2D2F; background: #F8F6F2; padding: 0.6rem 0.8rem; border-radius: 4px; margin-bottom: 0.4rem;">
                        <strong>Factual Finding:</strong> {alert['explanation']}
                    </div>
                    <div style="font-size: 0.85rem; color: #3E6B5C;">
                        <strong>Suggested Investigation:</strong> {alert['recommended_investigation']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# =============================================================================
# TAB 3: STORE DEEP-DIVE & UNIT ECONOMICS
# =============================================================================
with tab3:
    st.markdown("### 🔍 Store Deep-Dive & Unit Economics Diagnostics")
    
    # Store selector
    all_store_names = sorted(df_benchmarked["store_name"].unique().tolist())
    target_store = st.selectbox("Select Store for Deep-Dive Analysis:", all_store_names, index=0)
    store_records = df_benchmarked[df_benchmarked["store_name"] == target_store].sort_values("month")

    if not store_records.empty:
        # Store profile banner
        latest_record = store_records.iloc[-1]
        s_sid = latest_record["store_id"]
        s_city = latest_record["city"]
        s_tier = latest_record["tier"]
        s_format = latest_record["store_format"]
        avg_rev = store_records["revenue"].mean()
        avg_margin = store_records["operating_margin_pct"].mean()

        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        with p_col1:
            st.markdown(render_metric_card("Store ID & Format", f"{s_sid}", f"{s_format} • {s_tier}"), unsafe_allow_html=True)
        with p_col2:
            st.markdown(render_metric_card("City & Market", f"{s_city}", "Omnichannel Hub"), unsafe_allow_html=True)
        with p_col3:
            st.markdown(render_metric_card("6-Mo Average Revenue", format_inr_lakhs(avg_rev), "Monthly Run-Rate"), unsafe_allow_html=True)
        with p_col4:
            st.markdown(render_metric_card("6-Mo Average Margin", f"{avg_margin:.1f}%", "Operating Contribution"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Month selector for Waterfall
        m_choices = store_records["month"].tolist()
        inspect_month = st.selectbox("Select Month for 4-Wall P&L Bridge:", m_choices, index=len(m_choices)-1)
        month_row = store_records[store_records["month"] == inspect_month].iloc[0]

        d_col1, d_col2 = st.columns([7, 5])
        with d_col1:
            fig_bridge = create_pnl_bridge_waterfall(month_row)
            st.plotly_chart(fig_bridge, use_container_width=True)
        with d_col2:
            fig_donut = create_expense_breakdown_pie(month_row)
            st.plotly_chart(fig_donut, use_container_width=True)

        # Historical Trend for this specific store
        st.markdown("#### 📈 Multi-Month Performance Trend")
        fig_store_trend = create_monthly_trend_chart(df_benchmarked, store_id=s_sid)
        st.plotly_chart(fig_store_trend, use_container_width=True)

        # MoM Variance Ledger
        st.markdown("#### 📜 Historical Month-over-Month Variance Ledger")
        ledger_cols = [
            "month",
            "revenue",
            "revenue_mom_pct",
            "rent",
            "payroll",
            "marketing",
            "utilities",
            "other_expenses",
            "operating_profit_proxy",
            "operating_margin_pct",
            "operating_margin_mom_pp",
        ]
        ledger_df = store_records[ledger_cols].copy()
        ledger_df["Revenue (₹L)"] = (ledger_df["revenue"] / 100_000).round(2)
        ledger_df["Rev MoM %"] = ledger_df["revenue_mom_pct"].round(1)
        ledger_df["Rent (₹L)"] = (ledger_df["rent"] / 100_000).round(2)
        ledger_df["Payroll (₹L)"] = (ledger_df["payroll"] / 100_000).round(2)
        ledger_df["Marketing (₹L)"] = (ledger_df["marketing"] / 100_000).round(2)
        ledger_df["Utilities (₹L)"] = (ledger_df["utilities"] / 100_000).round(2)
        ledger_df["Other (₹L)"] = (ledger_df["other_expenses"] / 100_000).round(2)
        ledger_df["Store Contrib (₹L)"] = (ledger_df["operating_profit_proxy"] / 100_000).round(2)
        ledger_df["Margin %"] = ledger_df["operating_margin_pct"].round(1)
        ledger_df["Margin Shift (pp)"] = ledger_df["operating_margin_mom_pp"].round(1)

        display_ledger = ledger_df[
            [
                "month",
                "Revenue (₹L)",
                "Rev MoM %",
                "Rent (₹L)",
                "Payroll (₹L)",
                "Marketing (₹L)",
                "Utilities (₹L)",
                "Other (₹L)",
                "Store Contrib (₹L)",
                "Margin %",
                "Margin Shift (pp)",
            ]
        ]
        st.dataframe(display_ledger, use_container_width=True, hide_index=True)


# =============================================================================
# TAB 4: OPERATIONAL ACTION TRACKER
# =============================================================================
with tab4:
    st.markdown("### 📋 Operational Action Tracker")
    st.markdown(
        "Structured resolution workflows for cross-functional retail leadership. "
        "Assign owners, set target completion dates, and track resolution lifecycle."
    )

    # Session persistence notice
    st.info(f"ℹ️ {SESSION_PERSISTENCE_NOTICE}")

    # Action Items Status Metrics
    if st.session_state.actions_list:
        act_df = pd.DataFrame(st.session_state.actions_list)
        open_count = len(act_df[act_df["status"] == "Open"])
        review_count = len(act_df[act_df["status"] == "In Review"])
        progress_count = len(act_df[act_df["status"] == "In Progress"])
        resolved_count = len(act_df[act_df["status"] == "Resolved"])

        st_c1, st_c2, st_c3, st_c4 = st.columns(4)
        with st_c1:
            st.metric("Open Actions", open_count)
        with st_c2:
            st.metric("In Review", review_count)
        with st_c3:
            st.metric("In Progress", progress_count)
        with st_c4:
            st.metric("Resolved", resolved_count)

        st.markdown("---")

        # Interactive Data Editor for Actions
        st.markdown("#### ✏️ Update & Manage Action Items")
        editable_cols = ["action_id", "store_name", "category", "severity", "owner", "due_date", "status", "suggested_next_step"]
        
        # We display the dataframe with st.data_editor
        edited_df = st.data_editor(
            act_df[editable_cols],
            use_container_width=True,
            column_config={
                "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS, required=True),
                "owner": st.column_config.TextColumn("Assigned Owner", required=True),
                "due_date": st.column_config.TextColumn("Target Due Date (YYYY-MM-DD)", required=True),
                "suggested_next_step": st.column_config.TextColumn("Operational Resolution Step", width="large"),
            },
            disabled=["action_id", "store_name", "category", "severity"],
            key="action_editor",
        )

        # Save updates back to session_state
        if edited_df is not None:
            # Preserve non-displayed fields
            updated_records = []
            for _, r in edited_df.iterrows():
                orig = next((item for item in st.session_state.actions_list if item["action_id"] == r["action_id"]), {})
                orig.update(r.to_dict())
                updated_records.append(orig)
            st.session_state.actions_list = updated_records

        # Export Button
        export_bytes = export_actions_to_csv_bytes(st.session_state.actions_list)
        st.download_button(
            "📥 Download Action Plan (CSV)",
            data=export_bytes,
            file_name="storepulse_action_tracker.csv",
            mime="text/csv",
            use_container_width=False,
        )

    else:
        st.info("No action items available. Reset demo data or adjust anomaly thresholds to generate actions.")

    # Form to add a new custom action item
    with st.expander("➕ Add Custom Store Action Item", expanded=False):
        with st.form("new_action_form"):
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                new_store = st.selectbox("Target Store:", sorted(df_benchmarked["store_name"].unique().tolist()))
                new_cat = st.selectbox("Category:", ["Utilities", "Payroll", "Marketing", "Rent", "Other Expenses", "Revenue", "General Operations"])
                new_owner = st.text_input("Assigned Owner:", value="Retail Operations Management Trainee")
            with c_f2:
                new_sev = st.selectbox("Severity:", [SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW])
                new_due = st.date_input("Target Due Date:").strftime("%Y-%m-%d")
                new_status = st.selectbox("Status:", STATUS_OPTIONS)

            new_issue = st.text_area("Issue Description:")
            new_step = st.text_area("Suggested Next Operational Step:")

            submit_action = st.form_submit_button("Create Action Item")
            if submit_action:
                new_id = f"ACT-{(len(st.session_state.actions_list) + 1):03d}"
                st.session_state.actions_list.append({
                    "action_id": new_id,
                    "alert_id": "CUSTOM-ENTRY",
                    "month": selected_month if selected_month != "All Months (Aggregate)" else "2026-03",
                    "store_id": "MANUAL",
                    "store_name": new_store,
                    "category": new_cat,
                    "severity": new_sev,
                    "issue": new_issue,
                    "suggested_next_step": new_step,
                    "owner": new_owner,
                    "due_date": new_due,
                    "status": new_status,
                    "notes": "Manually logged by user.",
                })
                st.success(f"Created action item {new_id} successfully!")
                st.rerun()


# =============================================================================
# TAB 5: METHODOLOGY & ARCHITECTURE
# =============================================================================
with tab5:
    st.markdown("### 📖 StorePulse Methodology, Financial Formulas & Architecture")
    st.markdown(
        """
        StorePulse is built as a **decision-support copilot for retail leadership**, specifically tailored for
        omnichannel showroom networks like Wakefit.
        """
    )

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.markdown("#### 📐 Mathematical & Accounting Framework")
        st.markdown(
            r"""
            1. **Total Store Operating Expenses ($E_{store}$)**:
               $$E_{store} = \text{Rent} + \text{Payroll} + \text{Marketing} + \text{Utilities} + \text{Other}$$

            2. **Store Operating Profit Proxy ($P_{store}$)**:
               $$P_{store} = \text{Revenue} - E_{store}$$
               *Represents 4-wall store cash generation before corporate overhead, COGS, and centralized financing.*

            3. **Operating Margin Percentage ($M_{store}$)**:
               $$M_{store} = \left(\frac{P_{store}}{\text{Revenue}}\right) \times 100\%$$

            4. **Month-over-Month Expense Surge ($\Delta_{MoM}\%$)**:
               $$\Delta_{MoM}\% = \left(\frac{E_{t} - E_{t-1}}{|E_{t-1}|}\right) \times 100\%$$

            5. **Margin Compression in Percentage Points ($\Delta_{pp}$)**:
               $$\Delta_{pp} = M_{t} - M_{t-1}$$
            """
        )

    with m_col2:
        st.markdown("#### 🎯 Explainable Anomaly Detection Rules")
        st.markdown(
            """
            - **MoM Expense Surge**: Triggers if category growth exceeds threshold (default: >35%) AND absolute increase > ₹75,000.
            - **Material Revenue Decline**: Triggers if store monthly revenue drops by >20% MoM.
            - **Margin Deterioration**: Triggers if operating contribution margin compresses by >8 percentage points MoM.
            - **Negative Store Contribution**: Triggers if 4-wall store expenses exceed revenue ($P_{store} < 0$).
            - **Expense-Ratio Peer Outlier**: Triggers if store category-to-revenue ratio exceeds $1.5\times$ the median of comparable stores in the same tier.
            """
        )

    st.markdown("---")
    st.markdown("#### 🛡️ Compliance & Synthetic Data Disclaimer")
    st.caption(DATA_DISCLOSURE_BANNER)
    st.caption(ACCOUNTING_NOTE)
