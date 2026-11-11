"""
BDM Inventory Intelligence — database seed script.

Creates data/bdm.db from scratch, populates all 4 tables, and creates the
v_inventory_dashboard view. Idempotent: re-running drops and recreates everything.

drug_alternatives are hardcoded with real Health Canada DINs sourced manually
on 2026-11-11. The DPD REST API was returning empty responses at time of seeding.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "bdm.db")
SNAPSHOT_DATE = "2026-11-11"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS drug_alternatives;
        DROP TABLE IF EXISTS inventory_snapshots;
        DROP TABLE IF EXISTS drugs;
        DROP TABLE IF EXISTS sites;
        DROP VIEW  IF EXISTS v_inventory_dashboard;

        CREATE TABLE sites (
            site_id   TEXT PRIMARY KEY,
            site_name TEXT NOT NULL,
            city      TEXT NOT NULL,
            province  TEXT NOT NULL,
            region    TEXT NOT NULL
        );

        CREATE TABLE drugs (
            drug_id              TEXT PRIMARY KEY,
            generic_name         TEXT NOT NULL,
            brand_name           TEXT NOT NULL,
            din                  TEXT NOT NULL,
            atc_code             TEXT,
            shortage_active      INTEGER NOT NULL DEFAULT 0,
            shortage_tier        TEXT,
            shortage_report_id   TEXT,
            shortage_start_date  TEXT,
            shortage_end_date    TEXT,
            shortage_lookup_date TEXT,
            notes                TEXT
        );

        CREATE TABLE inventory_snapshots (
            snapshot_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id            TEXT    NOT NULL REFERENCES sites(site_id),
            drug_id            TEXT    NOT NULL REFERENCES drugs(drug_id),
            snapshot_date      TEXT    NOT NULL,
            qty_on_hand        REAL,
            tracking_status    TEXT    NOT NULL,
            avg_daily_usage_7d  REAL    NOT NULL,
            avg_daily_usage_30d REAL    NOT NULL,
            days_of_supply     REAL,
            display_qty        TEXT    NOT NULL,
            alert_level        TEXT    NOT NULL
        );

        CREATE TABLE drug_alternatives (
            alt_id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            primary_drug_id           TEXT    NOT NULL REFERENCES drugs(drug_id),
            alt_generic_name          TEXT    NOT NULL,
            alt_din                   TEXT,
            alt_atc_code              TEXT,
            alt_shortage_active       INTEGER NOT NULL DEFAULT 0,
            alt_shortage_tier         TEXT,
            alt_qty_on_hand_all_sites REAL,
            alt_availability          TEXT    NOT NULL
        );
    """)


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

def insert_sites(conn: sqlite3.Connection) -> None:
    rows = [
        ("S01", "Royal University Hospital Pharmacy",    "Saskatoon", "SK", "Prairies"),
        ("S02", "Foothills Medical Centre Pharmacy",     "Calgary",   "AB", "Prairies"),
        ("S03", "Vancouver General Hospital Pharmacy",   "Vancouver", "BC", "Pacific"),
        ("S04", "The Ottawa Hospital Pharmacy",          "Ottawa",    "ON", "Central"),
        ("S05", "QEII Health Sciences Pharmacy",         "Halifax",   "NS", "Atlantic"),
    ]
    conn.executemany(
        "INSERT INTO sites VALUES (?,?,?,?,?)",
        rows,
    )


# ---------------------------------------------------------------------------
# Drugs
# ---------------------------------------------------------------------------

