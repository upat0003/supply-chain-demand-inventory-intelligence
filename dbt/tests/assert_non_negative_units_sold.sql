select * from {{ ref('stg_daily_sales') }} where units_sold < 0
