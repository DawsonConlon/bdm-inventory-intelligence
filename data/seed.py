"""
BDM Inventory Intelligence — database seed script.

Creates data/bdm.db from scratch, populates all tables, and creates the
v_inventory_dashboard view. Idempotent: re-running drops and recreates everything.

Run it with:  python data/seed.py
"""

import os
import random
import sqlite3
from datetime import date, timedelta

# bdm.db is created next to this script (data/bdm.db), no matter which folder
# you run the script from. __file__ is the path of this script.
DB_PATH = os.path.join(os.path.dirname(__file__), "bdm.db")

# The "as of" date stamped on every inventory row and on the shortage lookup.
# Dates are stored as ISO text (YYYY-MM-DD) because SQLite has no date type.
SNAPSHOT_DATE = "2026-11-11"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def create_tables(conn: sqlite3.Connection) -> None:
    # executescript() runs several SQL statements in one call.
    # The DROPs come first so the script can be re-run safely: old tables are
    # wiped and rebuilt. "IF EXISTS" stops an error on the very first run.
    conn.executescript("""
        DROP TABLE IF EXISTS purchase_orders;
        DROP TABLE IF EXISTS inventory_snapshots;
        DROP TABLE IF EXISTS drugs;
        DROP TABLE IF EXISTS sites;
        DROP TABLE IF EXISTS distributors;
        DROP VIEW  IF EXISTS v_inventory_dashboard;

        -- sites: the 5 hospital pharmacies. One row per site.
        CREATE TABLE sites (
            site_id   TEXT PRIMARY KEY,   -- short code like 'S01'
            site_name TEXT NOT NULL,
            city      TEXT NOT NULL,
            province  TEXT NOT NULL,
            region    TEXT NOT NULL       -- Prairies / Pacific / Central / Atlantic
        );

        -- drugs: the 5 tracked drugs, including their shortage status.
        -- Shortage info lives here (not per site) because a shortage is national.
        CREATE TABLE drugs (
            drug_id              TEXT PRIMARY KEY,   -- 'D1'..'D5'
            generic_name         TEXT NOT NULL,
            brand_name           TEXT NOT NULL,
            din                  TEXT NOT NULL,      -- Health Canada Drug Identification Number (TEXT keeps leading zeros)
            atc_code             TEXT,               -- WHO drug classification code
            shortage_active      INTEGER NOT NULL DEFAULT 0,  -- SQLite has no boolean: 1 = yes, 0 = no
            shortage_tier        TEXT,               -- severity, e.g. 'Tier 3'
            shortage_report_id   TEXT,               -- Health Canada shortage report number
            shortage_start_date  TEXT,
            shortage_end_date    TEXT,               -- estimated end
            shortage_lookup_date TEXT,               -- when we checked the shortage status
            notes                TEXT
        );

        -- inventory_snapshots: stock level of one drug at one site on one date.
        -- This is the core table the dashboard is built on (5 sites x 5 drugs = 25 rows).
        CREATE TABLE inventory_snapshots (
            snapshot_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id            TEXT    NOT NULL REFERENCES sites(site_id),   -- foreign key to sites
            drug_id            TEXT    NOT NULL REFERENCES drugs(drug_id),   -- foreign key to drugs
            snapshot_date      TEXT    NOT NULL,
            qty_on_hand        REAL,                -- NULL allowed: untracked site has no number
            tracking_status    TEXT    NOT NULL,    -- 'tracked' / 'untracked' / 'negative' (bad data)
            avg_daily_usage_7d  REAL    NOT NULL,   -- units used per day, last 7 days
            avg_daily_usage_30d REAL    NOT NULL,   -- units used per day, last 30 days
            days_of_supply     REAL,                -- qty / avg 7d usage; NULL when it can't be trusted
            display_qty        TEXT    NOT NULL,    -- ready-to-show text, e.g. '7,700 tablets' or 'N/A'
            alert_level        TEXT    NOT NULL     -- 'critical' / 'concern' / 'none' / 'untracked'
        );

        -- distributors: Canadian hospital drug distributors.
        CREATE TABLE distributors (
            distributor_id   TEXT PRIMARY KEY,
            distributor_name TEXT NOT NULL,
            distributor_type TEXT NOT NULL,  -- 'National' or 'Specialty'
            contact_email    TEXT
        );

        -- purchase_orders: 6 months of procurement history per site per drug.
        -- Lead times and costs vary by distributor — this is the data that
        -- feeds future ML models for reorder-point and lead-time prediction.
        CREATE TABLE purchase_orders (
            order_id               TEXT PRIMARY KEY,
            site_id                TEXT    NOT NULL REFERENCES sites(site_id),
            drug_id                TEXT    NOT NULL REFERENCES drugs(drug_id),
            distributor_id         TEXT    NOT NULL REFERENCES distributors(distributor_id),
            order_date             TEXT    NOT NULL,   -- ISO date
            delivery_date          TEXT    NOT NULL,
            lead_time_days         INTEGER NOT NULL,
            unit_cost              REAL    NOT NULL,   -- cost per canonical unit (vial / tablet / IU)
            quantity_ordered       INTEGER NOT NULL,
            status                 TEXT    NOT NULL,   -- 'delivered' / 'in_transit' / 'pending'
            qty_on_hand_at_order   INTEGER             -- stock level when this order was placed; NULL for untracked/negative sites
        );

    """)


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

