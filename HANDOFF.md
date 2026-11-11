# Session Handoff — BDM Inventory Intelligence

This file exists to bring a new Claude Code session fully up to speed. Read it completely before doing anything.

---

## What We Are Building

A working mini inventory intelligence tool for BDM Healthware as a candidate build challenge. The tool must answer one question in seconds:

> **Which drugs, at which sites, have 7 days of supply or less?**

The tool is a Streamlit web app backed by a relational database, populated with a mix of real public data and clearly labelled simulated data.

---

## The Challenge Requirements

**Must-have capabilities:**
1. Usage — units consumed per item per site (daily/weekly/monthly), transfers/reversals removed
2. Unit normalisation — one canonical dispensing unit per item, conversions stated
3. Quantity on hand — untracked or negative stock shows as "N/A", never zero
4. Days of supply — stock ÷ average daily usage, flagged red at ≤7 days
5. Geography rollup — every metric viewable by site, city, and region/province

**Stretch capabilities:**
6. Demand forecast — probabilistic 14-day forecast with quantiles
7. Shortage signal — match a public shortage feed, flag at-risk items

**Deliverables:**
- Repo that runs end to end in one command
- Streamlit UI answering the 7-day question
- One-page write-up (sources, what was simulated, data problems, what's next)
- 20-minute walkthrough with BDM team

---

## Repository

GitHub: https://github.com/DawsonConlon/bdm-inventory-intelligence (private, main branch)

Local working directory: `/Users/dawsonconlon/coding/claude_code/bdm/`

Files currently in the repo:
- `BUILD_LOG.md` — daily progress log
- `BIBLIOGRAPHY.md` — APA-formatted data source citations
- `HANDOFF.md` — this file

---

## Database Design — 4 Tables

### Table 1: `sites` (simulated)
Five hospital pharmacy locations across Canadian provinces.

| site_id | site_name | city | province | region |
|---|---|---|---|---|
| S01 | Royal University Hospital Pharmacy | Saskatoon | SK | Prairies |
| S02 | Foothills Medical Centre Pharmacy | Calgary | AB | Prairies |
| S03 | Vancouver General Hospital Pharmacy | Vancouver | BC | Pacific |
| S04 | The Ottawa Hospital Pharmacy | Ottawa | ON | Central |
| S05 | QEII Health Sciences Pharmacy | Halifax | NS | Atlantic |

### Table 2: `drugs`
Five drugs. Real DINs from Health Canada DPD. Shortage flags sourced manually from healthproductshortages.ca on 2026-11-11.

| drug_id | generic_name | brand_name | din | shortage_active | shortage_tier | notes |
|---|---|---|---|---|---|---|
| D1 | Acetylcholine Chloride | MIOCHOL-E | 02133326 | Yes | Tier 3 | Ophthalmic surgical; manufacturing disruption; active since 2025-12-04, runs to 2027-02-05. ATC: S01EB. Report ID 272933 |
| D2 | Hydromorphone | APO-Hydromorphone | TBD | Verify | TBD | March 2026 shortage reported; current status needs manual check at healthproductshortages.ca |
| D3 | Atorvastatin | Lipitor | 02230711 | No | — | Common statin |
| D4 | Insulin Glargine | Lantus | 02240292 | No | — | High daily volume drug |
| D5 | Metoprolol | Lopressor | 00648051 | No | — | Common cardiac drug |

### Table 3: `inventory_snapshots`
25 rows (5 sites × 5 drugs). The centre of the relational model. Joined to `sites` on `site_id` and to `drugs` on `drug_id`.

Key columns: `snapshot_id`, `site_id` (FK), `drug_id` (FK), `snapshot_date`, `qty_on_hand`, `tracking_status`, `avg_daily_usage_7d`, `avg_daily_usage_30d`, `days_of_supply`, `display_qty`, `alert_level`

Alert levels: `critical` (≤7 days), `concern` (8–14 days), `none` (>14 days), `untracked` (NULL or negative qty — shows as N/A)

### Table 4: `drug_alternatives`
Therapeutic substitutes for each drug. DINs and ATC class data from Health Canada DPD. Shortage status manually sourced. Stock simulated.

Key columns: `alt_id`, `primary_drug_id` (FK → drugs), `alt_generic_name`, `alt_din`, `alt_atc_code`, `alt_shortage_active`, `alt_shortage_tier`, `alt_qty_on_hand_all_sites`, `alt_availability`

### Final deliverable view: `v_inventory_dashboard`
A flat SQL view joining all 4 tables. The Streamlit UI queries this view. The 7-day alert screen runs:

```sql
SELECT s.site_name, s.province, d.generic_name,
       i.display_qty, i.days_of_supply, i.alert_level,
       d.shortage_tier
FROM   inventory_snapshots i
JOIN   sites  s ON i.site_id  = s.site_id
JOIN   drugs  d ON i.drug_id  = d.drug_id
WHERE  i.alert_level = 'critical'
ORDER  BY i.days_of_supply ASC;
```

---

## 10 Showcase Situations Engineered into the Data

| # | Situation |
|---|---|
| 1 | Healthy stock (>14 days), no flags |
| 2 | Concern (8–14 days), no flags |
| 3 | Critical (≤7 days), no shortage |
| 4 | Exactly 7 days — boundary edge case |
| 5 | Critical stock + active shortage flag |
| 6 | Healthy stock + active shortage flag |
| 7 | Concern stock + active shortage flag |
| 8 | Untracked stock (NULL qty) → N/A |
| 9 | Negative stock (data error) → N/A |
| 10 | Same drug, opposite risk at different sites (geography rollup) |

---

## Data Sources

| Source | Type | Used For |
|---|---|---|
| Health Canada Drug Product Database (DPD) REST API | Real | Drug names, DINs, strengths, canonical units, ATC therapeutic class. Base URL: `https://health-products.canada.ca/api/drug/`. DIN lookup: `/drugproduct/?din=XXXXXXXX&type=json`. Therapeutic class: `/therapeuticclass/?id=<drug_code>&type=json` |
| Health Product Shortages Canada | Real — manual lookup | Shortage flags and tier levels. Site blocks automated fetching (403). Data sourced by hand from healthproductshortages.ca, labelled with lookup date 2026-11-11 |
| Simulated | Synthetic | Stock levels, avg daily usage rates (to be grounded in researched Canadian hospital baselines), site locations |

---

## Tech Stack (partially decided)

- **Language:** Python 3.11+
- **UI:** Streamlit
- **Data ingestion:** `requests` + `pandas`
- **Charting:** Plotly (via Streamlit)
- **Run command:** `streamlit run app.py`

### ⚠️ DATABASE SERVICE NOT YET DECIDED — THIS IS THE NEXT DECISION

SQLite was the original assumption (zero setup, single file). However, the user wants to query the database in a workbench-style tool. SQL Workbench connects to server-based databases (MySQL, PostgreSQL), not SQLite files. Options discussed:

- **SQLite + DBeaver** — keep SQLite, use DBeaver as the GUI query tool (free, works with SQLite natively, looks like a full workbench)
- **SQLite + DB Browser for SQLite** — purpose-built SQLite GUI, simpler but less workbench-like
- **PostgreSQL** — full server database, connects natively to SQL Workbench, but requires a running server (Docker or local install)

**The user has not made this decision yet. Start the next session by resolving this choice before writing any code.**

---

## Proposed Repo Structure (pending database decision)

```
bdm-inventory-intelligence/
├── app.py               ← Streamlit UI
├── data/
│   ├── seed.py          ← builds and populates the database
│   └── bdm.db           ← generated database file (if SQLite)
├── requirements.txt
├── BUILD_LOG.md
├── BIBLIOGRAPHY.md
├── HANDOFF.md
└── writeup.md
```

---

## Key Human Decisions Already Made (do not revisit without Dawson)

1. **Drop Medicaid SDUD** — the US dataset is state-level quarterly aggregates, too coarse for per-site daily usage. Usage will be simulated from researched Canadian hospital baselines.
2. **Add `drug_alternatives` table** — Dawson's idea; makes shortage tiers actionable by showing whether substitutes are themselves compromised.
3. **MIOCHOL-E as the Tier 3 drug** — chosen over Stannous MAA Kit because it has an ATC code (enabling real alternatives lookup) and a longer active shortage.
4. **Manual shortage lookup** — healthproductshortages.ca blocks automated fetching entirely; data sourced by hand and labelled with the lookup date.

---

## Open Items for Next Session

1. **Decide the database service** (SQLite vs PostgreSQL — see above)
2. **Verify Hydromorphone shortage status** manually at healthproductshortages.ca (D2)
3. **Research avg daily usage baselines** for the 5 chosen drugs in Canadian hospital settings
4. **Begin writing code** — seed script first, then app.py

---

## Important Notes

- The user's name is Dawson. Refer to design decisions as coming from Dawson where credited.
- The challenge contact is Trevor Tessier at BDM Healthware (Saskatoon, SK).
- Do not use emojis in responses.
- Keep responses concise and direct.
- Always update `BUILD_LOG.md` at the end of a session and push to GitHub.
