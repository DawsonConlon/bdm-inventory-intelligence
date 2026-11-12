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
        critical["Daily Usage (7d)"] = critical["avg_daily_usage_7d"].map(
            lambda x: f"{x:,.0f}"
        )
        critical["Weekly Usage (7d)"] = critical["avg_daily_usage_7d"].map(
            lambda x: f"{x * 7:,.0f}"
        )
        critical["Monthly Usage (30d)"] = critical["avg_daily_usage_30d"].map(
            lambda x: f"{x * 30:,.0f}"
        )

        display_df = critical[[
            "Drug", "site_name", "province", "display_qty",
            "Daily Usage (7d)", "Weekly Usage (7d)", "Monthly Usage (30d)",
            "Days of Supply",
        ]].rename(columns={
            "site_name": "Site",
            "province": "Province",
            "display_qty": "Qty on Hand",
        }).reset_index(drop=True)

        shortage_flags = critical["shortage_active"].tolist()

        def highlight_critical(row):
            color = "#90330B" if shortage_flags[row.name] == 1 else ""
            return [f"background-color: {color}" if color else "" for _ in row]

        styled = display_df.style.apply(highlight_critical, axis=1)

        st.dataframe(styled, use_container_width=True, hide_index=True)

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
            st.dataframe(recent, hide_index=True, use_container_width=True)

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
        full["Daily Usage (7d)"] = full["avg_daily_usage_7d"].map(
            lambda x: f"{x:,.0f}"
        )
        full["Weekly Usage (7d)"] = full["avg_daily_usage_7d"].map(
            lambda x: f"{x * 7:,.0f}"
        )
        full["Monthly Usage (30d)"] = full["avg_daily_usage_30d"].map(
            lambda x: f"{x * 30:,.0f}"
        )

        display_full = full[[
            "Drug", "site_name", "city", "province", "display_qty",
            "Daily Usage (7d)", "Weekly Usage (7d)", "Monthly Usage (30d)",
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
                color = "#90330B"
            elif level == "critical":
                color = "#5C1A1A"
            elif level == "concern":
                color = "#4A3800"
            elif level == "untracked":
                color = "#2A2A2A"
            else:
                color = ""
            return [f"background-color: {color}" if color else "" for _ in row]

        styled_full = display_full.style.apply(highlight_full, axis=1)
        st.dataframe(styled_full, use_container_width=True, hide_index=True)

        st.caption(
            "Critical + shortage: dark orange  |  Critical: dark red  |  "
            "Concern: dark amber  |  Untracked/negative: grey"
        )
