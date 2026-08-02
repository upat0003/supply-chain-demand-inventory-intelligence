"""Fabric-notebook-equivalent entrypoint: run the governance data-quality and
master-data checks against the current data/raw extracts and print a
pass/fail summary. Exits non-zero if any critical rule fails, so it can be
wired into a CI or orchestration gate ahead of gold-layer publication.

Run: python -m python.governance.run_data_quality_checks
"""
from __future__ import annotations

import sys

import pandas as pd

from supply_chain.config import ROOT
from supply_chain.governance import override_tracking_summary, run_data_quality_checks, validate_master_data

TABLES = ["products", "skus", "stores", "warehouses", "suppliers", "daily_sales", "inventory_snapshots",
          "purchase_orders", "lead_times", "promotions", "prices", "markdowns", "holidays", "weather",
          "returns", "stock_outs", "replenishment_decisions"]


def main() -> int:
    raw = ROOT / "data/raw"
    tables = {name: pd.read_csv(raw / f"{name}.csv") for name in TABLES}

    dq = run_data_quality_checks(ROOT / "governance/data_quality_rules.yml", tables)
    master = validate_master_data(tables["products"], tables["skus"], tables["stores"],
                                   tables["warehouses"], tables["suppliers"], tables["purchase_orders"])
    overrides = override_tracking_summary(tables["replenishment_decisions"])

    print("Data quality rules:\n", dq[["id", "table", "field", "pass_rate", "passed", "severity"]].to_string(index=False))
    print("\nMaster data checks:\n", master.to_string(index=False))
    print("\nOverride tracking:", overrides)

    critical_failures = dq[(~dq.passed) & (dq.severity == "critical")]
    if len(critical_failures):
        print(f"\n{len(critical_failures)} CRITICAL data-quality rule(s) failed: {critical_failures.id.tolist()}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
