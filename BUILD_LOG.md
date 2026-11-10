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
- Created BUILD_LOG.md

#### Decisions Made
*(to be filled in as decisions are confirmed)*

#### Blockers / Open Questions
*(to be filled in)*

---

<!-- Add new days below this line in the same format -->
