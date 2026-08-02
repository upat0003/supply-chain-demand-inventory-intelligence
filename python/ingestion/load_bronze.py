"""Fabric-notebook-equivalent entrypoint: land raw source extracts into bronze.

In production this becomes a Data Factory copy activity / Fabric notebook
that lands store POS, WMS and supplier EDI extracts into the Bronze
Lakehouse. Locally it generates the synthetic extracts and writes them to
data/raw, then registers the bronze views defined in sql/bronze/.

Run: python -m python.ingestion.load_bronze --scale dev
"""
from __future__ import annotations

import argparse

from supply_chain.config import ROOT, SCALES
from supply_chain.pipeline import build_warehouse
from supply_chain.synthetic import generate_supply_chain, write_raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate raw extracts and build the bronze layer")
    parser.add_argument("--scale", choices=list(SCALES), default="dev")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cfg = SCALES[args.scale]
    data = generate_supply_chain(cfg, seed=args.seed)
    write_raw(data, ROOT / "data/raw")
    con = build_warehouse(ROOT)
    counts = {name: con.execute(f"select count(*) from bronze.{name}").fetchone()[0] for name in data}
    con.close()
    for name, count in counts.items():
        print(f"bronze.{name}: {count} rows")


if __name__ == "__main__":
    main()
