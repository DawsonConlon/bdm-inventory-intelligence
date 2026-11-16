# Session Handoff — BDM Inventory Intelligence

This file exists to bring a new Claude Code session fully up to speed. Read it completely before doing anything.

---

## What We Are Building

A working mini inventory intelligence tool for BDM Healthware as a candidate build challenge. The tool must answer one question in seconds:

> **Which drugs, at which sites, have 7 days of supply or less?**

The tool is a Streamlit web app backed by a SQLite relational database, populated with a mix of real public data and clearly labelled simulated data.

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
- `BUILD_LOG.md` — daily progress log (includes all approved data tables, usage baselines, and seed script notes)
- `BIBLIOGRAPHY.md` — APA-formatted data source citations
- `HANDOFF.md` — this file
- `requirements.txt` — Python dependencies
- `.gitignore` — excludes `data/bdm.db`, `.DS_Store`, `__pycache__`
- `data/seed.py` — database seed script (complete and working)
- `app.py` — Streamlit UI (Pieces 3–5 — complete, tabs + procurement detail panel)
- `data/seed.py` — now seeds 6 tables: distributors, sites, drugs, inventory_snapshots, drug_alternatives, purchase_orders (471 procurement rows)
- `.streamlit/config.toml` — global theme: `#1F2123` background, `#2B2E31` sidebar, `#E6E7E8` text, `#F4A982` accent, `#90330B` shortage row highlight
- `.claude/launch.json` — browser preview config for Claude Code desktop app

---

## Tech Stack — Fully Decided

- **Language:** Python 3.11+
- **UI:** Streamlit
- **Database:** SQLite — file at `data/bdm.db`, created by the seed script
- **GUI query tool:** DBeaver (free, connects to SQLite natively)
- **Data ingestion:** `requests` + `pandas`
- **Charting:** Plotly (via Streamlit)
- **Run command:** `streamlit run app.py`
- **One-command requirement:** `app.py` checks for `data/bdm.db` on startup and auto-runs the seed script if the file does not exist. The reviewer clones and runs one command — nothing else required.

---

## Repo Structure (to be built)

```
bdm-inventory-intelligence/
├── app.py               ← Streamlit UI; auto-seeds on first run
├── data/
│   ├── seed.py          ← builds and populates the database
│   └── bdm.db           ← generated SQLite file (gitignored)
├── requirements.txt
├── BUILD_LOG.md
├── BIBLIOGRAPHY.md
├── HANDOFF.md
└── writeup.md
```

---

## Database Design — 6 Tables

### Table 1: `sites` (simulated)

| site_id | site_name | city | province | region |
|---|---|---|---|---|
| S01 | Royal University Hospital Pharmacy | Saskatoon | SK | Prairies |
| S02 | Foothills Medical Centre Pharmacy | Calgary | AB | Prairies |
| S03 | Vancouver General Hospital Pharmacy | Vancouver | BC | Pacific |
| S04 | The Ottawa Hospital Pharmacy | Ottawa | ON | Central |
| S05 | QEII Health Sciences Pharmacy | Halifax | NS | Atlantic |

### Table 2: `drugs`

All DINs confirmed from Health Canada DPD. Shortage flags sourced manually from healthproductshortages.ca on 2026-11-11.

| drug_id | generic_name | brand_name | din | shortage_active | shortage_tier | notes |
|---|---|---|---|---|---|---|
| D1 | Acetylcholine Chloride | MIOCHOL-E | 02133326 | Yes | Tier 3 | Ophthalmic surgical; manufacturing disruption; active since 2025-12-04, runs to 2027-02-05. ATC: S01EB. Report ID 272933 |
| D2 | Hydromorphone HCl | APO-Hydromorphone | 02364123 | No | — | Last shortage resolved 2017-12-14 (Report 26163). No active shortage. ATC: N02AA |
| D3 | Atorvastatin | Lipitor | 02230711 | No | — | Common statin. ATC: C10AA05 |
| D4 | Insulin Glargine | Lantus | 02240292 | No | — | High daily volume drug. ATC: A10AE04 |
| D5 | Metoprolol | Lopressor | 00648051 | No | — | Common cardiac drug. ATC: C07AB02 |

### Table 3: `inventory_snapshots` — 25 Approved Rows

All values approved by Dawson on 2026-11-11. Rows marked * have avg_7d diverging from avg_30d (simulated trending demand). days_of_supply = qty_on_hand / avg_daily_usage_7d.

