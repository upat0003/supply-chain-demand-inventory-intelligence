# Reference Data

Slowly-changing lookup data maintained by the business rather than extracted from a transactional source system. `category_service_level_targets.csv` sets the target cycle service level (and the rationale) used by `supply_chain.inventory.build_reorder_recommendations` when sizing safety stock by category; it mirrors `dbt/seeds/category_service_level_targets.csv` so the same reference values are available whether a downstream consumer works from the DuckDB warehouse (via dbt seed) or directly from a CSV.

Public holiday and weather data, although also reference-like in nature, are generated as part of the main synthetic dataset (`data/raw/holidays.csv`, `data/raw/weather.csv`) because they vary by date and region rather than being a static lookup table.
