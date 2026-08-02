-- Joins validated daily sales to product and store attributes and derives
-- the revenue-per-unit metric used by the pricing and promotion analyses.
select
    s.sale_date,
    s.store_id,
    s.sku_id,
    sk.category,
    sk.subcategory,
    st.region,
    st.store_format,
    s.units_sold,
    s.revenue,
    {{ safe_divide('s.revenue', 's.units_sold') }} as revenue_per_unit,
    s.promo_flag
from {{ ref('stg_daily_sales') }} s
inner join {{ source('raw', 'skus') }} sk on s.sku_id = sk.sku_id
inner join {{ source('raw', 'stores') }} st on s.store_id = st.store_id