def insert_sites(conn: sqlite3.Connection) -> None:
    # Each tuple is one row, in the same column order as the sites table.
    rows = [
        ("S01", "Royal University Hospital Pharmacy",    "Saskatoon", "SK", "Prairies"),
        ("S02", "Foothills Medical Centre Pharmacy",     "Calgary",   "AB", "Prairies"),
        ("S03", "Vancouver General Hospital Pharmacy",   "Vancouver", "BC", "Pacific"),
        ("S04", "The Ottawa Hospital Pharmacy",          "Ottawa",    "ON", "Central"),
        ("S05", "QEII Health Sciences Pharmacy",         "Halifax",   "NS", "Atlantic"),
    ]
    # executemany runs the INSERT once per tuple. Each "?" is filled by one
    # value from the tuple. Using "?" (instead of building the string by hand)
    # is the safe way to pass values into SQL.
    conn.executemany(
        "INSERT INTO sites VALUES (?,?,?,?,?)",
        rows,
    )


# ---------------------------------------------------------------------------
# Drugs
# ---------------------------------------------------------------------------

def insert_drugs(conn: sqlite3.Connection) -> None:
    # Column order: id, generic, brand, DIN, ATC, shortage_active, tier,
    # report_id, start, end, lookup_date, notes.
    # None becomes NULL in the database (used when there is no shortage).
    rows = [
        # D1 is the only drug with a real, active shortage (the story of the demo).
        (
            "D1", "Acetylcholine Chloride", "MIOCHOL-E", "02133326", "S01EB",
            1, "Tier 3", "272933", "2025-12-04", "2027-02-05", SNAPSHOT_DATE,
            "Ophthalmic surgical (cataract); manufacturing disruption.",
        ),
        (
            "D2", "Hydromorphone HCl", "APO-Hydromorphone", "02364123", "N02AA",
            0, None, None, None, None, None,
            "Last shortage resolved 2017-12-14 (Report 26163). No active shortage.",
        ),
        (
            "D3", "Atorvastatin", "Lipitor", "02230711", "C10AA05",
            0, None, None, None, None, None,
            "Common statin.",
        ),
        (
            "D4", "Insulin Glargine", "Lantus", "02240292", "A10AE04",
            0, None, None, None, None, None,
            "High daily volume long-acting insulin.",
        ),
        (
            "D5", "Metoprolol", "Lopressor", "00648051", "C07AB02",
            0, None, None, None, None, None,
            "Common cardiac beta-blocker.",
        ),
    ]
    conn.executemany(
        """INSERT INTO drugs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )


# ---------------------------------------------------------------------------
# Inventory snapshots — all 25 rows approved by Dawson on 2026-11-11
# ---------------------------------------------------------------------------

def _snap(site_id, drug_id, qty, avg7, avg30, days, alert, tracking, unit):
    """Build one snapshot row. Handles N/A display and NULL days."""
    # The leading underscore is a Python convention meaning "internal helper,
    # only used inside this file".
    #
    # Two kinds of rows can't be trusted for a days-of-supply number:
    #   untracked: the site doesn't track this drug, so qty is None.
    #   negative:  the site reported a negative quantity (a data error).
    # For both we show "N/A" and store NULL for days_of_supply, so the
    # dashboard never displays a misleading number.
    if tracking in ("untracked", "negative"):
        display = "N/A"
        days_val = None
        qty_val = qty  # preserves NULL or negative as-is
    else:
        qty_val = qty
        days_val = days
        # Format qty with commas; integers only (all our values are whole numbers)
        # e.g. 7700 -> "7,700 tablets"
        display = f"{int(qty):,} {unit}"
    # Tuple order must match the column list in insert_inventory_snapshots().
    return (site_id, drug_id, SNAPSHOT_DATE, qty_val, tracking, avg7, avg30, days_val, display, alert)


def insert_inventory_snapshots(conn: sqlite3.Connection) -> None:
    # Arguments to _snap: site, drug, qty, avg 7d usage, avg 30d usage,
    #                     days of supply, alert level, tracking status, unit.
    #
    # days_of_supply was calculated by hand as qty / avg 7-day usage, and the
    # alert level follows these cutoffs: critical <= 7 days, concern < 15 days,
    # none >= 15 days. Each drug is deliberately seeded with a mix of levels
    # so the dashboard has something interesting to show.
    rows = [
        # D1 — Acetylcholine Chloride (vials) — Active Shortage Tier 3
        _snap("S01","D1", 32,   8,    7,    4.0,  "critical",  "tracked",   "vials"),
        _snap("S02","D1", 72,   6,    5,    12.0, "concern",   "tracked",   "vials"),
        _snap("S03","D1", 180,  9,    9,    20.0, "none",      "tracked",   "vials"),
        _snap("S04","D1", 49,   7,    7,    7.0,  "critical",  "tracked",   "vials"),
        _snap("S05","D1", None, 4,    4,    None, "untracked", "untracked", "vials"),  # edge case: no data

        # D2 — Hydromorphone HCl 2mg (tablets) — No Shortage
        _snap("S01","D2", 7700, 220,  200,  35.0, "none",      "tracked",   "tablets"),
        _snap("S02","D2", 1980, 180,  170,  11.0, "concern",   "tracked",   "tablets"),
        _snap("S03","D2", 750,  150,  140,  5.0,  "critical",  "tracked",   "tablets"),
        _snap("S04","D2", -40,  160,  155,  None, "untracked", "negative",  "tablets"),  # edge case: bad data
        _snap("S05","D2", 2400, 120,  115,  20.0, "none",      "tracked",   "tablets"),

        # D3 — Atorvastatin (tablets) — No Shortage
        _snap("S01","D3", 1890, 90,   85,   21.0, "none",      "tracked",   "tablets"),
        _snap("S02","D3", 1200, 80,   78,   15.0, "none",      "tracked",   "tablets"),
        _snap("S03","D3", 1000, 100,  95,   10.0, "concern",   "tracked",   "tablets"),
        _snap("S04","D3", 350,  70,   68,   5.0,  "critical",  "tracked",   "tablets"),
        _snap("S05","D3", 975,  65,   60,   15.0, "none",      "tracked",   "tablets"),

        # D4 — Insulin Glargine (IU) — No Shortage
        _snap("S01","D4", 36000, 1600, 1500, 22.5, "none",     "tracked",   "IU"),
        _snap("S02","D4", 27000, 1800, 1700, 15.0, "none",     "tracked",   "IU"),
        _snap("S03","D4", 18000, 2000, 1900, 9.0,  "concern",  "tracked",   "IU"),
        _snap("S04","D4", 14000, 1400, 1400, 10.0, "concern",  "tracked",   "IU"),
        _snap("S05","D4", 7200,  1200, 1100, 6.0,  "critical", "tracked",   "IU"),

        # D5 — Metoprolol (tablets) — No Shortage
        _snap("S01","D5", 2250, 150,  145,  15.0, "none",      "tracked",   "tablets"),
        _snap("S02","D5", 1920, 160,  155,  12.0, "concern",   "tracked",   "tablets"),
        _snap("S03","D5", 980,  140,  130,  7.0,  "critical",  "tracked",   "tablets"),
        _snap("S04","D5", 1800, 120,  115,  15.0, "none",      "tracked",   "tablets"),
        _snap("S05","D5", 1200, 100,  95,   12.0, "concern",   "tracked",   "tablets"),
    ]
    # snapshot_id is not listed: AUTOINCREMENT fills it in automatically.
    # Here we name the columns explicitly because we are skipping one.
    conn.executemany(
        """INSERT INTO inventory_snapshots
           (site_id, drug_id, snapshot_date, qty_on_hand, tracking_status,
            avg_daily_usage_7d, avg_daily_usage_30d, days_of_supply,
            display_qty, alert_level)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )


