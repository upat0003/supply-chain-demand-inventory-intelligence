# Metric Catalogue

| Metric | Definition | Grain | Threshold / interpretation |
|---|---|---|---|
| WMAPE | Weighted mean absolute percentage error: Σ\|actual-forecast\| ÷ Σ\|actual\| | Store-SKU-week / SKU-week / category-week / total-week | warning ≥ 0.20, critical ≥ 0.28 |
| MAPE | Mean absolute percentage error | Same as WMAPE | supplementary, sensitive to low-volume weeks |
| Forecast bias | Mean (forecast - actual) ÷ mean actual | Same as WMAPE | investigate outside ±10% |
| Forecast accuracy % | 1 - WMAPE, expressed as a percentage | Same as WMAPE | headline KPI for the executive page |
| PSI | Population stability index between a reference and current window | Feature-period | warning ≥ 0.10, critical ≥ 0.25 |
| Days of supply | On-hand units ÷ average daily demand | Location-SKU-day | excess if > 6 days sustained (fast-turn grocery network norm) |
| Stock-out rate | Store-SKU-days with unmet demand ÷ total store-SKU-days | Store-SKU-period | target 10-20% relative reduction |
| Lost sales estimate | Unmet demand units × unit price | Store-SKU-day | reported as an annualised dollar estimate |
| Safety stock | z × √(LT×σ_d² + d̄²×σ_LT²) | Store/warehouse-SKU | recalculated on each pipeline run from observed variability |
| Reorder point | d̄ × LT + safety stock | Store/warehouse-SKU | triggers a replenishment recommendation |
| Economic order quantity | √(2 × annual demand × order cost ÷ holding cost) | Store/warehouse-SKU | advisory order-size guide |
| Inventory turns | Annualised COGS ÷ average inventory value | Category/total-period | target 5% relative improvement |
| Supplier on-time rate | Purchase orders delivered on/before expected date ÷ total | Supplier-period | critical below 70% |
| Lead-time risk score | Predicted probability a purchase order arrives late | Purchase order | review queue above 0.30 |
| Override rate | Manually overridden replenishment decisions ÷ total decisions | Period | target 20% relative reduction |
| Promotion uplift % | (Actual - expected baseline) ÷ expected baseline, during a promotion window | Promotion event | compared against planned uplift by promo type |
| Data quality pass rate | Mean pass rate across all governance rules | Pipeline run | critical below 93%, warning below 97% |
| Inventory anomaly count | Store/warehouse-SKU-days flagged by the anomaly detector | Pipeline run | reviewed weekly by Inventory Analyst |

All thresholds are defined once in `configs/monitoring_thresholds.yml` and read by `supply_chain/monitoring.py`, so the dashboard, the pipeline logs and this document can never drift out of sync with each other.
