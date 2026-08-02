-- Category-level inventory health mart used to reconcile the days-of-supply
-- and excess-stock figures shown on the Inventory Health dashboard page.
select
    sk.category,
    count(*) as snapshot_rows,
    avg(i.days_of_supply) as avg_days_of_supply,
    sum(case when i.days_of_supply > 6 then 1 else 0 end) * 1.0 / count(*) as excess_stock_rate
from {{ ref('stg_inventory_snapshots') }} i
inner join {{ source('raw', 'skus') }} sk on i.sku_id = sk.sku_id
where i.location_type = 'Store'
group by 1