# ---------------------------------------------------------------------------
# Distributors
# ---------------------------------------------------------------------------

def insert_distributors(conn: sqlite3.Connection) -> None:
    rows = [
        ("DIST01", "McKesson Canada",       "National",  "hospital.orders@mckesson.ca"),
        ("DIST02", "Cardinal Health Canada", "National",  "hospital.supply@cardinalhealth.ca"),
        ("DIST03", "Innomar Strategies",     "Specialty", "specialty@innomar.com"),
    ]
    conn.executemany("INSERT INTO distributors VALUES (?,?,?,?)", rows)
    print("Distributors inserted.")


# ---------------------------------------------------------------------------
# Purchase orders — 6 months generated programmatically (May–Nov 2026)
# ---------------------------------------------------------------------------

# Lead time ranges (min, max) in days per distributor
_DIST_LEAD = {
    "DIST01": (2, 5),   # McKesson: national reach, reliable
    "DIST02": (3, 7),   # Cardinal: slightly longer, competitive cost
    "DIST03": (1, 4),   # Innomar: specialty/shortage drugs, fastest
}

# Per drug: (order_freq_days, unit_cost_lo, unit_cost_hi, primary_dist, secondary_dist)
# Innomar is primary for D1 (shortage drug). Cardinal primary for insulin (D4).
# McKesson primary for all others.
_DRUG_ORDER_PROFILE = {
    "D1": (14, 48.00, 62.00,  "DIST03", "DIST01"),
    "D2": (7,  0.52,  0.78,   "DIST01", "DIST02"),
    "D3": (14, 0.28,  0.52,   "DIST01", "DIST02"),
    "D4": (7,  0.052, 0.068,  "DIST02", "DIST01"),
    "D5": (14, 0.18,  0.32,   "DIST01", "DIST02"),
}

