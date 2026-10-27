"""
StorePulse Configuration and Business Rules
Retail P&L Intelligence Engine for Multi-Store Showrooms.
"""

# Mandatory Synthetic Data Disclosure
DATA_DISCLOSURE_BANNER = (
    "SYNTHETIC DATASET NOTICE: All financial and operational figures displayed in StorePulse "
    "are purely synthetic and algorithmically simulated for demonstration purposes. "
    "This dataset does NOT represent real financial data of Wakefit Innovations Pvt. Ltd. "
    "or any specific retail entity."
)

APP_TITLE = "StorePulse | Retail P&L Intelligence Agent"
APP_SUBTITLE = "Store-Level Operating Contribution & Unit Economics Diagnostics"

# Expected P&L Dataset Columns
REQUIRED_COLUMNS = [
    "month",
    "store_id",
    "store_name",
    "city",
    "tier",
    "store_format",
    "revenue",
    "rent",
    "payroll",
    "marketing",
    "utilities",
    "other_expenses",
]

EXPENSE_COLUMNS = [
    "rent",
    "payroll",
    "marketing",
    "utilities",
    "other_expenses",
]

# Business Metrics & Accounting Disclaimers
ACCOUNTING_NOTE = (
    "Accounting Terminology Note: 'Store Operating Profit Proxy' (Store Contribution Margin) "
    "reflects direct 4-wall store cash generation: Revenue minus direct store-level operating expenses "
    "(Rent, Payroll, Local Marketing, Utilities, Store Maintenance/Other). It excludes central corporate overhead, "
    "supply chain COGS, and centralized depreciation/amortization."
)

# Anomaly Detection Rules & Configurable Default Thresholds
DEFAULT_ALERT_THRESHOLDS = {
    # 1. MoM Expense Surge: trigger if any expense category grows by > threshold and absolute change > min_abs
    "mom_expense_growth_pct": 35.0,  # 35% growth
    "mom_expense_min_abs_inr": 75_000,  # Min absolute jump ₹75,000

    # 2. Material Revenue Decline: trigger if store revenue drops by > threshold MoM
    "revenue_drop_pct": 20.0,  # 20% decline

    # 3. Store Operating Margin Deterioration: trigger if margin drops by > threshold percentage points
    "margin_deterioration_pp": 8.0,  # 8 percentage points compression

    # 4. Negative Store Operating Contribution: store operating cash loss
    "negative_margin_trigger": 0.0,

    # 5. Expense to Revenue Ratio Peer Outlier: trigger if expense category ratio > peer median * multiplier
    "peer_ratio_outlier_mult": 1.5,  # 50% higher than peer tier median
}

# Severity Classification
SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"

# Theme Colors (Warm neutral, Charcoal typography, Muted Sage, Terracotta)
THEME_COLORS = {
    "primary": "#3E6B5C",         # Muted Sage
    "secondary": "#D97746",       # Terracotta warning / alert
    "neutral_bg": "#FBF9F5",      # Warm linen neutral
    "card_bg": "#FFFFFF",         # Card background
    "border": "#E5E1D8",          # Warm subtle border
    "text_main": "#2B2D2F",       # Charcoal typography
    "text_muted": "#6E7174",      # Subdued slate
    "success": "#2D7251",         # Forest green
    "danger": "#BA3C2A",          # Terracotta deep red
    "warning": "#D97746",         # Terracotta amber
    "info": "#4A6E82",            # Muted slate blue
}
