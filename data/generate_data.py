"""
Deterministic synthetic P&L dataset generator for StorePulse.
Generates 12 fictional retail stores across 6 months with realistic seasonality
and precisely documented intentional anomalies.
"""

import os
import pandas as pd
import numpy as np

MONTHS = [
    "2025-10",  # Festive kick-off (Dussehra/Diwali)
    "2025-11",  # Peak festive demand
    "2025-12",  # Year-end clearance & winter gifting
    "2026-01",  # Post-festive slump / winter season
    "2026-02",  # Normal retail run-rate
    "2026-03",  # Fiscal year-end campaigns
]

# Baseline store definitions
STORES = [
    {
        "store_id": "ST-01",
        "store_name": "Bangalore - Indiranagar Flagship",
        "city": "Bangalore",
        "tier": "Tier 1",
        "store_format": "Flagship",
        "base_rev": 5200000,
        "base_rent": 750000,
        "base_payroll": 550000,
        "base_mkt": 350000,
        "base_util": 210000,
        "base_other": 160000,
    },
    {
        "store_id": "ST-02",
        "store_name": "Bangalore - HSR Layout Studio",
        "city": "Bangalore",
        "tier": "Tier 1",
        "store_format": "Experience Studio",
        "base_rev": 3800000,
        "base_rent": 520000,
        "base_payroll": 420000,
        "base_mkt": 280000,
        "base_util": 160000,
        "base_other": 120000,
    },
    {
        "store_id": "ST-03",
        "store_name": "Bangalore - Whitefield Hub",
        "city": "Bangalore",
        "tier": "Tier 1",
        "store_format": "Standard",
        "base_rev": 4200000,
        "base_rent": 600000,
        "base_payroll": 420000,
        "base_mkt": 300000,
        "base_util": 170000,
        "base_other": 130000,
    },
    {
        "store_id": "ST-04",
        "store_name": "Mumbai - Andheri West Center",
        "city": "Mumbai",
        "tier": "Tier 1",
        "store_format": "Flagship",
        "base_rev": 5600000,
        "base_rent": 980000,
        "base_payroll": 580000,
        "base_mkt": 400000,
        "base_util": 185000,
        "base_other": 180000,
    },
    {
        "store_id": "ST-05",
        "store_name": "Mumbai - Thane Viviana",
        "city": "Mumbai",
        "tier": "Tier 1",
        "store_format": "Standard",
        "base_rev": 3600000,
        "base_rent": 540000,
        "base_payroll": 380000,
        "base_mkt": 250000,
        "base_util": 140000,
        "base_other": 110000,
    },
    {
        "store_id": "ST-06",
        "store_name": "Delhi NCR - Gurgaon Sector 29",
        "city": "Delhi NCR",
        "tier": "Tier 1",
        "store_format": "Flagship",
        "base_rev": 4800000,
        "base_rent": 720000,
        "base_payroll": 500000,
        "base_mkt": 250000,
        "base_util": 200000,
        "base_other": 150000,
    },
    {
        "store_id": "ST-07",
        "store_name": "Delhi NCR - Noida Sector 18",
        "city": "Delhi NCR",
        "tier": "Tier 1",
        "store_format": "Standard",
        "base_rev": 3500000,
        "base_rent": 500000,
        "base_payroll": 370000,
        "base_mkt": 240000,
        "base_util": 150000,
        "base_other": 110000,
    },
    {
        "store_id": "ST-08",
        "store_name": "Hyderabad - Gachibowli Tech Corridor",
        "city": "Hyderabad",
        "tier": "Tier 1",
        "store_format": "Experience Studio",
        "base_rev": 4300000,
        "base_rent": 580000,
        "base_payroll": 430000,
        "base_mkt": 290000,
        "base_util": 170000,
        "base_other": 130000,
    },
    {
        "store_id": "ST-09",
        "store_name": "Hyderabad - Banjara Hills",
        "city": "Hyderabad",
        "tier": "Tier 1",
        "store_format": "Flagship",
        "base_rev": 4600000,
        "base_rent": 690000,
        "base_payroll": 480000,
        "base_mkt": 320000,
        "base_util": 190000,
        "base_other": 140000,
    },
    {
        "store_id": "ST-10",
        "store_name": "Pune - Koregaon Park",
        "city": "Pune",
        "tier": "Tier 2",
        "store_format": "Experience Studio",
        "base_rev": 3200000,
        "base_rent": 420000,
        "base_payroll": 320000,
        "base_mkt": 210000,
        "base_util": 130000,
        "base_other": 110000,
    },
    {
        "store_id": "ST-11",
        "store_name": "Chennai - Anna Nagar",
        "city": "Chennai",
        "tier": "Tier 1",
        "store_format": "Standard",
        "base_rev": 3900000,
        "base_rent": 550000,
        "base_payroll": 390000,
        "base_mkt": 260000,
        "base_util": 160000,
        "base_other": 120000,
    },
    {
        "store_id": "ST-12",
        "store_name": "Lucknow - Gomti Nagar",
        "city": "Lucknow",
        "tier": "Tier 2",
        "store_format": "Standard",
        "base_rev": 2800000,
        "base_rent": 320000,
        "base_payroll": 270000,
        "base_mkt": 180000,
        "base_util": 100000,
        "base_other": 80000,
    },
]

