# Semantic Model

A star schema built directly on top of the gold layer (`sql/gold/01_gold_star_schema.sql`), imported into Power BI from the `powerbi/data/*.csv` exports (or, in production, from the Fabric Warehouse gold schema directly via DirectLake/Import).

## Dimensions

| Table | Grain | Key columns |
|---|---|---|
| Dim Date | Day | date_key, year, month, iso_week, day_of_week, is_weekend |
| Dim Product | SKU | sku_id (key), product_id, category, subcategory, brand, pack_size, unit_cost, unit_price, shelf_life_days, is_seasonal |
| Dim Store | Store | store_id (key), region, warehouse_id, store_format, size_sqm |
| Dim Warehouse | Warehouse | warehouse_id (key), region, warehouse_type, capacity_units |
| Dim Supplier | Supplier | supplier_id (key), supplier_name, primary_category, region_of_origin, reliability_score |

## Facts

| Table | Grain | Key measures |
|---|---|---|
| Fact Daily Sales | Store-SKU-day | units_sold, revenue, promo_flag |
| Fact Inventory | Location-SKU-day | on_hand_units, on_order_units, safety_stock_units, days_of_supply |
| Fact Purchase Orders | Purchase order line | quantity_ordered, quantity_received, is_late |
| Fact Stockouts | Store-SKU-day (unmet demand only) | lost_sales_units_estimate, lost_sales_revenue_estimate |
| Fact Replenishment Decisions | Decision | recommended_order_qty, approved_qty, override_flag, decision_status |
| Fact Forecast | Store-SKU-week (holdout) | actual_units, forecast_units, method (baseline / champion / ETS) |
| Fact Drift | Feature-period | psi, status |
| Fact Data Quality | Rule-run | pass_rate, passed, severity |
| Fact Inventory Anomalies | Location-SKU-day (flagged only) | anomaly_score, anomaly_type |
| Fact Promotion Uplift | Promotion event | actual_units, expected_units_baseline, uplift_pct, planned_uplift_pct |

## Relationships

`Dim Product[sku_id]` is the one-to-many parent of every fact table's `sku_id`. `Dim Store[store_id]` relates to `Fact Daily Sales`, `Fact Stockouts` and the store-grain rows of `Fact Inventory` and `Fact Replenishment Decisions`. `Dim Warehouse[warehouse_id]` relates to `Fact Purchase Orders` and the warehouse-grain rows of `Fact Inventory`. `Dim Supplier[supplier_id]` relates to `Fact Purchase Orders`. `Dim Date[date_key]` relates to every fact table's date column, giving a single conformed calendar for all time intelligence measures. `Fact Inventory` carries a `location_type` flag (Store/Warehouse) because it is a single table serving two different dimensional roles - a documented, deliberate simplification rather than two nearly-identical fact tables.

## Row-level security

Two RLS roles are defined: `Regional Planner` (filters `Dim Store[region]` and `Dim Warehouse[region]` to the user's assigned region) and `Category Manager` (filters `Dim Product[category]` to the user's assigned categories). Executives and governance roles see all rows. RLS is enforced at the semantic-model layer, not in report visuals, so it cannot be bypassed by adding a new visual.

## Calculation groups and time intelligence

A `Period` calculation group (Current, Prior period, Same period last year) is applied to every headline measure so a single visual can be toggled between absolute and comparative views without duplicating measures. `Dim Date` includes a fiscal-week attribute aligned to the 13-week reporting cadence used throughout the dashboard's "Latest 13 weeks" default filter chip.
