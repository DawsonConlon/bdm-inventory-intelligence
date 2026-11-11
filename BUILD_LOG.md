# BDM Inventory Intelligence — Build Log

**Challenge:** Inventory Intelligence Candidate Build Challenge  
**Started:** 2026-11-10

---

## The Goal

Build a working mini version of BDM's inventory intelligence product using public data.  
Core question the tool must answer: **Which drugs, at which sites, have 7 days of supply or less?**

---

## Must-Have Capabilities

- [ ] Usage (units consumed per item per site — daily/weekly/monthly, transfers/reversals removed)
- [ ] Unit normalisation (one canonical dispensing unit per item, conversions stated)
- [ ] Quantity on hand (untracked/negative = "N/A", never zero)
- [ ] Days of supply (stock ÷ avg daily usage, flagged red at ≤7 days)
- [ ] Geography rollup (view by site, city, region/province)

## Stretch Capabilities

- [ ] Demand forecast (probabilistic 14-day forecast with quantiles, evaluated)
- [ ] Shortage signal (match public shortage feed, flag at-risk items)

---

## Deliverables Checklist

- [ ] Repo runs end to end in one command
- [ ] UI (Streamlit / web app / notebook) answering the 7-day question
- [ ] One-page write-up (sources, simulated parts, data problems, what's next)
- [ ] Ready for 20-minute walkthrough

---

## Data Architecture

Four relational tables:

1. **`sites`** — 5 hospital pharmacy locations across Canadian provinces (simulated, realistic names and cities)
2. **`drugs`** — 5 chosen drugs with DINs, strengths, canonical units, and shortage flags (Health Canada DPD + Health Product Shortages Canada)
3. **`inventory_snapshots`** — 25 rows (5 sites × 5 drugs): qty on hand, avg daily usage, days of supply, alert status (simulated stock, researched usage baselines)
4. **`drug_alternatives`** — therapeutic substitutes for each drug, with their own shortage status and system-wide stock (Health Canada DPD ATC codes + Health Product Shortages Canada API; stock simulated)

### Confirmed Drug List

| ID | Generic Name | Brand Name | DIN | Shortage | Tier | Notes |
|---|---|---|---|---|---|---|
| D1 | Acetylcholine Chloride | MIOCHOL-E | 02133326 | ✅ Active | Tier 3 | Ophthalmic surgical (cataract); manufacturing disruption; runs to 2027-02-05. ATC: S01EB. Sourced manually from healthproductshortages.ca/shortage/272933 on 2026-11-11 |
| D2 | Hydromorphone | APO-Hydromorphone | TBD | ⚠️ Verify | TBD | March 2026 shortage report found; current status to be confirmed manually on healthproductshortages.ca |
| D3 | Atorvastatin | Lipitor | 02230711 | ❌ None | — | Common statin, no active shortage |
| D4 | Insulin Glargine | Lantus | 02240292 | ❌ None | — | High daily volume, no active shortage |
| D5 | Metoprolol | Lopressor | 00648051 | ❌ None | — | Common cardiac drug, no active shortage |

### Data Sources

| Source | Type | Used For |
|---|---|---|
| Health Canada Drug Product Database (DPD) | Real — REST API | Drug names, DINs, strengths, canonical units, ATC therapeutic class |
| Health Product Shortages Canada | Real — manual lookup (site blocks automated access) | Shortage flags and tier levels sourced by hand, labelled with lookup date |
| Simulated — researched baselines | Synthetic | Stock levels, avg daily usage rates, site locations |

### Situations Demonstrated in the Data

| # | Situation | Status |
|---|---|---|
| 1 | Healthy stock (>14 days), no flags | 🟢 |
| 2 | Concern (8–14 days), no flags | 🟡 |
| 3 | Critical (≤7 days), no shortage | 🔴 |
| 4 | Exactly 7 days — boundary edge case | 🔴 |
| 5 | Critical stock + active shortage flag | 🔴 ⚠️ |
| 6 | Healthy stock + active shortage flag | 🟢 ⚠️ |
| 7 | Concern stock + active shortage flag | 🟡 ⚠️ |
| 8 | Untracked stock (NULL qty) → N/A | ⚪ |
| 9 | Negative stock (data error) → N/A | ⚪ |
| 10 | Same drug, opposite risk at different sites (geography rollup) | 🟢↔🔴 |

---

## Key Design Decisions

### Human-Driven Decisions

**Decision: Drop the Medicaid SDUD dataset and build a synthetic usage dataset instead**
- Proposed by: Dawson
- The US Medicaid State Drug Utilization Data was initially identified as a usage source, but after reviewing it Dawson flagged that it is state-level quarterly aggregates — not granular enough to calculate per-site, per-drug daily usage. The decision was made to simulate usage rates instead, grounded in researched real-world Canadian hospital consumption baselines for the five chosen drugs. This is explicitly permitted by the challenge brief ("simulate anything that isn't published").

**Decision: Add a `drug_alternatives` table as a fourth relational table**
- Proposed by: Dawson
- Dawson identified that the shortage tier flags (Tier 1–3) are more meaningful if the tool also shows whether the alternatives for a critically low drug are themselves available or at risk. This table pulls real therapeutic class data (ATC codes) from the Health Canada DPD to identify substitutes, checks each substitute against the Health Product Shortages Canada API for its own shortage status, and simulates system-wide stock for each alternative. This turns the shortage tier from a static label into actionable decision support — e.g. Vancouver is critically low on Pip-Taz (Tier 2) and both of its alternatives are also compromised.

---

## Daily Log

---

### Day 1 — 2026-11-10

#### Planned
- Read and understand the challenge brief
- Create this tracking log
- Decide on data sources
- Decide on tech stack
- Sketch the architecture (data pipeline → warehouse → UI)
- Begin data sourcing

#### Accomplished
- Read the challenge brief (BDM Inventory Intelligence Challenge.pdf)
- Created BUILD_LOG.md and BIBLIOGRAPHY.md
- GitHub repository created: github.com/DawsonConlon/bdm-inventory-intelligence (main branch)
- Researched and evaluated all data sources mentioned in the brief (Medicaid SDUD, Health Canada DPD, openFDA NDC, Health Product Shortages Canada)
- Decided on final data sources and synthetic data strategy
- Designed full 4-table relational data architecture (sites, drugs, inventory_snapshots, drug_alternatives)
- Defined the final deliverable view (v_inventory_dashboard) joining all 4 tables
- Identified all 10 showcase situations to demonstrate in the tool
- Defined 5 sites, 5 drugs, and all 25 inventory snapshot scenarios with alert levels
- Confirmed Health Canada DPD REST API works — 5-call chain per DIN documented and verified
- Identified that Health Product Shortages Canada API requires a free account (blocked to automated fetches without auth)
- Confirmed ATC codes to use for all 5 drugs and their 2 alternatives each
- Created BIBLIOGRAPHY.md with APA-formatted citations for all data sources

#### Decisions Made
- Drop Medicaid SDUD → use simulated usage with researched baselines (Dawson)
- Add `drug_alternatives` table powered by Health Canada DPD ATC codes (Dawson)
- Health Product Shortages Canada: decision pending — register free account (Option A), scrape public search (Option B), or simulate with manually sourced flags (Option C)
- Negative and untracked stock → N/A per challenge brief

#### Blockers / Open Questions
- ~~Health Product Shortages Canada API access method~~ — resolved: manual lookup, labelled with date
- ~~Tier 3 shortage drug selection~~ — resolved: MIOCHOL-E / Acetylcholine Chloride (DIN 02133326)
- Hydromorphone shortage status still needs manual verification on healthproductshortages.ca
- Tech stack not yet confirmed (Python + Streamlit most likely)
- Avg daily usage baselines for the 5 chosen drugs not yet researched
- Architecture diagram not yet sketched

---

### Day 2 — 2026-11-11

#### Planned
- Confirm Tier 3 shortage drug
- Finalise shortage data approach
- Confirm tech stack
- Decide on database service
- Begin writing code

#### Accomplished
- Swapped Tier 3 drug from Stannous MAA Kit → MIOCHOL-E (Acetylcholine Chloride, DIN 02133326) — better choice because it has an ATC code (S01EB) enabling real alternatives lookup and has a longer active shortage (to 2027-02-05)
- Confirmed shortage data approach: manual lookup at healthproductshortages.ca, flags hardcoded with lookup date 2026-11-11
- Confirmed tech stack: Python + Streamlit + Plotly, run with `streamlit run app.py`
- Produced full ERD diagram showing all 4 tables and foreign key relationships
- Produced prototype query result mockup showing the 7-day alert view
- Identified that SQL Workbench does not support SQLite — discussed DBeaver and DB Browser for SQLite as alternatives, or switching to PostgreSQL
- Created HANDOFF.md to bring a new session up to speed

#### Decisions Made
- MIOCHOL-E selected as Tier 3 shortage drug (Dawson)
- Shortage data: manual lookup approach confirmed
- Tech stack: Python + Streamlit confirmed
- Repo structure defined

#### Blockers / Open Questions
- **Database service not yet decided** — SQLite + DBeaver vs PostgreSQL. This is the first decision for the next session before any code is written.
- Hydromorphone shortage status still needs manual verification
- Avg daily usage baselines for the 5 drugs not yet researched

---

<!-- Add new days below this line in the same format -->