# Month seasonality multipliers for top-line revenue
SEASONALITY = {
    "2025-10": 1.15,  # Festive surge
    "2025-11": 1.25,  # Peak festive
    "2025-12": 1.10,  # Year end
    "2026-01": 0.88,  # Post holiday drop
    "2026-02": 0.95,  # Baseline recovery
    "2026-03": 1.08,  # Fiscal year close push
}


def generate_synthetic_pnl_dataset(seed: int = 42) -> pd.DataFrame:
    """Generate deterministic synthetic P&L records with intentional anomalies."""
    np.random.seed(seed)
    rows = []

    for month in MONTHS:
        s_mult = SEASONALITY[month]

        for s in STORES:
            sid = s["store_id"]

            # Minor deterministic variations (+/- 2.5%) for non-anomalous noise
            noise_rev = 1.0 + ((hash(f"{sid}_{month}_rev") % 100) - 50) / 2000.0
            noise_payroll = 1.0 + ((hash(f"{sid}_{month}_pay") % 100) - 50) / 3000.0
            noise_util = 1.0 + ((hash(f"{sid}_{month}_util") % 100) - 50) / 2500.0
            noise_mkt = 1.0 + ((hash(f"{sid}_{month}_mkt") % 100) - 50) / 2500.0
            noise_oth = 1.0 + ((hash(f"{sid}_{month}_oth") % 100) - 50) / 2500.0

            rev = round(s["base_rev"] * s_mult * noise_rev, -2)
            rent = float(s["base_rent"])  # Fixed contractual rent
            payroll = round(s["base_payroll"] * noise_payroll, -2)
            marketing = round(s["base_mkt"] * (0.9 + 0.15 * s_mult) * noise_mkt, -2)
            utilities = round(s["base_util"] * noise_util, -2)
            other = round(s["base_other"] * noise_oth, -2)

            # --- SEEDED INTENTIONAL ANOMALIES ---

            # Anomaly 1: ST-04 (Mumbai Andheri) Utilities Surge in Feb & Mar 2026
            # Cause: HVAC central chiller compressor failure & running commercial backup DG continuously
            if sid == "ST-04" and month == "2026-02":
                utilities = 445000.0  # +140% jump from ~₹1.85L baseline
            elif sid == "ST-04" and month == "2026-03":
                utilities = 432000.0

            # Anomaly 2: ST-06 (Gurgaon Sec 29) Unproductive Marketing Surge in Jan 2026
            # Cause: Heavy local uncoordinated agency spend during winter footfall slump
            if sid == "ST-06" and month == "2026-01":
                marketing = 525000.0  # +110% jump from ~₹2.5L
                rev = round(rev * 0.85, -2)  # Additional revenue drop

            # Anomaly 3: ST-08 (Hyderabad Gachibowli) Revenue Collapse in Mar 2026
            # Cause: Severe flyover / metro construction barricades closing showroom access
            if sid == "ST-08" and month == "2026-03":
                rev = 2480000.0  # -42% MoM decline from ~₹43L

            # Anomaly 4: ST-03 (Bangalore Whitefield) Payroll Spike in Dec 2025
            # Cause: Excessive unapproved holiday seasonal overtime and contract sales staffing
            if sid == "ST-03" and month == "2025-12":
                payroll = 695000.0  # +65% jump from ~₹4.2L

            # Anomaly 5: ST-10 (Pune Koregaon) Other Expenses Surge in Nov 2025
            # Cause: Burst underground pipe causing showroom water damage remediation
            if sid == "ST-10" and month == "2025-11":
                other = 335000.0  # +204% jump from ~₹1.1L

            # Anomaly 6: ST-05 (Mumbai Thane) Contractual Rent Dispute in Jan 2026
            # Cause: Disputed retrospective property tax escalation passed on by mall management
            if sid == "ST-05" and month == "2026-01":
                rent = 729000.0  # +35% jump from ₹5.4L

            rows.append({
                "month": month,
                "store_id": sid,
                "store_name": s["store_name"],
                "city": s["city"],
                "tier": s["tier"],
                "store_format": s["store_format"],
                "revenue": float(rev),
                "rent": float(rent),
                "payroll": float(payroll),
                "marketing": float(marketing),
                "utilities": float(utilities),
                "other_expenses": float(other),
            })

    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "sample_store_pnl.csv")
    df = generate_synthetic_pnl_dataset()
    df.to_csv(out_file, index=False)
    print(f"Generated {len(df)} records ({len(STORES)} stores x {len(MONTHS)} months) -> {out_file}")
