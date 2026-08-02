# Power BI Supply Chain AI Control Centre - Dashboard Specification

Visual identity: a graphite navigation rail with a warm rust/amber and steel-blue accent palette (see `theme.json`), chosen to read as a warehouse/logistics product rather than a reskin of a financial or healthcare dashboard. Global filter chips (persistent, removable pills, top-right of every page): reporting period, model version, region. Every chart carries a colour-coded legend, labelled axes, a hover tooltip on at least one highlighted data point, and a cross-filter highlight (outlined bar/cell/segment) so the interaction model is consistent page to page.

| Page | Decision story | Principal visuals | Alert / drill-through |
|---|---|---|---|
| Supply Chain Executive Overview | Are we hitting stock-out, inventory and forecast targets today? | Forecast accuracy trend, stock-out rate by region, inventory value by category | KPI card → underlying detail page |
| Demand Forecast Accuracy | Which forecasting method is winning, and at what level? | WMAPE trend (baseline vs champion), accuracy by hierarchy level, forecast error by category | Hierarchy level → store-SKU detail |
| Inventory Health | Where is stock sitting too long or too thin? | Days-of-supply heatmap by category/region, inventory composition donut, anomaly type breakdown | Category → SKU-store inventory ledger |
| Stock-Out Risk | Which store-SKU combinations are about to run out? | Risk score by category, stock-out rate trend, top at-risk combinations | Combination → replenishment recommendation |
| Replenishment Recommendations | What should we order next, and who needs to approve it? | Prioritised reorder queue, override reasons, safety stock by scenario | Queue row → decision approval workflow |
| Supplier Performance | Which suppliers are putting delivery at risk? | On-time delivery rate by supplier, late-delivery trend, lead time vs reliability | Supplier → purchase order history |
| Promotion Impact | Are promotions delivering the uplift we planned for? | Actual vs planned uplift by promo type, promotion mix by category, variance trend | Promo type → SKU-level uplift detail |
| Data Quality and Model Monitoring | Can we trust the data and the models feeding these pages? | Data-quality rule results, rule ownership by domain, weekly WMAPE control chart | Rule → governance data-quality-rules register |

## Alert thresholds

WMAPE ≥ 0.20 warning / ≥ 0.28 critical; PSI ≥ 0.10 warning / ≥ 0.25 critical; data-quality pass rate < 97% warning / < 93% critical; supplier late-delivery rate ≥ 20% watch / ≥ 30% critical; inventory anomaly flagged when IsolationForest score exceeds the 98th percentile or on-hand is negative. Thresholds are defined once in `configs/monitoring_thresholds.yml` and read by `supply_chain/monitoring.py`, so this page, the pipeline logs and the metric catalogue can never drift out of sync.

## Drill-through and tooltips

Every KPI card and chart mark carries a tooltip with the metric's current value, its comparison (baseline, target or prior period) and, on the Data Quality page, the accountable owner. Drill-through is defined from category/supplier/rule level down to the store-SKU, purchase-order or governance-register row that explains it, so a planner or executive never has to leave Power BI to find the underlying evidence.

## Mobile layout note

The 1600x900 desktop canvas re-flows to a single-column mobile layout: KPI cards stack full-width at the top, the two primary charts stack vertically beneath them, and the narrative card moves to the bottom. Cross-filtering and tooltips behave identically on mobile; the filter-chip row collapses into a single "Filters" button that expands a slide-over panel, consistent with Power BI Mobile's standard phone layout behaviour.

## Reproducible build

`powerbi/Templates/pages.json` holds the content for all 8 pages (KPIs, chart legends, axis labels, tooltip text, narrative). `powerbi/Templates/render_mockups.py` (Python + Pillow) renders `powerbi/Screenshots/*.png` and the annotated `powerbi/Mockups/*.png` wireframes from that same file, so the design and the "screenshots" in this repository can never drift apart - regenerate with `python powerbi/Templates/render_mockups.py`.
