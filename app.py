import os
import sqlite3
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(page_title="BDM Inventory Intelligence", layout="wide")

# ---------------------------------------------------------------------------
# Auto-seed: create the database if it doesn't exist yet
# ---------------------------------------------------------------------------
DB_PATH = "data/bdm.db"

if not os.path.exists(DB_PATH):
    from data.seed import seed
    seed()

# ---------------------------------------------------------------------------
# Data loading — cached for the session
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM v_inventory_dashboard", conn)
    conn.close()
    return df

@st.cache_data
def load_purchase_orders():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM purchase_orders", conn)
    conn.close()
    return df

@st.cache_data
def load_distributors():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM distributors", conn)
    conn.close()
    return df

df = load_data()
po_df = load_purchase_orders()
dist_df = load_distributors()

# ---------------------------------------------------------------------------
# Sidebar — cascading geography filters (applied to both tabs)
# ---------------------------------------------------------------------------
st.sidebar.title("Geography")

critical = df[df["alert_level"] == "critical"].copy()

regions = ["All"] + sorted(critical["region"].dropna().unique().tolist())
region = st.sidebar.selectbox("Region", regions)
if region != "All":
    critical = critical[critical["region"] == region]

provinces = ["All"] + sorted(critical["province"].dropna().unique().tolist())
province = st.sidebar.selectbox("Province", provinces)
if province != "All":
    critical = critical[critical["province"] == province]

cities = ["All"] + sorted(critical["city"].dropna().unique().tolist())
city = st.sidebar.selectbox("City", cities)
if city != "All":
    critical = critical[critical["city"] == city]

site_names = ["All"] + sorted(critical["site_name"].dropna().unique().tolist())
site = st.sidebar.selectbox("Site", site_names)
if site != "All":
    critical = critical[critical["site_name"] == site]

critical = critical.sort_values("days_of_supply").reset_index(drop=True)

st.sidebar.divider()
st.sidebar.markdown("**Legend**")
st.sidebar.markdown("""
<style>
.leg-row { display:flex; align-items:flex-start; gap:8px; margin-bottom:10px; }
.leg-dot { width:11px; height:11px; border-radius:50%; flex-shrink:0; margin-top:3px; }
.leg-label { font-size:12px; font-weight:600; color:#E6E7E8; }
.leg-desc { font-size:11px; color:#9a9b9c; line-height:1.4; margin-top:1px; }
</style>
<div class="leg-row">
  <div class="leg-dot" style="background:#8B0C0C;"></div>
  <div><div class="leg-label">Critical + shortage</div>
  <div class="leg-desc">≤7 days supply with an active Health Canada shortage alert</div></div>
</div>
<div class="leg-row">
  <div class="leg-dot" style="background:#E96A10;"></div>
  <div><div class="leg-label">Critical</div>
  <div class="leg-desc">≤7 days supply, no current shortage — order needed</div></div>
</div>
<div class="leg-row">
  <div class="leg-dot" style="background:#7a6000;border:1px solid #a08000;"></div>
  <div><div class="leg-label">Concern</div>
  <div class="leg-desc">8–14 days supply — not yet critical, monitor closely</div></div>
</div>
<div class="leg-row">
  <div class="leg-dot" style="background:#2A2A2A;border:1px solid #555;"></div>
  <div><div class="leg-label">Untracked / N/A</div>
  <div class="leg-desc">Qty not tracked or negative — supply cannot be calculated</div></div>
</div>
<div class="leg-row">
  <div class="leg-dot" style="background:#3a3a3a;border:1px solid #666;"></div>
  <div><div class="leg-label">Healthy</div>
  <div class="leg-desc">&gt;14 days supply — no action needed</div></div>
</div>
""", unsafe_allow_html=True)

# Apply same selections to full dataset for Tab 2
full = df.copy()
if region != "All":
    full = full[full["region"] == region]
if province != "All":
    full = full[full["province"] == province]
if city != "All":
    full = full[full["city"] == city]
if site != "All":
    full = full[full["site_name"] == site]