def insert_drugs(conn: sqlite3.Connection) -> None:
    rows = [
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
    if tracking in ("untracked", "negative"):
        display = "N/A"
        days_val = None
        qty_val = qty  # preserves NULL or negative as-is
    else:
        qty_val = qty
        days_val = days
        # Format qty with commas; integers only (all our values are whole numbers)
        display = f"{int(qty):,} {unit}"
    return (site_id, drug_id, SNAPSHOT_DATE, qty_val, tracking, avg7, avg30, days_val, display, alert)


def insert_inventory_snapshots(conn: sqlite3.Connection) -> None:
    rows = [
        # D1 — Acetylcholine Chloride (vials) — Active Shortage Tier 3
        _snap("S01","D1", 32,   8,    7,    4.0,  "critical",  "tracked",   "vials"),
        _snap("S02","D1", 72,   6,    5,    12.0, "concern",   "tracked",   "vials"),
        _snap("S03","D1", 180,  9,    9,    20.0, "none",      "tracked",   "vials"),
        _snap("S04","D1", 49,   7,    7,    7.0,  "critical",  "tracked",   "vials"),
        _snap("S05","D1", None, 4,    4,    None, "untracked", "untracked", "vials"),

        # D2 — Hydromorphone HCl 2mg (tablets) — No Shortage
        _snap("S01","D2", 7700, 220,  200,  35.0, "none",      "tracked",   "tablets"),
        _snap("S02","D2", 1980, 180,  170,  11.0, "concern",   "tracked",   "tablets"),
        _snap("S03","D2", 750,  150,  140,  5.0,  "critical",  "tracked",   "tablets"),
        _snap("S04","D2", -40,  160,  155,  None, "untracked", "negative",  "tablets"),
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
    conn.executemany(
        """INSERT INTO inventory_snapshots
           (site_id, drug_id, snapshot_date, qty_on_hand, tracking_status,
            avg_daily_usage_7d, avg_daily_usage_30d, days_of_supply,
            display_qty, alert_level)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )


# ---------------------------------------------------------------------------
# Drug alternatives — fetched live from Health Canada DPD API
# ---------------------------------------------------------------------------

# Alternatives with real Health Canada DINs sourced manually on 2026-11-11.
# The DPD REST API was returning empty responses at time of seeding.
# shortage_active is simulated (healthproductshortages.ca blocks automated access).
# Carbachol flagged as also at risk to make the MIOCHOL-E shortage situation actionable.
# Pilocarpine DIN 02213044 may be discontinued — flagged as Uncertain.
# Insulin Detemir DIN 02271842 has anticipated discontinuation Dec 2025 — flagged as Limited.
_ALTERNATIVES = [
    # D1 — Acetylcholine Chloride alternatives (S01EB ophthalmic parasympathomimetics)
    ("D1", "Carbachol",               "00042544", "S01EB02", 1, "Tier 2", 48,    "Limited"),
    ("D1", "Pilocarpine",             "02213044", "S01EB01", 0, None,     320,   "Uncertain"),

    # D2 — Hydromorphone HCl alternatives (N02AA natural opioid alkaloids)
    ("D2", "Morphine",                "02302764", "N02AA01", 0, None,     12000, "Available"),
    ("D2", "Oxycodone/Acetaminophen", "02324628", "N02AA05", 0, None,     8500,  "Available"),

    # D3 — Atorvastatin alternatives (C10AA statins)
    ("D3", "Rosuvastatin",            "02337991", "C10AA07", 0, None,     9200,  "Available"),
    ("D3", "Simvastatin",             "02332000", "C10AA01", 0, None,     7800,  "Available"),

    # D4 — Insulin Glargine alternatives (A10AE long-acting insulins)
    ("D4", "Insulin Detemir",         "02271842", "A10AE05", 0, None,     24000, "Limited"),
    ("D4", "Insulin Degludec",        "02467860", "A10AE06", 0, None,     18000, "Available"),

    # D5 — Metoprolol alternatives (C07AB selective beta-blockers)
    ("D5", "Bisoprolol",              "02302640", "C07AB07", 0, None,     11000, "Available"),
    ("D5", "Atenolol",                "02266660", "C07AB03", 0, None,     6500,  "Available"),
]


def fetch_drug_alternatives(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """INSERT INTO drug_alternatives
           (primary_drug_id, alt_generic_name, alt_din, alt_atc_code,
            alt_shortage_active, alt_shortage_tier,
            alt_qty_on_hand_all_sites, alt_availability)
           VALUES (?,?,?,?,?,?,?,?)""",
        _ALTERNATIVES,
    )
    print("Drug alternatives inserted.")


# ---------------------------------------------------------------------------
# Dashboard view
# ---------------------------------------------------------------------------

def create_view(conn: sqlite3.Connection) -> None:
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
        JOIN  sites s ON i.site_id  = s.site_id
        JOIN  drugs d ON i.drug_id  = d.drug_id
    """)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def seed() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        create_tables(conn)
        insert_sites(conn)
        insert_drugs(conn)
        insert_inventory_snapshots(conn)
        fetch_drug_alternatives(conn)
        create_view(conn)
        conn.commit()
        print(f"\nDatabase created: {DB_PATH}")
        print("Tables: sites, drugs, inventory_snapshots, drug_alternatives")
        print("View:   v_inventory_dashboard")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
