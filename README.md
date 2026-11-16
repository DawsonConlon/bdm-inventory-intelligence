# BDM Inventory Intelligence

A web-based inventory decision-support tool that answers one question: **which drugs, at which sites, have seven days of supply or less?**

Built with Streamlit and SQLite. Designed for hospital pharmacy environments where supply disruptions carry direct patient-care risk.

---

## What It Does

- Flags drugs at critical supply levels (7 days or less) across multiple hospital sites
- Surfaces active Health Canada drug shortages alongside inventory alerts
- Shows procurement history per drug-site pair with derived consumption metrics
- Filters by region, province, city, or individual site
- Displays a full inventory view across all alert levels

---

## Running Locally

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
streamlit run app.py
```

The database is created automatically on first run. No setup required.

---

## Tech Stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| Database | SQLite |
| Data | Pandas |
| Seed data | Python (data/seed.py) |

---

## Data

All inventory quantities, purchase order history, usage rates, and shortage flags are simulated. Drug names and classifications are drawn from the Health Canada Drug Product Database. Daily usage rates are grounded in WHO Defined Daily Dose (DDD) values scaled to a plausible Canadian hospital inpatient volume. Shortage tier definitions follow Health Canada classifications (Tier 1 Manageable, Tier 2 Serious, Tier 3 Critical).

Consumption between orders is derived from procurement events using:

```
units used = qty on hand at previous order + qty ordered − qty on hand at current order
```

---

## Deployment

Deployed on Streamlit Cloud. The app auto-reseeds the database on first launch. Because the Streamlit Cloud filesystem is read-only, the database is written to `/tmp` when the `data/` directory is not writable.

---

## Future Plans

- Live shortage tier data via the Health Canada Health Product Shortages API (`healthproductshortages.ca/api/`)
- Integration with live pharmacy information system data feeds
- Alert notifications for newly flagged critical items

---

## Sources

- Health Canada Drug Product Database — canada.ca
- Health Canada Health Product Shortages — healthproductshortages.ca
- WHO ATC/DDD Index — atcddd.fhi.no
- Canadian Journal of Hospital Pharmacy (2016) — opioid prescribing in Canadian tertiary care hospitals
- Tu et al. (2009) — statin and beta-blocker prescribing rates in Ontario
- Schlenker et al. (2016) — cataract surgery volume and OR throughput benchmarks

Full citations in [BIBLIOGRAPHY.md](BIBLIOGRAPHY.md).