full = full.sort_values(["alert_level", "days_of_supply"]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("BDM Inventory Intelligence")
st.caption("Drugs at ≤ 7 days of supply — snapshot 2026-11-11")

# ---------------------------------------------------------------------------
# Summary metric tiles (driven by filtered critical rows)
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Critical Items", len(critical))
col2.metric("Shortage Flags", int(critical["shortage_active"].sum()))
col3.metric("Sites Affected", critical["site_id"].nunique())
col4.metric("Provinces Affected", critical["province"].nunique())

st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2 = st.tabs(["Critical Alerts", "Full Inventory"])

# ---------------------------------------------------------------------------
# Tab 1 — Critical Alerts (with click-to-expand procurement detail)
# ---------------------------------------------------------------------------
with tab1:
    if critical.empty:
        st.info("No critical items match the current filters.")
    else:
        critical["Drug"] = critical.apply(
            lambda r: f"{r['generic_name']} [{r['shortage_tier']}]"
            if r["shortage_active"] == 1 else r["generic_name"],
            axis=1,
        )
        critical["Days of Supply"] = critical["days_of_supply"].map(
            lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
        )
        critical["Daily Usage"] = critical["avg_daily_usage_7d"].map(
            lambda x: f"{x:,.0f}"
        )
        critical["Weekly Usage"] = critical["avg_daily_usage_7d"].map(
            lambda x: f"{x * 7:,.0f}"
        )
        critical["Monthly Usage"] = critical["avg_daily_usage_30d"].map(
            lambda x: f"{x * 30:,.0f}"
        )

        display_df = critical[[
            "Drug", "site_name", "province", "display_qty",
            "Daily Usage", "Weekly Usage", "Monthly Usage",
            "Days of Supply",
        ]].rename(columns={
            "site_name": "Site",
            "province": "Province",
            "display_qty": "Qty on Hand",
        }).reset_index(drop=True)

        shortage_flags = critical["shortage_active"].tolist()

        def highlight_critical(row):
            color = "#8B0C0C" if shortage_flags[row.name] == 1 else "#E96A10C3"
            return [f"background-color: {color}" for _ in row]

        styled = display_df.style.apply(highlight_critical, axis=1)

        st.dataframe(styled, width="stretch", hide_index=True)

        if int(critical["shortage_active"].sum()) > 0:
            st.caption("Highlighted rows have an active drug shortage.")

        # ---------------------------------------------------------------
        # Procurement detail panel — driven by a selectbox
        # ---------------------------------------------------------------
        labels = [
            f"{row['Drug']} — {row['Site']}"
            for _, row in display_df.iterrows()
        ]
        choice = st.selectbox("View procurement history for:", ["— select a drug —"] + labels)

        if choice != "— select a drug —":
            idx = labels.index(choice)
            sel = critical.iloc[idx]
            drug_id = sel["drug_id"]
            site_id = sel["site_id"]

            orders = po_df[
                (po_df["drug_id"] == drug_id) & (po_df["site_id"] == site_id)
            ].merge(
                dist_df[["distributor_id", "distributor_name", "distributor_type"]],
                on="distributor_id",
                how="left",
            ).sort_values("order_date", ascending=False)

            st.divider()
            st.subheader(f"Procurement — {sel['generic_name']} @ {sel['site_name']}")

            delivered = orders[orders["status"] == "delivered"]
            avg_lead = delivered["lead_time_days"].mean() if len(delivered) > 0 else 0
            avg_cost = delivered["unit_cost"].mean() if len(delivered) > 0 else 0
            total_orders = len(orders)

            m1, m2, m3 = st.columns(3)
            m1.metric("Avg Lead Time (delivered)", f"{avg_lead:.1f} days")
            m2.metric("Avg Unit Cost (delivered)", f"${avg_cost:.4f}")
            m3.metric("Orders (6 months)", total_orders)

            recent = orders.head(5)[[
                "order_date", "distributor_name", "quantity_ordered",
                "unit_cost", "lead_time_days", "status",
            ]].rename(columns={
                "order_date":       "Order Date",
                "distributor_name": "Distributor",
                "quantity_ordered": "Qty Ordered",
                "unit_cost":        "Unit Cost ($)",
                "lead_time_days":   "Lead (days)",
                "status":           "Status",
            })
            st.dataframe(recent, hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# Tab 2 — Full Inventory
# ---------------------------------------------------------------------------
with tab2:
    if full.empty:
        st.info("No items match the current filters.")
    else:
        full["Drug"] = full.apply(
            lambda r: f"{r['generic_name']} [{r['shortage_tier']}]"
            if r["shortage_active"] == 1 else r["generic_name"],
            axis=1,
        )
        full["Days of Supply"] = full["days_of_supply"].map(
            lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
        )
        full["Daily Usage"] = full["avg_daily_usage_7d"].map(
            lambda x: f"{x:,.0f}"
        )
        full["Weekly Usage"] = full["avg_daily_usage_7d"].map(
            lambda x: f"{x * 7:,.0f}"
        )
        full["Monthly Usage"] = full["avg_daily_usage_30d"].map(
            lambda x: f"{x * 30:,.0f}"
        )

        display_full = full[[
            "Drug", "site_name", "city", "province", "display_qty",
            "Daily Usage", "Weekly Usage", "Monthly Usage",
            "Days of Supply", "alert_level",
        ]].rename(columns={
            "site_name":   "Site",
            "city":        "City",
            "province":    "Province",
            "display_qty": "Qty on Hand",
            "alert_level": "Alert",
        }).reset_index(drop=True)

        alert_levels = full["alert_level"].tolist()
        shortage_flags_full = full["shortage_active"].tolist()

        def highlight_full(row):
            level = alert_levels[row.name]
            shortage = shortage_flags_full[row.name]
            if level == "critical" and shortage == 1:
                color = "#8B0C0C"
            elif level == "critical":
                color = "#E96A10C3"
            elif level == "concern":
                color = "#4A3800"
            elif level == "untracked":
                color = "#2A2A2A"
            else:
                color = ""
            return [f"background-color: {color}" if color else "" for _ in row]

        styled_full = display_full.style.apply(highlight_full, axis=1)
        st.dataframe(styled_full, width="stretch", hide_index=True)

