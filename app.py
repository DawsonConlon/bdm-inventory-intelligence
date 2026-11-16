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
# On Streamlit Cloud the repo is mounted read-only; fall back to /tmp.
_data_dir = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(_data_dir, "bdm.db") if os.access(_data_dir, os.W_OK) else "/tmp/bdm.db"

if not os.path.exists(DB_PATH    ):
    from data.seed import seed
    seed()

# ---------------------------------------------------------------------------
# Data loading — cached for the session 
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    """
    Load the full inventory dashboard view from the database.

    Reads from v_inventory_dashboard, a SQL view that pre-joins sites, drugs,
    and the most recent inventory snapshot for each drug-site pair. Caching
    with @st.cache_data means the query runs once per session; Streamlit
    re-runs the script on every user interaction, but the data is reused.

    Returns
    -------
    pd.DataFrame
        One row per drug-site combination. Key columns: generic_name,
        site_name, province, alert_level, days_of_supply, shortage_active,
        shortage_tier, display_qty, avg_daily_usage_7d, avg_daily_usage_30d.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM v_inventory_dashboard", conn)
    conn.close()
    return df

@st.cache_data
def load_purchase_orders():
    """
    Load all purchase orders from the database.

    Used to build the procurement history panel in Tab 1. Loaded once and
    filtered in-memory per drug-site selection so we avoid repeated queries.

    Returns
    -------
    pd.DataFrame
        All rows from purchase_orders. Key columns: drug_id, site_id,
        distributor_id, order_date, quantity_ordered, qty_on_hand_at_order,
        unit_cost, lead_time_days, status.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM purchase_orders", conn)
    conn.close()
    return df

@st.cache_data
def load_distributors():
    """
    Load distributor reference data from the database.

    Merged into purchase orders so the procurement panel can display
    human-readable distributor names instead of raw IDs.

    Returns
    -------
    pd.DataFrame
        All rows from distributors. Key columns: distributor_id,
        distributor_name, distributor_type.
    """
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

# Snapshot the critical rows before any filtering so we always start
# from the full critical set and can re-apply geography selections cleanly.
critical = df[df["alert_level"] == "critical"].copy()

# filter_base drives the dropdown options, not the displayed data.
# Using the full df means every site appears in the Site picker even if
# that site has no critical items — prevents the Calgary / "missing site" bug.
filter_base = df.copy()

regions = ["All"] + sorted(filter_base["region"].dropna().unique().tolist())
region = st.sidebar.selectbox("Region", regions)
if region != "All":
    filter_base = filter_base[filter_base["region"] == region]

provinces = ["All"] + sorted(filter_base["province"].dropna().unique().tolist())
province = st.sidebar.selectbox("Province", provinces)
if province != "All":
    filter_base = filter_base[filter_base["province"] == province]

cities = ["All"] + sorted(filter_base["city"].dropna().unique().tolist())
city = st.sidebar.selectbox("City", cities)
if city != "All":
    filter_base = filter_base[filter_base["city"] == city]

site_names = ["All"] + sorted(filter_base["site_name"].dropna().unique().tolist())
site = st.sidebar.selectbox("Site", site_names)

# Apply selections to the critical subset
if region != "All":
    critical = critical[critical["region"] == region]
if province != "All":
    critical = critical[critical["province"] == province]
if city != "All":
    critical = critical[critical["city"] == city]
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
  <div class="leg-desc">≤7 days supply, no current shortage: Order needed</div></div>
</div>
<div class="leg-row">
  <div class="leg-dot" style="background:#7a6000;border:1px solid #a08000;"></div>
  <div><div class="leg-label">Concern</div>
  <div class="leg-desc">8–14 days supply: Not yet critical, monitor closely</div></div>
</div>
<div class="leg-row">
  <div class="leg-dot" style="background:#5A5A5A;border:1px solid #888;"></div>
  <div><div class="leg-label">Untracked / N/A</div>
  <div class="leg-desc">Qty not tracked or negative: Supply cannot be calculated</div></div>