# Sites where Cardinal is preferred over McKesson for non-D1 drugs
_SITE_DIST_OVERRIDE = {"S03": "DIST02", "S05": "DIST02"}

# Avg daily usage per site-drug (mirrors inventory_snapshots values)
_AVG_DAILY = {
    ("S01","D1"): 8,    ("S02","D1"): 6,    ("S03","D1"): 9,    ("S04","D1"): 7,    ("S05","D1"): 4,
    ("S01","D2"): 220,  ("S02","D2"): 180,  ("S03","D2"): 150,  ("S04","D2"): 160,  ("S05","D2"): 120,
    ("S01","D3"): 90,   ("S02","D3"): 80,   ("S03","D3"): 100,  ("S04","D3"): 70,   ("S05","D3"): 65,
    ("S01","D4"): 1600, ("S02","D4"): 1800, ("S03","D4"): 2000, ("S04","D4"): 1400, ("S05","D4"): 1200,
    ("S01","D5"): 150,  ("S02","D5"): 160,  ("S03","D5"): 140,  ("S04","D5"): 120,  ("S05","D5"): 100,
}

# Snapshot qty per site-drug on 2026-11-11 (mirrors inventory_snapshots).
# None = untracked or negative — qty_on_hand_at_order will be NULL for all orders at that site/drug.
_SNAPSHOT_QTY = {
    ("S01","D1"): 32,    ("S02","D1"): 72,    ("S03","D1"): 180,  ("S04","D1"): 49,    ("S05","D1"): None,
    ("S01","D2"): 7700,  ("S02","D2"): 1980,  ("S03","D2"): 750,  ("S04","D2"): None,  ("S05","D2"): 2400,
    ("S01","D3"): 1890,  ("S02","D3"): 1200,  ("S03","D3"): 1000, ("S04","D3"): 350,   ("S05","D3"): 975,
    ("S01","D4"): 36000, ("S02","D4"): 27000, ("S03","D4"): 18000,("S04","D4"): 14000, ("S05","D4"): 7200,
    ("S01","D5"): 2250,  ("S02","D5"): 1920,  ("S03","D5"): 980,  ("S04","D5"): 1800,  ("S05","D5"): 1200,
}