Alert levels: `critical` (≤7 days), `concern` (8–14 days), `none` (>14 days), `untracked` (NULL or negative qty — displays as N/A)

**D1 — Acetylcholine Chloride (vials) — Active Shortage, Tier 3**

| site_id | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert_level | Situation |
|---|---|---|---|---|---|---|
| S01 | 8 | 7* | 32 | 4.0 | critical | #5: critical + shortage |
| S02 | 6 | 5* | 72 | 12.0 | concern | #7: concern + shortage |
| S03 | 9 | 9 | 180 | 20.0 | none | #6: healthy + shortage |
| S04 | 7 | 7 | 49 | 7.0 | critical | #4+5: exactly 7d + shortage |
| S05 | 4 | 4 | NULL | N/A | untracked | #8: untracked stock |

**D2 — Hydromorphone HCl (2mg tablets) — No Shortage**

| site_id | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert_level | Situation |
|---|---|---|---|---|---|---|
| S01 | 220 | 200* | 7700 | 35.0 | none | #1: healthy |
| S02 | 180 | 170 | 1980 | 11.0 | concern | #2: concern |
| S03 | 150 | 140* | 750 | 5.0 | critical | #3: critical, no shortage |
| S04 | 160 | 155 | -40 | N/A | untracked | #9: negative stock |
| S05 | 120 | 115 | 2400 | 20.0 | none | #1: healthy |

**D3 — Atorvastatin (tablets) — No Shortage**

| site_id | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert_level | Situation |
|---|---|---|---|---|---|---|
| S01 | 90 | 85 | 1890 | 21.0 | none | #10: healthy side of geography split |
| S02 | 80 | 78 | 1200 | 15.0 | none | #1: healthy |
| S03 | 100 | 95 | 1000 | 10.0 | concern | #2: concern |
| S04 | 70 | 68 | 350 | 5.0 | critical | #10: critical side of geography split |
| S05 | 65 | 60 | 975 | 15.0 | none | #1: healthy |

**D4 — Insulin Glargine (IU) — No Shortage**

| site_id | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert_level | Situation |
|---|---|---|---|---|---|---|
| S01 | 1600 | 1500* | 36000 | 22.5 | none | #1: healthy |
| S02 | 1800 | 1700 | 27000 | 15.0 | none | #1: healthy |
| S03 | 2000 | 1900 | 18000 | 9.0 | concern | #2: concern |
| S04 | 1400 | 1400 | 14000 | 10.0 | concern | #2: concern |
| S05 | 1200 | 1100* | 7200 | 6.0 | critical | #3: critical |

**D5 — Metoprolol (tablets) — No Shortage**

| site_id | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert_level | Situation |
|---|---|---|---|---|---|---|
| S01 | 150 | 145 | 2250 | 15.0 | none | #1: healthy |
| S02 | 160 | 155 | 1920 | 12.0 | concern | #2: concern |
| S03 | 140 | 130* | 980 | 7.0 | critical | #4: exactly 7d, no shortage |
| S04 | 120 | 115 | 1800 | 15.0 | none | #1: healthy |
| S05 | 100 | 95 | 1200 | 12.0 | concern | #2: concern |

### Table 4: `drug_alternatives`

10 rows (2 per primary drug). DINs sourced manually on 2026-11-11 — the DPD REST API was returning empty responses at time of seeding. Shortage status simulated. Stock simulated.

Key columns: `alt_id`, `primary_drug_id` (FK → drugs), `alt_generic_name`, `alt_din`, `alt_atc_code`, `alt_shortage_active`, `alt_shortage_tier`, `alt_qty_on_hand_all_sites`, `alt_availability`

### Table 5: `distributors`

3 rows. Real Canadian hospital drug distributors.

| distributor_id | distributor_name | distributor_type | contact_email |
|---|---|---|---|
| DIST01 | McKesson Canada | National | hospital.orders@mckesson.ca |
| DIST02 | Cardinal Health Canada | National | hospital.supply@cardinalhealth.ca |
| DIST03 | Innomar Strategies | Specialty | specialty@innomar.com |

### Table 6: `purchase_orders`

471 rows. 6 months of procurement history (May 12 – Nov 11, 2026). Generated programmatically with `random.Random(42)` fixed seed — reproducible on every run.

Key columns: `order_id`, `site_id`, `drug_id`, `distributor_id`, `order_date`, `delivery_date`, `lead_time_days`, `unit_cost`, `quantity_ordered`, `status` (delivered / in_transit / pending)

