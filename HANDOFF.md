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
- `BUILD_LOG.md` — daily progress log (includes all approved data tables and usage baselines)
- `BIBLIOGRAPHY.md` — APA-formatted data source citations
- `HANDOFF.md` — this file

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

## Database Design — 4 Tables

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

Therapeutic substitutes for each drug. DINs and ATC class data from Health Canada DPD. Shortage status manually sourced. Stock simulated. **Data not yet populated — to be fetched via Health Canada DPD API during seed script development. If the API causes unresolvable issues, escalate to Dawson before hardcoding.**

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
7. **drug_alternatives via DPD API** — seed script will call the Health Canada DPD API live to fetch alternatives. If unresolvable, escalate to Dawson before hardcoding.
8. **avg_7d and avg_30d meaningfully different** — selected rows show 7d > 30d to simulate trending demand.
9. **All 25 inventory snapshot rows approved by Dawson** — values locked in. Do not change without Dawson's sign-off.

---

## Open Items for Next Session

1. **Write `data/seed.py`** — creates all 4 tables, inserts all approved data, creates `v_inventory_dashboard` view. Attempts to fetch drug_alternatives via Health Canada DPD API. This is the first file to write.
2. **Write `app.py`** — Streamlit UI with auto-seed on startup, 7-day alert view, geography filters.
3. **`drug_alternatives` data** — not yet populated. Seed script will attempt DPD API; escalate to Dawson if issues arise.

---

## Important Notes

- The user's name is Dawson. Refer to design decisions as coming from Dawson where credited.
- The challenge contact is Trevor Tessier at BDM Healthware (Saskatoon, SK).
- Do not use emojis in responses.
- Keep responses concise and direct.
- Always ask Dawson rather than making assumptions — use the grill-me skill before writing code or making design choices.
- Always update `BUILD_LOG.md` at the end of a session and push to GitHub.
