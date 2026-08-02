# Data Catalogue and Provenance

| Asset | Layer | Grain | Classification | Owner | Retention |
|---|---|---|---|---|---|
| Products | Bronze/Silver | Product | Internal | Product Data Steward | Life of product + 3 years |
| SKUs | Bronze/Silver | SKU | Internal | Product Data Steward | Life of product + 3 years |
| Stores | Bronze/Silver | Store | Internal | Location Data Steward | Life of store + 3 years |
| Warehouses | Bronze/Silver | Warehouse | Internal | Location Data Steward | Life of warehouse + 3 years |
| Suppliers | Bronze/Silver | Supplier | Confidential (commercial) | Supplier Data Steward | 7 years (contractual) |
| Daily sales | Bronze/Silver/Gold | Store-SKU-day | Internal | Sales Data Steward | 3 years detail, 7 years aggregate |
| Inventory snapshots | Bronze/Silver/Gold | Location-SKU-day | Internal | Inventory Data Steward | 3 years |
| Purchase orders | Bronze/Silver/Gold | Purchase order line | Confidential (commercial) | Supply Chain Data Steward | 7 years |
| Lead times | Silver (derived) | Supplier-SKU | Internal | Supply Chain Data Steward | 3 years |
| Promotions | Bronze/Silver | Promotion-SKU | Internal | Category Data Steward | 3 years |
| Prices | Bronze/Silver | SKU-effective date | Internal | Pricing Data Steward | 7 years |
| Markdowns | Bronze/Silver | Markdown event | Internal | Category Data Steward | 3 years |
| Holidays | Reference | Date-region | Public | Planning Data Steward | Indefinite |
| Weather | Reference | Date-region | Public | Planning Data Steward | 3 years |
| Returns | Bronze/Silver | Return line | Internal | Store Operations | 3 years |
| Stock-outs | Bronze/Silver/Gold | Store-SKU-day | Internal | Inventory Data Steward | 3 years |
| Replenishment decisions | Bronze/Silver/Gold | Decision | Internal | Supply Chain Data Steward | 7 years (audit trail) |
| Forecast outputs | Gold/Model output | Store-SKU-week | Internal | Demand Planning Lead | 3 years, versioned |
| Model artifacts | Model registry | Model version | Restricted | Model Owner | Life of model + 3 years |

No dataset in this platform contains personal or customer-identifying information; the lowest grain of any table is a store, warehouse, supplier or SKU, not an individual. All sample data is synthetic and deterministically generated from seed 42. Production provenance must additionally record source system, extraction timestamp, schema version, checksum, pipeline run identifier and transformation commit hash for every load.

## Business glossary (selected critical data elements)

| Term | Definition | Critical data element |
|---|---|---|
| SKU | Sellable unit of a product at a specific pack size; the base grain for demand and inventory | Yes |
| Days of supply | On-hand inventory divided by average daily demand; expressed in days | Yes |
| Safety stock | Buffer inventory held to absorb demand and lead-time variability at a target service level | Yes |
| Reorder point | Inventory level that triggers a new replenishment order | Yes |
| Stock-out | A store-SKU-day where realised demand exceeded available inventory | Yes |
| Lead time | Elapsed days between placing a purchase order and receiving usable stock | Yes |
| Forecast WMAPE | Weighted mean absolute percentage error; the primary forecast accuracy metric | Yes |
| Override | A manual planner decision that departs from the system-recommended order quantity | Yes |
| Champion model | The forecast/inventory model currently approved for production decisioning | Yes |

See [docs/data_dictionary.md](../docs/data_dictionary.md) for full column-level definitions.