Distributor assignment logic:
- Innomar (DIST03) is primary for Acetylcholine (D1 — shortage drug); fastest lead 1–4 days
- Cardinal Health (DIST02) is primary for Insulin Glargine (D4); also preferred at S03/S05 for non-D1 drugs
- McKesson (DIST01) is primary for all other drugs/sites
- 80% orders use the primary distributor, 20% secondary

Strategic purpose: this table is the foundation for future ML lead-time prediction and reorder-point optimization models (Dawson's vision).

| primary_drug_id | alt_generic_name | alt_din | shortage_active | availability | Note |
|---|---|---|---|---|---|
| D1 | Carbachol | 00042544 | Yes (Tier 2) | Limited | Makes MIOCHOL-E situation actionable — both primary and first alternative are under shortage |
| D1 | Pilocarpine | 02213044 | No | Uncertain | May be discontinued in DPD |
| D2 | Morphine | 02302764 | No | Available | |
| D2 | Oxycodone/Acetaminophen | 02324628 | No | Available | Combination product |
| D3 | Rosuvastatin | 02337991 | No | Available | |
| D3 | Simvastatin | 02332000 | No | Available | |
| D4 | Insulin Detemir | 02271842 | No | Limited | Anticipated discontinuation Dec 2025 |
| D4 | Insulin Degludec | 02467860 | No | Available | |
| D5 | Bisoprolol | 02302640 | No | Available | |
| D5 | Atenolol | 02266660 | No | Available | |

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

## 10 Showcase Situations

| # | Situation | Row(s) |
|---|---|---|
| 1 | Healthy stock (>14 days), no flags | D2/S01, D2/S05, D3/S02, D3/S05, D4/S01, D4/S02, D5/S01, D5/S04 |
| 2 | Concern (8–14 days), no flags | D2/S02, D3/S03, D4/S03, D4/S04, D5/S02, D5/S05 |
| 3 | Critical (≤7 days), no shortage | D2/S03, D4/S05 |
| 4 | Exactly 7 days — boundary edge case | D1/S04 (with shortage), D5/S03 (without shortage) |
| 5 | Critical stock + active shortage flag | D1/S01, D1/S04 |
| 6 | Healthy stock + active shortage flag | D1/S03 |
| 7 | Concern stock + active shortage flag | D1/S02 |
| 8 | Untracked stock (NULL qty) → N/A | D1/S05 |
| 9 | Negative stock (data error) → N/A | D2/S04 |
| 10 | Same drug, opposite risk at different sites | D3/S01 (21d, healthy) vs D3/S04 (5d, critical) |

---

## Data Sources

| Source | Type | Used For |
|---|---|---|
| Health Canada Drug Product Database (DPD) REST API | Real | Drug names, DINs, strengths, canonical units, ATC therapeutic class. Base URL: `https://health-products.canada.ca/api/drug/`. DIN lookup: `/drugproduct/?din=XXXXXXXX&type=json`. Therapeutic class: `/therapeuticclass/?id=<drug_code>&type=json` |
| Health Product Shortages Canada | Real — manual lookup | Shortage flags and tier levels. Site blocks automated fetching. Data sourced by hand from healthproductshortages.ca, labelled with lookup date 2026-11-11 |
| WHO ATC/DDD Index | Real — manual lookup | Defined Daily Doses used as baselines for avg daily usage simulation. Source: atcddd.fhi.no |
| Simulated | Synthetic | Stock levels, avg daily usage rates grounded in researched Canadian hospital baselines (see BUILD_LOG.md), site locations |

---

## Key Human Decisions Already Made (do not revisit without Dawson)

1. **Drop Medicaid SDUD** — US dataset is state-level quarterly aggregates, too coarse for per-site daily usage. Usage simulated from researched Canadian hospital baselines.
2. **Add `drug_alternatives` table** — Dawson's idea. Turns shortage tier from a static label into actionable decision support by showing whether substitutes are themselves compromised.
3. **MIOCHOL-E as the Tier 3 drug** — chosen over Stannous MAA Kit because it has an ATC code (enabling real alternatives lookup) and a longer active shortage.
4. **Manual shortage lookup** — healthproductshortages.ca blocks automated fetching. Data sourced by hand and labelled with the lookup date.
5. **SQLite over PostgreSQL** — chosen to satisfy the one-command run requirement. PostgreSQL requires a running server; SQLite is a file. GUI: DBeaver.
6. **One-command run via auto-seed** — `app.py` checks for `data/bdm.db` on startup and seeds it automatically if missing.
7. **drug_alternatives DINs hardcoded** — DPD REST API returned empty responses at time of seeding. 10 real Canadian DINs sourced manually on 2026-11-11 and baked into `data/seed.py`. Do not attempt to restore live API calls without verifying the DPD API is serving data again.
8. **avg_7d and avg_30d meaningfully different** — selected rows show 7d > 30d to simulate trending demand.
9. **All 25 inventory snapshot rows approved by Dawson** — values locked in. Do not change without Dawson's sign-off.

---

## Current State — End of Day 4 (2026-11-15)

**Complete:**
- `data/seed.py` — idempotent, runs cleanly, all 6 tables populated, view created, 471 POs seeded
- `requirements.txt`
- `.gitignore`
- All data designed, approved, and seeded
- `app.py` — Streamlit UI, Pieces 3–5 complete, verified working in browser
- Sidebar legend with colored dot swatches and plain-language operational descriptions
- Column headers cleaned up (no time window suffixes)
- Stale Tab 2 caption removed

**Run command:**
```
python3 -m streamlit run app.py
```
On first run, `app.py` auto-seeds the database if `data/bdm.db` is missing. Use `python3 -m streamlit` not `streamlit` directly — `streamlit` may not be on PATH depending on environment.

**Verified in browser (unfiltered, as of Day 6):**
- Tab 1 (Critical Alerts): 6 rows, sorted by days_of_supply ascending
- Tiles: Critical Items 6 | Shortage Flags 2 | Sites Affected 4 | Provinces Affected 4
- Acetylcholine Chloride rows show "[Tier 3]" badge and maroon (#8B0C0C) highlight
- Non-shortage critical rows highlighted orange (#E96A10C3) — bug fixed Day 5
- Geography sidebar filters cascade correctly and include all sites (Calgary now visible) — bug fixed Day 6
- Sidebar legend: Untracked dot now mid-grey (#5A5A5A), Healthy dot matches sidebar background (#2B2E31) — bug fixed Day 6
- "View procurement history for:" selectbox — pick any drug/site, shows avg lead time, avg unit cost, 5 most recent POs
- Procurement table columns: Order Date | Distributor | Qty on Hand | Days Since Last Order | Units Used | Qty Ordered | Unit Cost ($) | Days to Delivery | Status
- Days to Delivery shows "—" for in_transit orders; oldest visible row shows "—" for Days Since Last Order and Units Used
- Tab 2 (Full Inventory): all 25 rows, same geography filters, color-coded by alert level; untracked rows #3A3A3A
- Theme: #1F2123 background, #E6E7E8 text, #F4A982 warm peach accent (Dawson's final values)

**Current git branch:** `dev` — pushed to GitHub (all Day 4 work committed)
**Main branch:** not yet updated — merge dev → main before submission

**Final Full Inventory colors (Dawson's confirmed choices, as of 2026-11-15):**
- Critical + shortage: `#8B0C0C` (deep maroon)
- Critical (no shortage): `#E96A10C3` (orange)
- Concern: `#4A3800` (dark amber)
- Untracked/negative: `#2A2A2A` (grey)
- Healthy: no color (default background)

## Open Items for Next Session

### Remaining deliverables

1. **Piece 6 (stretch)** — Alternatives panel in the UI (show `drug_alternatives` data for each critical row — which substitutes are available, which are under their own shortage).
2. **Piece 7 (required)** — `writeup.md` explaining sources, what was simulated, data problems, and what's next. README. Final one-command run verification. Required deliverable per the brief.
3. **Merge dev → main** — the challenge reviewer will clone main. Do not merge until Piece 7 is done.
4. **ML forecasting vision (Dawson)** — `purchase_orders` table is the foundation. Future work: lead-time prediction, reorder-point optimization, demand forecast. Not in scope for this challenge.

---

## Important Notes

- The user's name is Dawson. Refer to design decisions as coming from Dawson where credited.
- The challenge contact is Trevor Tessier at BDM Healthware (Saskatoon, SK).
- Do not use emojis in responses.
- Keep responses concise and direct.
- Always ask Dawson rather than making assumptions — use the grill-me skill before writing code or making design choices.
- Always update `BUILD_LOG.md` at the end of a session and push to GitHub.
