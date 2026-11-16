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
| D2 | Hydromorphone HCl | APO-Hydromorphone | 02364123 | ❌ None | — | Last shortage resolved 2017-12-14 (Report 26163). No active shortage. ATC: N02AA |
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

#### Accomplishments (continued — same session)
- Wrote `data/seed.py` — idempotent seed script creating all 4 tables, 25 approved inventory rows, 10 drug alternatives, and the `v_inventory_dashboard` view
- Wrote `requirements.txt`
- Created `.gitignore` (excludes `data/bdm.db`, `.DS_Store`, `__pycache__`)
- Confirmed database seeds cleanly: `python3 data/seed.py` runs in one step, all 25 rows and all 10 alternatives verified
- Health Canada DPD API investigated — returns empty responses for all queries (DIN lookups and ingredient searches). Alternatives DINs sourced manually instead. Issue noted in code.
- Drug alternatives data: 10 real Canadian DINs hardcoded with sourcing date 2026-11-11

#### Piece 2 Complete
Seed script is working. `streamlit run app.py` will auto-call `data/seed.py` on first run if `data/bdm.db` is missing. No code exists for `app.py` yet.

---

#### Accomplishments (continued — same session, Piece 3)
- Wrote `app.py` — Streamlit UI answering the core 7-day question
- Auto-seed on startup: `app.py` checks for `data/bdm.db` and calls `data.seed.seed()` if missing; one-command run requirement fully satisfied
- 4 summary metric tiles: Critical Items / Shortage Flags / Sites Affected / Provinces Affected
- Cascading geography sidebar filters: Region → Province → City → Site (each narrows the next)
- Alert table with `pandas.Styler` row coloring: shortage rows highlighted, non-shortage rows white
- Drug shortage tier badge: "[Tier 3]" appended to drug name in table when `shortage_active == 1`
- Created `.claude/launch.json` for browser preview via `python3 -m streamlit run app.py`

