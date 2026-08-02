"""Fabric-notebook-equivalent entrypoint: run the silver conformance and gold
star-schema transformations against the DuckDB warehouse.

Assumes data/raw already exists (run python/ingestion/load_bronze.py first,
or the full pipeline via `python -m supply_chain.pipeline`). Executes
sql/silver/*.sql and sql/gold/*.sql in order and prints row counts for a
quick sanity check - the same reconciliation check that runs in CI.
"""
from __future__ import annotations

from supply_chain.config import ROOT
from supply_chain.pipeline import build_warehouse


def main() -> None:
    con = build_warehouse(ROOT)
    for schema, table in [
        ("silver", "daily_sales"), ("silver", "inventory_snapshots"), ("silver", "purchase_orders"),
        ("gold", "fact_daily_sales"), ("gold", "fact_inventory"), ("gold", "fact_purchase_orders"),
        ("gold", "dim_product"), ("gold", "dim_store"), ("gold", "supplier_performance"),
    ]:
        count = con.execute(f"select count(*) from {schema}.{table}").fetchone()[0]
        print(f"{schema}.{table}: {count} rows")
    con.close()


if __name__ == "__main__":
    main()
