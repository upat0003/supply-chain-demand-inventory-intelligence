-- Bronze layer: raw, untransformed source extracts registered as DuckDB views.
-- In a Fabric deployment these views become shortcuts onto the Bronze Lakehouse
-- (one Parquet delta per source system, no cleaning applied). Locally they read
-- straight off the CSV extracts landed by supply_chain.synthetic.write_raw.
create schema if not exists bronze;

create or replace view bronze.products             as select * from read_csv_auto('data/raw/products.csv');
create or replace view bronze.skus                  as select * from read_csv_auto('data/raw/skus.csv');
create or replace view bronze.stores                as select * from read_csv_auto('data/raw/stores.csv');
create or replace view bronze.warehouses             as select * from read_csv_auto('data/raw/warehouses.csv');
create or replace view bronze.suppliers              as select * from read_csv_auto('data/raw/suppliers.csv');
create or replace view bronze.daily_sales            as select * from read_csv_auto('data/raw/daily_sales.csv');
create or replace view bronze.inventory_snapshots     as select * from read_csv_auto('data/raw/inventory_snapshots.csv');
create or replace view bronze.purchase_orders        as select * from read_csv_auto('data/raw/purchase_orders.csv');
create or replace view bronze.lead_times             as select * from read_csv_auto('data/raw/lead_times.csv');
create or replace view bronze.promotions             as select * from read_csv_auto('data/raw/promotions.csv');
create or replace view bronze.prices                 as select * from read_csv_auto('data/raw/prices.csv');
create or replace view bronze.markdowns              as select * from read_csv_auto('data/raw/markdowns.csv');
create or replace view bronze.holidays               as select * from read_csv_auto('data/raw/holidays.csv');
create or replace view bronze.weather                as select * from read_csv_auto('data/raw/weather.csv');
create or replace view bronze.returns                as select * from read_csv_auto('data/raw/returns.csv');
create or replace view bronze.stock_outs             as select * from read_csv_auto('data/raw/stock_outs.csv');
create or replace view bronze.replenishment_decisions as select * from read_csv_auto('data/raw/replenishment_decisions.csv');
