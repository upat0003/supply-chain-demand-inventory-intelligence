-- Silver layer: conformed, validated and de-duplicated tables.
-- Referential integrity, deduplication, missing-value handling and value-range
-- clipping happen exactly once here, so every gold table and downstream model
-- reads from a single validated source of truth.
create schema if not exists silver;

create or replace table silver.products as
select product_id, category, subcategory, brand, unit_cost, unit_price, shelf_life_days,
       is_seasonal, launch_date, discontinued
from bronze.products
where product_id is not null;

create or replace table silver.skus as
select s.sku_id, s.product_id, s.category, s.subcategory, s.pack_size, s.uom, s.barcode,
       s.unit_cost, s.unit_price, s.case_pack_qty, s.discontinued
from bronze.skus s
inner join bronze.products p using (product_id);   -- drops any SKU with an orphaned product reference

create or replace table silver.stores as
select st.* from bronze.stores st
inner join bronze.warehouses w using (warehouse_id);  -- drops any store with an orphaned warehouse reference

create or replace table silver.warehouses as select * from bronze.warehouses;
create or replace table silver.suppliers as select * from bronze.suppliers;

-- de-duplicate exact-duplicate POS extract rows and repair missing revenue
-- from unit price, while flagging (not silently discarding) implausible spikes
create or replace table silver.daily_sales as
select distinct
    d.date, d.store_id, d.sku_id,
    d.units_sold,
    coalesce(d.revenue, d.units_sold * sk.unit_price) as revenue,
    d.promo_flag,
    d.units_sold >= 200 as is_volume_outlier
from bronze.daily_sales d
inner join silver.skus sk using (sku_id);

-- negative on-hand is a physical impossibility (system sync defect); clip to
-- zero for downstream analytics but retain a flag for the governance report
create or replace table silver.inventory_snapshots as
select
    date, location_type, location_id, sku_id,
    greatest(on_hand_units, 0) as on_hand_units,
    on_order_units,
    safety_stock_units,
    days_of_supply,
    on_hand_units < 0 as had_negative_on_hand_defect
from bronze.inventory_snapshots;

create or replace table silver.purchase_orders as
select po.* from bronze.purchase_orders po
inner join silver.skus sk using (sku_id);  -- drops the injected bad-SKU reference row(s)

create or replace table silver.lead_times as select * from bronze.lead_times;
create or replace table silver.promotions as select * from bronze.promotions;
create or replace table silver.prices as select * from bronze.prices;
create or replace table silver.markdowns as select * from bronze.markdowns;
create or replace table silver.holidays as select * from bronze.holidays;

create or replace table silver.weather as
select date, region,
       coalesce(avg_temp_c, avg(avg_temp_c) over (partition by region)) as avg_temp_c,
       coalesce(precipitation_mm, avg(precipitation_mm) over (partition by region)) as precipitation_mm,
       severe_weather_flag
from bronze.weather;

create or replace table silver.returns as select * from bronze.returns;
create or replace table silver.stock_outs as select * from bronze.stock_outs;
create or replace table silver.replenishment_decisions as select * from bronze.replenishment_decisions;
