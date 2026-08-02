# Sample Data

`data/samples/supplier_scorecard.csv` and `data/samples/inventory_health_summary.csv` are the outputs of `sql/analytics/01_supplier_scorecard.sql` and `sql/analytics/02_inventory_health_summary.sql` respectively - the ad-hoc queries a demand planning analyst would run directly against the warehouse. They are regenerated on every pipeline run.

Run `python -m supply_chain.pipeline --scale dev --seed 42` to regenerate these files along with every other raw, processed and Power BI export in this repository. All data is synthetic and deterministic; it contains no real retailer, supplier or customer information.