</div>
<div class="leg-row">
  <div class="leg-dot" style="background:#2B2E31;border:1px solid #444;"></div>
  <div><div class="leg-label">Healthy</div>
  <div class="leg-desc">&gt;14 days supply: No action needed</div></div>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.markdown("**Health Canada Shortage Tiers**")
st.sidebar.markdown("""
<style>
.tier-row { display:flex; align-items:flex-start; gap:8px; margin-bottom:10px; }
.tier-badge { font-size:10px; font-weight:700; color:#E6E7E8; background:#5A1A1A; border:1px solid #8B0C0C; border-radius:3px; padding:1px 5px; flex-shrink:0; margin-top:2px; white-space:nowrap; }
.tier-label { font-size:12px; font-weight:600; color:#E6E7E8; }
.tier-desc { font-size:11px; color:#9a9b9c; line-height:1.4; margin-top:1px; }
</style>
<div class="tier-row">
  <div class="tier-badge">Tier 1</div>
  <div><div class="tier-label">Manageable</div>
  <div class="tier-desc">Supply is interrupted but alternatives exist and patient care is not expected to be impacted</div></div>
</div>
<div class="tier-row">
  <div class="tier-badge">Tier 2</div>
  <div><div class="tier-label">Serious</div>
  <div class="tier-desc">Shortage may impact patient care; alternatives may be limited or require protocol changes</div></div>
</div>
<div class="tier-row">
  <div class="tier-badge">Tier 3</div>
  <div><div class="tier-label">Critical</div>
  <div class="tier-desc">Shortage will likely impact patient care; no suitable alternatives or all alternatives are also constrained</div></div>
</div>
<div style="font-size:10px;color:#6a6b6c;margin-top:4px;">Source: Health Product Shortages Canada — healthproductshortages.ca</div>
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
# shortage_active is 0/1 integer — sum() gives the count of active shortages
col2.metric("Shortage Flags", int(critical["shortage_active"].sum()))
# nunique() counts distinct IDs, so a site with multiple critical drugs counts once
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
        critical["Drug"] = critical["generic_name"]
        critical["Shortage"] = critical.apply(
            lambda r: r["shortage_tier"] if r["shortage_active"] == 1 else "None",
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
            "Drug", "Shortage", "site_name", "province", "display_qty",
            "Daily Usage", "Weekly Usage", "Monthly Usage",
            "Days of Supply",
        ]].rename(columns={
            "site_name": "Site",
            "province": "Province",
            "display_qty": "Qty on Hand",
        }).reset_index(drop=True)

        shortage_flags = critical["shortage_active"].tolist()

        def highlight_critical(row):
            """
            Apply row-level background color to the Critical Alerts table.

            Every row in Tab 1 is already critical (≤7 days). The only
            distinction here is whether a Health Canada shortage is also active.
            row.name is the DataFrame integer index, used to look up the
            pre-built shortage_flags list in O(1) rather than re-querying.

            Parameters
            ----------
            row : pd.Series
                One row of display_df, passed by Styler.apply(axis=1).

            Returns
            -------
            list[str]
                One CSS background-color string per cell in the row.
            """
            # Maroon for critical + active shortage; orange for critical only
            color = "#8B0C0C" if shortage_flags[row.name] == 1 else "#E96A10C3"
            return [f"background-color: {color}" for _ in row]

        styled = display_df.style.apply(highlight_critical, axis=1)

        st.dataframe(styled, width="stretch", hide_index=True)


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

            recent5 = orders.head(5).reset_index(drop=True)

            # Walk the 5 most recent orders (sorted newest-first) to derive two
            # computed columns that are not stored in the database:
            #
            #   Days Since Last Order — calendar days between consecutive orders.
            #   Units Used            — stock consumed between orders, calculated as:
            #                           prev_qty_on_hand + prev_qty_ordered − this_qty_on_hand
            #
            # Row i+1 is always the older order. The final (oldest) row gets "—"
            # because there is no earlier row to diff against.
            days_since_col = []
            units_used_col = []
            for i in range(len(recent5)):
                if i == len(recent5) - 1:
                    # Oldest visible row — no earlier order to compare against
                    days_since_col.append("—")
                    units_used_col.append("—")
                else:
                    d_this = pd.to_datetime(recent5.iloc[i]["order_date"])
                    d_prev = pd.to_datetime(recent5.iloc[i + 1]["order_date"])
                    days_since_col.append(str((d_this - d_prev).days))

                    prev_qty     = recent5.iloc[i + 1]["qty_on_hand_at_order"]
                    prev_ordered = recent5.iloc[i + 1]["quantity_ordered"]
                    this_qty     = recent5.iloc[i]["qty_on_hand_at_order"]
                    if pd.notna(prev_qty) and pd.notna(this_qty):
                        # Units consumed = what was on hand + what arrived − what remains
                        used = int(prev_qty + prev_ordered - this_qty)
                        units_used_col.append(f"{used:,}")
                    else:
                        units_used_col.append("—")

            recent5 = recent5.copy()
            recent5["Days Since Last Order"] = days_since_col
            recent5["Units Used"]      = units_used_col
            recent5["Qty on Hand"]     = recent5["qty_on_hand_at_order"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "—"
            )
            recent5["Qty Ordered"]     = recent5["quantity_ordered"].apply(lambda x: f"{x:,}")
            recent5["Lead (days)"]     = recent5.apply(
                lambda r: "—" if r["status"] == "in_transit" else str(int(r["lead_time_days"])),
                axis=1,
            )

            recent_display = recent5[[
                "order_date", "distributor_name",
                "Qty on Hand", "Days Since Last Order", "Units Used", "Qty Ordered",
                "unit_cost", "Lead (days)", "status",
            ]].rename(columns={
                "order_date":       "Order Date",
                "distributor_name": "Distributor",
                "unit_cost":        "Unit Cost ($)",
                "Lead (days)":      "Days to Delivery",
                "status":           "Status",
            })
            st.dataframe(recent_display, hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# Tab 2 — Full Inventory
# ---------------------------------------------------------------------------
with tab2:
    if full.empty:
        st.info("No items match the current filters.")
    else:
        full["Drug"] = full["generic_name"]
        full["Shortage"] = full.apply(
            lambda r: r["shortage_tier"] if r["shortage_active"] == 1 else "None",
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
            "Drug", "Shortage", "site_name", "city", "province", "display_qty",
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
            """
            Apply row-level background color to the Full Inventory table.

            Five distinct states are possible in Tab 2, compared to the two
            in Tab 1. Healthy rows return an empty string so they inherit the
            default Streamlit table background rather than a hard-coded color,
            which keeps them legible in both light and dark themes.

            Parameters
            ----------
            row : pd.Series
                One row of display_full, passed by Styler.apply(axis=1).

            Returns
            -------
            list[str]
                One CSS background-color string (or empty string) per cell.
            """
            level = alert_levels[row.name]
            shortage = shortage_flags_full[row.name]
            if level == "critical" and shortage == 1:
                color = "#8B0C0C"       # maroon  — critical + active shortage
            elif level == "critical":
                color = "#E96A10C3"     # orange  — critical, no shortage
            elif level == "concern":
                color = "#4A3800"       # amber   — 8–14 days
            elif level == "untracked":
                color = "#3A3A3A"       # grey    — qty NULL or negative
            else:
                color = ""              # no fill — healthy (>14 days)
            return [f"background-color: {color}" if color else "" for _ in row]

        styled_full = display_full.style.apply(highlight_full, axis=1)
        st.dataframe(styled_full, width="stretch", hide_index=True)

