select
    cast(date as date) as sale_date,
    cast(store_id as varchar) as store_id,
    cast(sku_id as varchar) as sku_id,
    cast(units_sold as integer) as units_sold,
    cast(revenue as decimal(18, 2)) as revenue,
    cast(promo_flag as boolean) as promo_flag
from {{ source('raw', 'daily_sales') }}
where units_sold >= 0
