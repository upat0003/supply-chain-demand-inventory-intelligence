# Planning Assumptions Register

Assumptions that feed the forecasting and inventory models but are not themselves learned from data - each has an owner and a review cadence, so a change in the business (a new supplier, a service-level policy change) has a clear place to be reflected.

| Assumption | Current value | Owner | Review cadence |
|---|---|---|---|
| Target cycle service level (default) | 95% (z = 1.65) | Demand Planning Lead | Quarterly |
| Category-specific service level | See `dbt/seeds/category_service_level_targets.csv` (90-97%) | Demand Planning Lead | Quarterly |
| Excess-inventory threshold | Days of supply > 6 (fast-turn grocery/FMCG norm) | Inventory Analyst | Annually |
| Forecast holdout window | 8 weeks | Data Science Lead | Reviewed at each model retraining |
| Reference window for drift detection | Earliest and latest 12 weeks of the modelled period | Data Science Lead | Reviewed at each model retraining |
| Order cost assumption (EOQ) | $45 per purchase order | Supply Chain Manager | Annually, or on 3PL/procurement contract change |
| Inventory holding cost rate | 22% of unit cost per year | Finance | Annually |
| Internal store replenishment lead time | 2-3 days (warehouse to store transfer) | Supply Chain Manager | Reviewed on network/DC change |
| Promotion baseline window | 21 days immediately before a promotion starts | Category Data Steward | Reviewed at each promotion cycle |
| Late-delivery definition | Actual delivery date later than the supplier's quoted expected delivery date | Supply Chain Manager | Reviewed on supplier contract renewal |

Every assumption above is read from `supply_chain/config.py`, `configs/monitoring_thresholds.yml` or `dbt/seeds/category_service_level_targets.csv` - never hardcoded inline in a model - so a change is a one-line configuration update with a visible diff, not a buried code change.