#### UI Iteration 1 — Styling Pass
- Added `.streamlit/config.toml`: final theme — `backgroundColor: #1F2123`, `secondaryBackgroundColor: #2B2E31`, `textColor: #E6E7E8`, `primaryColor: #F4A982` (warm peach accent)
- Shortage row highlight finalised to `#90330B` (deep burnt orange — Dawson's choice)

#### Piece 3 Complete — Verified in browser
Unfiltered view confirmed:
- **6 critical rows** displayed, sorted ascending by days_of_supply (4.0 → 5.0 → 5.0 → 6.0 → 7.0 → 7.0)
- **Tiles:** Critical Items: 6 | Shortage Flags: 2 | Sites Affected: 4 | Provinces Affected: 4
- **Shortage rows** (both Acetylcholine Chloride) highlighted pink with [Tier 3] badge
- **Geography filters** cascade correctly — Province/City/Site dropdowns update based on upstream selections

#### Drug Alternatives — Notable Flags
- **Carbachol** (D1 alt): DIN 00042544. Simulated Tier 2 shortage, availability = Limited. Makes the MIOCHOL-E situation actionable — the primary drug is Tier 3 shortage AND its first alternative is also compromised.
- **Pilocarpine** (D1 alt): DIN 02213044. Availability = Uncertain (may be discontinued in DPD).
- **Insulin Detemir** (D4 alt): DIN 02271842. Availability = Limited (anticipated discontinuation Dec 2025).
- All other alternatives: Available, no shortage.

#### Decisions Made (continued)
- **Database service: SQLite** — chosen over PostgreSQL to satisfy the one-command run requirement. PostgreSQL would require a running server before `streamlit run app.py` could work, making setup harder for the reviewer. SQLite is a single file; the seed script creates and populates it on first run, so the entire stack boots in one command. GUI query tool: DBeaver (free, supports SQLite natively, full workbench experience).
- **One-command run confirmed:** `app.py` will auto-call the seed script on startup if the database file does not exist. Reviewer clones and runs `streamlit run app.py` — nothing else required.
- **drug_alternatives sourcing:** Try the Health Canada DPD API live at seed time first. If the API causes unresolvable issues, escalate to Dawson before hardcoding.
- **avg_daily_usage_7d vs avg_daily_usage_30d:** Meaningfully different on selected rows to simulate trending demand (7d > 30d = usage trending up).
- **Hydromorphone shortage verified:** Last shortage resolved 2017-12-14 (Report ID 26163). No active shortage. DIN confirmed: 02364123. ATC: N02AA. D2 is a clean drug.
- **All 25 inventory snapshot rows approved by Dawson** — specific qty_on_hand and avg_daily_usage values locked in. All 10 showcase situations confirmed covered. See full table below.

#### Blockers / Open Questions
- ~~Hydromorphone shortage status~~ — resolved (see above)
- ~~Avg daily usage baselines~~ — researched and documented. See Avg Daily Usage Baselines section.
- ~~Full 25-row inventory data~~ — approved. See Approved Inventory Snapshot Data section.
- **drug_alternatives table data** — real alternatives per ATC class not yet researched. To be fetched via Health Canada DPD API during seed script development. Fallback: hardcode after Dawson approval.
- ~~Seed script~~ — complete. See above.
- **`app.py` not yet written** — next phase (Piece 3).

---

---

## Approved Inventory Snapshot Data

All 25 rows approved by Dawson on 2026-11-11. Rows marked * have avg_7d diverging from avg_30d (simulated trending demand).

### D1 — Acetylcholine Chloride (vials) — Active Shortage, Tier 3

| Site | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert | Situation |
|---|---|---|---|---|---|---|
| S01 Saskatoon | 8 | 7* | 32 | 4.0 | critical | #5: critical + shortage |
| S02 Calgary | 6 | 5* | 72 | 12.0 | concern | #7: concern + shortage |
| S03 Vancouver | 9 | 9 | 180 | 20.0 | none | #6: healthy + shortage |
| S04 Ottawa | 7 | 7 | 49 | 7.0 | critical | #4+5: exactly 7d + shortage |
| S05 Halifax | 4 | 4 | NULL | N/A | untracked | #8: untracked stock |

### D2 — Hydromorphone HCl (2mg tablets) — No Shortage

| Site | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert | Situation |
|---|---|---|---|---|---|---|
| S01 Saskatoon | 220 | 200* | 7700 | 35.0 | none | #1: healthy |
| S02 Calgary | 180 | 170 | 1980 | 11.0 | concern | #2: concern |
| S03 Vancouver | 150 | 140* | 750 | 5.0 | critical | #3: critical, no shortage |
| S04 Ottawa | 160 | 155 | -40 | N/A | untracked | #9: negative stock |
| S05 Halifax | 120 | 115 | 2400 | 20.0 | none | #1: healthy |

### D3 — Atorvastatin (tablets) — No Shortage

| Site | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert | Situation |
|---|---|---|---|---|---|---|
| S01 Saskatoon | 90 | 85 | 1890 | 21.0 | none | #10: healthy side of geography split |
| S02 Calgary | 80 | 78 | 1200 | 15.0 | none | #1: healthy |
| S03 Vancouver | 100 | 95 | 1000 | 10.0 | concern | #2: concern |
| S04 Ottawa | 70 | 68 | 350 | 5.0 | critical | #10: critical side of geography split |
| S05 Halifax | 65 | 60 | 975 | 15.0 | none | #1: healthy |

### D4 — Insulin Glargine (IU) — No Shortage

| Site | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert | Situation |
|---|---|---|---|---|---|---|
| S01 Saskatoon | 1600 | 1500* | 36000 | 22.5 | none | #1: healthy |
| S02 Calgary | 1800 | 1700 | 27000 | 15.0 | none | #1: healthy |
| S03 Vancouver | 2000 | 1900 | 18000 | 9.0 | concern | #2: concern |
| S04 Ottawa | 1400 | 1400 | 14000 | 10.0 | concern | #2: concern |
| S05 Halifax | 1200 | 1100* | 7200 | 6.0 | critical | #3: critical |

### D5 — Metoprolol (tablets) — No Shortage

| Site | avg_7d | avg_30d | qty_on_hand | days_of_supply | alert | Situation |
|---|---|---|---|---|---|---|
| S01 Saskatoon | 150 | 145 | 2250 | 15.0 | none | #1: healthy |
| S02 Calgary | 160 | 155 | 1920 | 12.0 | concern | #2: concern |
| S03 Vancouver | 140 | 130* | 980 | 7.0 | critical | #4: exactly 7d, no shortage |
| S04 Ottawa | 120 | 115 | 1800 | 15.0 | none | #1: healthy |
| S05 Halifax | 100 | 95 | 1200 | 12.0 | concern | #2: concern |

---

## Avg Daily Usage Baselines

Researched 2026-11-11. Sources: WHO ATC/DDD Index, Canadian Journal of Hospital Pharmacy, published Canadian hospital utilization studies. Assumptions based on a large tertiary hospital (~400–600 beds).

| Drug | Unit | Daily range per site | Basis |
|---|---|---|---|
| Acetylcholine Chloride | vials (1 per cataract case) | 2–10 | Cataract OR throughput; high-volume ophthalmology: 8–10/day, lower-volume: 2–4/day |
| Hydromorphone HCl 2mg | tablets | 100–300 | 65% inpatient opioid rate (Canadian tertiary hospitals); PRN orders rarely maxed; ~8–15 mg/day per patient |
| Atorvastatin | tablets | 60–120 | ~20% of inpatients on a statin; continued from home medications; 1 tablet/day |
| Insulin Glargine | IU | 1,200–2,000 | ~10% of inpatients on glargine × WHO DDD 40 IU; ~1–2 vials/day or 4–7 SoloStar pens/day |
| Metoprolol | tablets | 80–180 | ~15% of inpatients on beta-blocker; typical dose 50 mg bid = 2 tablets/day |

**Note on Acetylcholine Chloride:** No WHO DDD assigned — it is a single-use surgical drug, not a maintenance medication. Volume is driven by ophthalmology OR throughput, not patient days.

**Sources:**
- WHO ATC/DDD Index (N02AA03, C10AA05, C07AB02, A10AE04): https://atcddd.fhi.no/atc_ddd_index/
- Inpatient opioid prescribing rate (65%, Canadian tertiary hospitals): https://ifp.nyu.edu/2024/journal-article-abstracts/opioid_prescribing_among_hospitalized_patients_in-4-aspx/
- Hydromorphone as most common inpatient opioid (CJHP, Toronto): https://www.cjhp-online.ca/index.php/cjhp/article/view/1387
- Post-event statin and beta-blocker rates (Ontario, PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC2700711/table/T3
- Cataract surgery OR throughput: https://pmc.ncbi.nlm.nih.gov/articles/PMC4918740/
- Canadian hospital diabetes/insulin utilization (CJHT): https://www.canjhealthtechnol.ca/index.php/cjht/article/download/AU0001/3545

---

---

#### Piece 5 — Distributor + Procurement History

**Data architecture additions:**
- Added `distributors` table (3 rows): McKesson Canada (National), Cardinal Health Canada (National), Innomar Strategies (Specialty)
- Added `purchase_orders` table (471 rows): 6 months of procurement history (May–Nov 2026) generated programmatically with fixed random seed 42 for reproducibility
- Order frequency: weekly for high-volume drugs (Hydromorphone, Insulin Glargine); bi-weekly for others (Acetylcholine, Atorvastatin, Metoprolol)
- Lead times vary by distributor: McKesson 2–5 days, Cardinal 3–7 days, Innomar 1–4 days (specialty/fastest)
- Innomar is primary distributor for Acetylcholine (D1, shortage drug); Cardinal primary for Insulin Glargine; McKesson primary for all others with regional override for BC/NS sites to Cardinal
- Unit costs vary by drug: Acetylcholine $48–62/vial, Hydromorphone $0.52–0.78/tablet, Atorvastatin $0.28–0.52/tablet, Insulin Glargine $0.052–0.068/IU, Metoprolol $0.18–0.32/tablet
- Strategic purpose: procurement history is the foundation for future ML reorder-point and lead-time prediction models (Dawson's vision)

**UI additions:**
- Tab 1 (Critical Alerts): "View procurement history for:" selectbox dropdown below the table — pick any drug/site combo, procurement panel appears below
- Procurement panel shows: avg lead time, avg unit cost (delivered orders only), total orders (6 months), and 5 most recent orders with distributor name, qty, cost, lead days, and status
- `load_purchase_orders()` and `load_distributors()` added as `@st.cache_data` functions

**UX fix (same session):**
- Initial implementation used Streamlit `on_select="rerun"` row selection which required clicking a small checkbox at the far left of each row — not intuitive
- Replaced with a labeled `st.selectbox` below the table (Dawson flagged the issue)

**Deprecation fix (same session):**
- Streamlit 2.x deprecated `use_container_width=True` in favour of `width="stretch"`
- Replaced all 3 occurrences in `app.py`

---

### Day 3 — 2026-11-14

#### Planned
- Push dev branch to GitHub
- Review all features against BDM brief requirements
- Plan Full Inventory legend and highlight clarification

#### Accomplished
- Pushed dev branch to GitHub (Dawson — first remote push)
- Reviewed full feature checklist against brief: all 5 must-haves confirmed complete, shortage signal partially complete, demand forecast not started, `writeup.md` not started
- Dawson updated Full Inventory alert colors in `app.py`:
  - Critical + shortage: `#8B0C0C` (deep maroon)
  - Critical (no shortage): `#0980DB78` (semi-transparent blue — under review)
  - Concern: `#4A3800` unchanged
  - Untracked: `#2A2A2A` unchanged
- Dawson added second legend line to Tab 1: "Non highlighted rows have 7 days or less of supplies."
- Identified that the existing caption in Tab 2 is stale (text does not match current colors) and that the legend needs plain-language descriptions of what each alert level means operationally, not just color names
- Plan agreed: replace caption with a proper visual legend (colored swatches + plain-language meaning per tier)

#### Decisions Made
- Legend redesign approach agreed: colored swatches + plain-language operational meaning per tier (not just color names)
- Full Inventory colors still being finalized by Dawson — `#0980DB78` for critical (no shortage) is under review

#### Open Questions
- Final color for critical (no shortage) rows — `#0980DB78` intentional or still experimenting?
- Legend implementation deferred to next session pending Dawson's color confirmation

---

### Day 4 — 2026-11-15

#### Planned
- Finalize Full Inventory highlight colors
- Implement sidebar legend with colored swatches and plain-language descriptions
- Clean up column headers
- Remove stale Tab 2 caption

#### Accomplished
- **Color finalization (Dawson):**
  - Critical + shortage: `#8B0C0C` (deep maroon) — confirmed final
  - Critical (no shortage): changed from `#0980DB78` (semi-transparent blue) to `#E96A10C3` (orange) — Dawson flagged blue was visually indistinguishable from "healthy" in a clinical context
  - Concern: `#4A3800` unchanged
  - Untracked/negative: `#2A2A2A` unchanged
- **Sidebar legend implemented** — replaced the stale text caption in Tab 2 with a sidebar legend containing colored dot swatches and plain-language operational descriptions for each alert tier (Critical + shortage, Critical, Concern, Untracked/N/A, Healthy)
- **Column headers cleaned up** — removed time window suffixes: `Daily Usage (7d)` → `Daily Usage`, `Weekly Usage (7d)` → `Weekly Usage`, `Monthly Usage (30d)` → `Monthly Usage` across both tabs (8 occurrences)
- **Stale Tab 2 caption removed** — the old `st.caption("Critical + shortage: dark orange | ...")` line was inaccurate and superseded by the sidebar legend
- All changes committed and pushed to dev branch

#### Decisions Made
- Orange (`#E96A10C3`) for critical rows without a shortage — better clinical intuition than blue
- Sidebar legend placement (below geography filters) — Dawson's preferred location

#### Open Questions
- None — Day 4 UI work complete

---

### Day 5 — 2026-11-15 (continued)

#### Planned
- Fix Tab 1 critical row highlight: non-shortage critical rows should be orange, matching the legend

#### Accomplished
- **Tab 1 highlight bug fixed:** `highlight_critical()` was only applying maroon (`#8B0C0C`) to shortage rows and no color to all other critical rows. Updated the else branch from `""` to `"#E96A10C3"` so non-shortage critical rows now render orange, matching the sidebar legend and Tab 2 behavior.

#### Decisions Made
- No new decisions — fix aligns Tab 1 with colors already confirmed by Dawson on Day 4

#### Open Questions
- None

---

### Day 6 — 2026-11-16

#### Planned
- Fix geography filter missing Calgary (Bug 1)
- Fix Healthy / Untracked legend colors indistinguishable (Bug 2)

#### Accomplished

**Bug 1 — Geography filter missing Calgary — Fixed:**
Root cause: the sidebar cascading dropdowns (Region → Province → City → Site) were built by filtering the `critical` DataFrame at each step. Calgary/S02 has no critical items, so it never entered the option lists — meaning Tab 2 (Full Inventory) also could not be filtered to Calgary.
Fix: introduced a separate `filter_base` DataFrame (copy of full `df`) to build all four dropdown option lists. The cascade narrows `filter_base` at each level so the options still update contextually, but all 25 rows are eligible. The user's selections are then applied independently to both `critical` and `full` afterward. Any site with zero critical items is now visible in the filters.

**Bug 2 — Healthy / Untracked legend colors — Fixed:**
Root cause: both legend dots were near-black on a near-black sidebar background (`#2A2A2A` / `#3a3a3a`), visually indistinguishable.
Fix:
- Untracked/N/A legend dot: `#2A2A2A` → `#5A5A5A` with `#888` border (clearly visible mid-grey — signals "data problem")
- Healthy legend dot: `#3a3a3a` → `#2B2E31` with `#444` border (matches sidebar background — signals "nothing notable")
- Tab 2 untracked row highlight: `#2A2A2A` → `#3A3A3A` (more distinguishable from the `#1F2123` default row background)

#### Decisions Made
- Filter options built from full dataset (`df`), not critical subset — Dawson confirmed approach before implementation
- Untracked color in legend and table made visibly grey; Healthy blends into sidebar background (Dawson's review pending commit)

#### Open Questions
- None — both bugs resolved

---

#### Feature — Procurement History: Qty on Hand, Days Since Last Order, Units Used

**Data architecture:**
- Added `qty_on_hand_at_order INTEGER` column to `purchase_orders` table in `data/seed.py`
- Added `_SNAPSHOT_QTY` lookup dict (mirrors `inventory_snapshots` qty values; `None` for untracked/negative sites D1/S05 and D2/S04)
- Backfill logic: forward walk from opening stock of `avg_daily × order_freq × 2` (2 order cycles). For each order, record current stock, then advance: `running_qty = running_qty + qty_ordered - days_to_next_order × avg_daily`. Forward walk chosen over backwards walk because critically low snapshot items (e.g. D1/S01 at 32 vials) caused the backwards walk to immediately go negative and clamp to zero.
- 471 rows re-seeded cleanly. Zero counts verified: none.

**UI additions (Tab 1 — procurement panel):**
- `Qty on Hand` — stock at time of order, formatted with commas; "—" for untracked/negative sites
- `Days Since Last Order` — integer days between this order and the prior one; "—" for the oldest visible row
- `Units Used` — `qty_on_hand[prev] + qty_ordered[prev] − qty_on_hand[current]`, formatted with commas; "—" for oldest visible row or untracked sites
- `Qty Ordered` — now formatted with commas (was plain integer)
- `Days to Delivery` — renamed from "Lead (days)"; shows "—" for in_transit orders since delivery has not occurred yet

**Column order in final table:**
Order Date | Distributor | Qty on Hand | Days Since Last Order | Units Used | Qty Ordered | Unit Cost ($) | Days to Delivery | Status

**Decisions made:**
- Forward walk over backwards walk — Dawson confirmed after seeing backwards walk produce all-zero results for critically low items
- "Days to Delivery" rename and "—" for in_transit — Dawson's direction
- Column names approved by Dawson before implementation

**Pushed to GitHub dev branch by Dawson — 2026-11-16**

---

#### Decision — Remove `drug_alternatives` table (2026-11-16)

Dawson decided to descope the drug_alternatives feature from the submission version of the tool. The table was designed, seeded with 10 real Canadian DINs, and documented, but was never wired into the UI. All `drug_alternatives` code has been removed from `data/seed.py`:
- `DROP TABLE IF EXISTS drug_alternatives` removed from schema
- `CREATE TABLE drug_alternatives` block removed
- `_ALTERNATIVES` data list removed
- `fetch_drug_alternatives()` function removed
- Call to `fetch_drug_alternatives(conn)` removed from `seed()`

The database now seeds 5 tables: distributors, sites, drugs, inventory_snapshots, purchase_orders.

The underlying idea remains valid and Dawson intends to implement it in a future version: showing whether substitute drugs are themselves under shortage or supply constraint turns the shortage tier from a static label into actionable decision support. The ATC codes are still stored on the `drugs` table, which will enable this lookup when the feature is revisited.

---

## Future Plans

### Live Shortage Tier Data — Health Canada API Integration

The current tool hardcodes shortage tier values (e.g. Tier 3 for Acetylcholine Chloride) sourced manually from Health Product Shortages Canada on 2026-11-11. The plan is to replace these static values with live data pulled directly from the Health Canada Drug Shortages API.

**API source:** Health Product Shortages Canada — https://www.healthproductshortages.ca/api/

The API supports querying by DIN, drug name, and shortage status. A production implementation would call this API at app load time (or on a nightly scheduled job) to fetch the current shortage tier and status for each drug in the database, then store the result in a `shortage_cache` table with a `fetched_at` timestamp. The UI would display the live tier label alongside how recently the data was refreshed.

The DINs are already stored in the `drugs` table, so the lookup key is in place. The only remaining step is authenticated API access — Health Canada's API blocks unauthenticated automated requests, but a free account or API key issued to a healthcare organization would bypass this restriction.

<!-- Add new days below this line in the same format -->
