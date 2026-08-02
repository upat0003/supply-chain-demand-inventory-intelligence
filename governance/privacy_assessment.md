# Privacy Assessment

## Scope and data subjects

This platform processes product, store, warehouse, supplier, sales, inventory and purchase-order data. It does not process customer-level or employee-level personal information: the finest grain in any table is a store-SKU-day or a purchase-order line, and no table carries a customer identifier, loyalty number, payment instrument, name, address or other direct or indirect personal identifier. Supplier records carry a business name and commercial reliability score, which is business (not personal) data, though the same governance discipline is applied to it because it materially affects a third-party's operational reputation.

## Privacy-by-design controls applied

- **Purpose limitation** - the platform exists solely to improve demand forecasting and inventory decisions; no dataset is repurposed for marketing, pricing discrimination against individuals, or workforce monitoring.
- **Data minimisation** - only the attributes required for forecasting, replenishment and supplier performance are retained; no incidental customer or loyalty data is ingested even though a real POS/CRM extract would carry it.
- **Aggregation** - all reporting is at store, region, category, SKU or supplier level; no dashboard, export or model output resolves to an individual shopper.
- **Synthetic data** - every record in this repository is synthetically generated (seed 42) for demonstration purposes; no real retailer, supplier or transaction data is used or referenced.
- **Access control** - see [access_control_matrix.md](access_control_matrix.md) for role-based access to bronze, silver, gold and model layers.
- **Encryption and workspace controls** - production deployment assumes encryption in transit and at rest, managed identities, and workspace-level access restriction consistent with the organisation's cloud security baseline.

## Production considerations (not yet in scope for this synthetic build)

A production implementation that ingests real POS or loyalty-linked transaction data would need to additionally assess: whether loyalty-linked sales data constitutes personal information under the Australian Privacy Act 1988 and applicable state records legislation; a documented lawful basis and data-sharing agreement with each supplier and store banner; a data retention and deletion schedule aligned to tax and consumer-law requirements (typically 5-7 years for transaction records); and a data breach response plan covering the supplier and inventory systems in scope. None of these are required for the current synthetic, non-personal dataset, but the assessment is documented here so it is not overlooked if the platform is extended to ingest loyalty or customer-linked data in future.

## Retention

Raw bronze extracts: 3 years. Silver and gold tables: 3 years detail, 7 years aggregate. Purchase order and replenishment decision records: 7 years (commercial audit trail). Model artifacts and run summaries: life of model version + 3 years. Reference data (holidays, weather): indefinite, no privacy sensitivity.
