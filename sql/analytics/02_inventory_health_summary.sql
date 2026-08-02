-- Ad-hoc analytics query: inventory health by category, combining stock
-- position with recent stock-out incidence for the weekly planning huddle.
with recent_inventory as (
    select f.sku_id, p.category, f.days_of_supply
    from gold.fact_inventory f
    inner join gold.dim_product p using (sku_id)
    where f.location_type = 'Store'
      and f.date_key >= (select max(date_key) - interval 30 day from gold.fact_inventory)
),
recent_stockouts as (
    select p.category, count(*) as stockout_days, sum(s.lost_sales_units_estimate) as lost_sales_units
    from gold.fact_stockouts s
    inner join gold.dim_product p using (sku_id)
    where s.stockout_flag
      and s.date_key >= (select max(date_key) - interval 30 day from gold.fact_stockouts)
    group by 1
)
select
    i.category,
    round(avg(i.days_of_supply), 1) as avg_days_of_supply,
    round(sum(case when i.days_of_supply > 6 then 1.0 else 0.0 end) / count(*) * 100, 1) as excess_stock_pct,
    coalesce(so.stockout_days, 0) as stockout_days_last_30,
    coalesce(so.lost_sales_units, 0) as lost_sales_units_last_30
from recent_inventory i
left join recent_stockouts so using (category)
group by 1, so.stockout_days, so.lost_sales_units
order by excess_stock_pct desc;