def seed_purchase_orders(conn: sqlite3.Connection) -> None:
    rng = random.Random(42)  # fixed seed = reproducible data every run
    start = date(2026, 5, 12)
    today = date(2026, 11, 11)  # snapshot date

    all_rows = []
    order_num = 1

    for site_id in ["S01", "S02", "S03", "S04", "S05"]:
        for drug_id in ["D1", "D2", "D3", "D4", "D5"]:
            freq_days, cost_lo, cost_hi, primary_dist, secondary_dist = _DRUG_ORDER_PROFILE[drug_id]
            avg_daily = _AVG_DAILY[(site_id, drug_id)]

            # Regional distributor preference overrides for non-D1 drugs
            if drug_id != "D1" and site_id in _SITE_DIST_OVERRIDE:
                primary_dist = _SITE_DIST_OVERRIDE[site_id]
                secondary_dist = "DIST01"

            # Build all orders for this (site, drug) pair first so we can
            # backfill qty_on_hand_at_order across the whole sequence.
            pair_orders = []
            order_date = start
            while order_date <= today:
                dist_id = primary_dist if rng.random() < 0.80 else secondary_dist

                lead_lo, lead_hi = _DIST_LEAD[dist_id]
                lead_days = rng.randint(lead_lo, lead_hi)
                delivery_date = order_date + timedelta(days=lead_days)

                buffer = rng.uniform(0.90, 1.30)
                qty = max(1, round(avg_daily * freq_days * buffer))
                unit_cost = round(rng.uniform(cost_lo, cost_hi), 4)

                if delivery_date <= today:
                    status = "delivered"
                elif order_date <= today:
                    status = "in_transit"
                else:
                    status = "pending"

                pair_orders.append({
                    "order_id":      f"PO{order_num:04d}",
                    "site_id":       site_id,
                    "drug_id":       drug_id,
                    "order_date":    order_date,
                    "delivery_date": delivery_date,
                    "lead_days":     lead_days,
                    "unit_cost":     unit_cost,
                    "qty":           qty,
                    "status":        status,
                    "dist_id":       dist_id,
                })
                order_num += 1
                jitter = rng.randint(-2, 2)
                order_date += timedelta(days=freq_days + jitter)

            # Compute qty_on_hand_at_order by walking forward from an opening
            # stock of 2 order cycles. This avoids the backwards-walk breaking
            # for critically low items (e.g. D1/S01 snapshot = 32 vials).
            # Formula: at each order, record current stock, then advance:
            #   running_qty = running_qty + qty_ordered - days_to_next * avg_daily
            # For untracked/negative sites the column stays NULL.
            if _SNAPSHOT_QTY[(site_id, drug_id)] is None:
                for o in pair_orders:
                    o["qty_on_hand_at_order"] = None
            else:
                asc = sorted(pair_orders, key=lambda x: x["order_date"])
                running_qty = float(avg_daily * freq_days * 2)  # ~2 cycles as opening stock
                for i, o in enumerate(asc):
                    o["qty_on_hand_at_order"] = max(0, round(running_qty))
                    days_gap = (
                        (asc[i + 1]["order_date"] - o["order_date"]).days
                        if i + 1 < len(asc)
                        else (today - o["order_date"]).days
                    )
                    running_qty = running_qty + o["qty"] - days_gap * avg_daily

            all_rows.extend(pair_orders)

    conn.executemany(
        """INSERT INTO purchase_orders
           (order_id, site_id, drug_id, distributor_id, order_date, delivery_date,
            lead_time_days, unit_cost, quantity_ordered, status, qty_on_hand_at_order)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (
                o["order_id"], o["site_id"], o["drug_id"], o["dist_id"],
                o["order_date"].isoformat(), o["delivery_date"].isoformat(),
                o["lead_days"], o["unit_cost"], o["qty"], o["status"],
                o["qty_on_hand_at_order"],
            )
            for o in all_rows
        ],
    )
    print(f"Purchase orders inserted: {len(all_rows)} rows.")


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Dashboard view
# ---------------------------------------------------------------------------

def create_view(conn: sqlite3.Connection) -> None:
    # A VIEW is a saved query that behaves like a read-only table. It stitches
    # inventory + site + drug info into one flat table so the Streamlit app
    # can run a simple "SELECT * FROM v_inventory_dashboard" and never has to
    # write JOINs itself. It stores no data of its own, so it is always current.
    conn.execute("""
        CREATE VIEW v_inventory_dashboard AS
        SELECT
            i.snapshot_id,
            s.site_id,
            s.site_name,
            s.city,
            s.province,
            s.region,
            d.drug_id,
            d.generic_name,
            d.brand_name,
            d.din,
            d.atc_code,
            d.shortage_active,
            d.shortage_tier,
            i.snapshot_date,
            i.qty_on_hand,
            i.tracking_status,
            i.avg_daily_usage_7d,
            i.avg_daily_usage_30d,
            i.days_of_supply,
            i.display_qty,
            i.alert_level
        FROM  inventory_snapshots i
        JOIN  sites s ON i.site_id  = s.site_id   -- attach site details to each row
        JOIN  drugs d ON i.drug_id  = d.drug_id   -- attach drug + shortage details
    """)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def seed() -> None:
    # Make sure the data/ folder exists before SQLite tries to create a file in it.
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Opens bdm.db, creating the file if it doesn't exist.
    conn = sqlite3.connect(DB_PATH)
    try:
        # Order matters: parent tables (sites, drugs) must be filled before
        # tables that reference them, and the view is created last because
        # it reads from the tables above.
        create_tables(conn)
        insert_distributors(conn)
        insert_sites(conn)
        insert_drugs(conn)
        insert_inventory_snapshots(conn)
        seed_purchase_orders(conn)
        create_view(conn)

        # Nothing is saved to disk until commit(). If any step above fails,
        # we never reach this line.
        conn.commit()
        print(f"\nDatabase created: {DB_PATH}")
        print("Tables: distributors, sites, drugs, inventory_snapshots, purchase_orders")
        print("View:   v_inventory_dashboard")
    except Exception:
        conn.rollback()  # undo any half-finished inserts
        raise            # re-raise so you still see the real error
    finally:
        conn.close()     # always runs, success or failure


# Only run seed() when this file is executed directly (python seed.py),
# not when another file does "import seed".
if __name__ == "__main__":
    seed()
