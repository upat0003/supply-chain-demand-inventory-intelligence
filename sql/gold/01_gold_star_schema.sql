-- Gold layer: conformed star schema for reporting and modelling.
-- Dimensions carry the descriptive attributes; facts stay narrow and numeric.
-- This is the layer Power BI's semantic model and the Python feature/model
-- code both read from.
create schema if not exists gold;

create or replace table gold.dim_date as
select
    d::date as date_key,
    extract(year from d) as year,
    extract(month from d) as month,
    extract(week from d) as iso_week,
    extract(dow from d) as day_of_week,
    case when extract(dow from d) in (0, 6) then true else false end as is_weekend
from (select unnest(generate_series(
        (select min(date::date) from silver.daily_sales),
        (select max(date::date) from silver.daily_sales),
        interval 1 day)) as d);

create or replace table gold.dim_product as
select sk.sku_id, sk.product_id, p.category, p.subcategory, p.brand, sk.pack_size, sk.uom,
       sk.unit_cost, sk.unit_price, p.shelf_life_days, p.is_seasonal, sk.discontinued
from silver.skus sk
inner join silver.products p using (product_id);

create or replace table gold.dim_store as
select store_id, region, warehouse_id, store_format, size_sqm, open_date from silver.stores;

create or replace table gold.dim_warehouse as select * from silver.warehouses;
create or replace table gold.dim_supplier as select * from silver.suppliers;

create or replace table gold.fact_daily_sales as
select date::date as date_key, store_id, sku_id, units_sold, revenue, promo_flag, is_volume_outlier
from silver.daily_sales;

create or replace table gold.fact_inventory as
select date::date as date_key, location_type, location_id, sku_id, on_hand_units, on_order_units,
       safety_stock_units, days_of_supply, had_negative_on_hand_defect
from silver.inventory_snapshots;

create or replace table gold.fact_purchase_orders as
select po_id, supplier_id, sku_id, warehouse_id, order_date::date as order_date,
       expected_delivery_date::date as expected_delivery_date,
       actual_delivery_date::date as actual_delivery_date,
       quantity_ordered, quantity_received, unit_cost, status,
       (actual_delivery_date::date > expected_delivery_date::date) as is_late
from silver.purchase_orders;

create or replace table gold.fact_stockouts as
select date::date as date_key, store_id, sku_id, stockout_flag, lost_sales_units_estimate,
       lost_sales_revenue_estimate
from silver.stock_outs;

create or replace table gold.fact_replenishment_decisions as
select decision_id, date::date as date_key, sku_id, location_type, location_id,
       recommended_order_qty, reorder_point, safety_stock_units, approved_qty, approver,
       override_flag, override_reason, decision_status
from silver.replenishment_decisions;

-- Warehouse and supplier performance mart used directly by the Supplier
-- Performance dashboard page and the lead-time risk model.
create or replace table gold.supplier_performance as
select
    s.supplier_id, s.supplier_name, s.reliability_score, s.region_of_origin,
    count(*) as purchase_orders,
    avg(case when po.is_late then 1.0 else 0.0 end) as late_rate,
    avg(datediff('day', po.order_date, po.actual_delivery_date)) as avg_actual_lead_time_days,
    avg(po.quantity_received / nullif(po.quantity_ordered, 0)) as avg_fill_rate
from gold.fact_purchase_orders po
inner join gold.dim_supplier s using (supplier_id)
group by 1, 2, 3, 4;
