select
    cast(date as date) as snapshot_date,
    cast(location_type as varchar) as location_type,
    cast(location_id as varchar) as location_id,
    cast(sku_id as varchar) as sku_id,
    greatest(cast(on_hand_units as double), 0) as on_hand_units,
    cast(on_order_units as double) as on_order_units,
    cast(days_of_supply as double) as days_of_supply
from {{ source('raw', 'inventory_snapshots') }}
