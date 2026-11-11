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

df = load_data()

# ---------------------------------------------------------------------------
# Sidebar — cascading geography filters
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

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("BDM Inventory Intelligence")
st.caption("Drugs at ≤ 7 days of supply — snapshot 2026-11-11")

# ---------------------------------------------------------------------------
# Summary metric tiles
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Critical Items", len(critical))
col2.metric("Shortage Flags", int(critical["shortage_active"].sum()))
col3.metric("Sites Affected", critical["site_id"].nunique())
col4.metric("Provinces Affected", critical["province"].nunique())

st.divider()

# ---------------------------------------------------------------------------
# Alert table
# ---------------------------------------------------------------------------
if critical.empty:
    st.info("No critical items match the current filters.")
else:
    # Drug column: append shortage tier badge when active
    critical["Drug"] = critical.apply(
        lambda r: f"{r['generic_name']} [{r['shortage_tier']}]"
        if r["shortage_active"] == 1 else r["generic_name"],
        axis=1,
    )

    # Formatted display columns
    critical["Days of Supply"] = critical["days_of_supply"].map(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    critical["Avg Daily Usage (7d)"] = critical["avg_daily_usage_7d"].map(
        lambda x: f"{x:,.0f}"
    )

    display_df = critical[[
        "Drug", "site_name", "province", "display_qty",
        "Avg Daily Usage (7d)", "Days of Supply",
    ]].rename(columns={
        "site_name": "Site",
        "province": "Province",
        "display_qty": "Qty on Hand",
    }).reset_index(drop=True)

    # Row highlighting: shortage rows get a light red background
    shortage_flags = critical["shortage_active"].tolist()

    def highlight_shortage(row):
        color = "#90330B" if shortage_flags[row.name] == 1 else ""
        return [f"background-color: {color}" if color else "" for _ in row]

    styled = display_df.style.apply(highlight_shortage, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

    if int(critical["shortage_active"].sum()) > 0:
        st.caption("Highlighted rows have an active drug shortage.")
