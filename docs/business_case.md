# Business Case and Value Measurement

## Problem

Demand planning currently relies on spreadsheets and static trailing averages. Forecasts do not adequately account for promotions, seasonality, weather, regional differences, supplier lead-time variability or supply constraints, so planners either over-order (tying up working capital and increasing markdown risk) or under-order (causing stock-outs and lost sales), and spend disproportionate manual effort chasing exceptions rather than working from a governed, auditable recommendation.

## Stakeholder personas

| Persona | What they need from this platform | Primary dashboard pages |
|---|---|---|
| Demand Planner | A trustworthy forecast and a prioritised list of exceptions, not a blank spreadsheet to rebuild weekly | Demand Forecast Accuracy, Replenishment Recommendations |
| Inventory Analyst | Early warning on stock-outs and excess stock, by category and location | Inventory Health, Stock-Out Risk |
| Supply Chain Manager | Supplier accountability evidence and network-wide performance | Supplier Performance, Executive Overview |
| Category Manager | Evidence-based read on whether promotions delivered the uplift vendors proposed | Promotion Impact |
| Data/Model Governance Lead | Confidence that the data feeding every number is checked, and that models are monitored and change-controlled | Data Quality and Model Monitoring, `governance/` |
| Executive Sponsor | A five-minute read on whether targets are being hit and what it is worth | Executive Overview |

## Current-state pain points

Forecasts are rebuilt manually in spreadsheets with no consistent methodology across categories; there is no systematic way to size safety stock against actual observed lead-time variability; supplier performance is tracked informally and inconsistently; promotion uplift is assumed rather than measured; and there is no standing view of data quality, so errors are found downstream rather than caught at the source.

## Target outcomes

| Outcome | Baseline (dev-scale run, seed 42) | Target | Measurement |
|---|---:|---:|---|
| Stock-out rate | 0.63% of store-SKU-days | 10-20% relative reduction (→ ~0.50-0.57%) | store-SKU-days with unmet demand ÷ total store-SKU-days |
| Excess inventory rate | 15.8% of store inventory positions | 8-15% relative reduction (→ ~13.4-14.5%) | share of store inventory positions with days-of-supply > 6 |
| Forecast accuracy (WMAPE, store-SKU grain) | 15.48% (4-week moving average) | 10% relative improvement target; 6.6% achieved by the gradient-boosted champion in this build (WMAPE 14.46%), with a further-improvement roadmap in the model card | weighted mean absolute percentage error on an 8-week holdout |
| Forecast accuracy (category grain) | 7.92% (moving average) | gradient-boosted bottom-up already reaches 7.09% (10.5% relative improvement) - the target is met at category and total grain today | same measure, category/total roll-up |
| Inventory turnover | ~94x/year (fast-turn grocery/FMCG assortment) | 5% relative improvement (→ ~98x) | annualised COGS ÷ average inventory value |
| Manual planning effort | 4.25% of replenishment decisions require planner override | 20% reduction in override volume | share of replenishment decisions requiring planner override |
| Supplier and warehouse performance | 22.9% of purchase orders arrive late overall (supplier-level range ~14.5%-31.5%) | move every supplier out of the "Critical" band | on-time delivery rate, fill rate, predicted late-delivery risk |

Baselines above are genuine outputs of the pipeline's holdout evaluation and business-KPI computation at the default `dev` scale and seed - not assumed figures. Re-run `python -m supply_chain.pipeline --scale dev --seed 42` and read `artifacts/run_summary.json` to reproduce them exactly; a different seed or `--scale full` will shift the exact numbers while preserving the same pattern (store-SKU forecasts are hardest, category/total roll-ups are easiest; slower suppliers cluster in imported, longer-lead-time categories). Targets reflect a standard, achievable first-year improvement band for a retailer moving from static averages to a governed forecasting and inventory platform, consistent with published industry benchmarks for demand-planning modernisation programs. The store-SKU-level forecast target is presented honestly as partially achieved rather than inflated - see the model card's retraining and improvement roadmap for how the remaining gap is closed.

## Indicative financial value

At dev scale (8 stores, 24 SKUs) the pipeline computes an annualised cost of goods sold of approximately **$2.04m** and an annualised lost-sales estimate from observed stock-outs of approximately **$14.3k** (`business_kpis.annualised_cogs_estimate_aud`, `business_kpis.annual_lost_sales_estimate_aud`). These figures scale roughly linearly with store and SKU count - at `--scale full` (140 stores) the same computation would be expected to produce a COGS base in the tens of millions and a proportionally larger lost-sales exposure, which is the more representative number for an actual investment decision:

- **Stock-out reduction**: a 10-20% relative reduction in stock-out incidence, applied to the annualised lost-sales estimate, is the direct revenue-recovery opportunity.
- **Excess inventory reduction**: an 8-15% reduction in excess days-of-supply reduces working-capital carrying cost, estimated at a 22% annual holding-cost rate on the freed inventory value (consistent with the holding-cost assumption used in `supply_chain/inventory.py`'s EOQ calculation).
- **Forecast accuracy improvement**: every one-point reduction in WMAPE reduces both the safety stock required to hold a given service level and the frequency of emergency replenishment, compounding into both of the above.
- **Manual effort reduction**: at an illustrative loaded planner cost of $65/hour and a baseline of roughly 120 planner-hours per month spent on manual exception review and override, a 20% reduction in override volume frees approximately 24 hours per month, worth roughly $18,700 annually per planning team.

Finance validates realised benefits against the frozen baseline in `configs/monitoring_thresholds.yml`; the platform reports the leading indicators (forecast accuracy, stock-out rate, excess inventory, supplier performance) that predict the value, while quarterly finance reconciliation confirms it against actual P&L and working-capital movement.

## Risks and limitations to the business case

The improvement targets are calibrated for a retailer moving off a purely averages-based process; a retailer with an already-mature forecasting function should expect smaller relative gains. Forecast accuracy gains are demonstrably real (see the holdout WMAPE comparison) but will vary by category - fast-moving, weather-sensitive categories (Beverages, Frozen) show the largest gain from the gradient-boosted model in this build, while stable categories (Household, Personal Care) see a smaller relative improvement because the baseline moving average was already adequate for them. See [risk register](../governance/risk_register.md) for the full list of operational and model risks.

## Adoption plan

Phase 1 (weeks 1-4): shadow-run the forecasting and reorder-point models alongside the existing spreadsheet process for one category group, with planners reviewing every recommendation. Phase 2 (weeks 5-8): expand to all categories, move well-behaved SKU-store combinations (low override rate, low forecast error) to auto-approval, keep manual review for high-value or high-variance combinations. Phase 3 (weeks 9-12): enable scenario modelling for peak-season and supplier-disruption planning, and stand up the monthly governance forum. Phase 4 (ongoing): quarterly model revalidation, annual full-scale data refresh, and a standing improvement backlog fed by the override-reason and anomaly logs.
