"""Data-quality and master-data governance checks.

Executes the rules in governance/data_quality_rules.yml against the bronze
extracts, validates referential integrity between the product, SKU, store,
warehouse and supplier master tables, and summarises manual override /
approval activity from the replenishment decisions log. This is the
evidence layer behind the Data Quality and Model Monitoring dashboard page.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def load_rules(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text())["rules"]


def _evaluate_rule(rule: dict, tables: dict[str, pd.DataFrame]) -> dict:
    table = tables.get(rule["table"])
    if table is None or rule["field"] not in table.columns:
        return {**rule, "pass_rate": float("nan"), "passed": False, "rows_checked": 0}

    field = table[rule["field"]]
    expectation = rule["expectation"]
    if expectation == "not_null":
        mask = field.notna()
    elif expectation == "unique_and_not_null":
        mask = field.notna() & ~field.duplicated(keep=False)
    elif expectation.startswith("between_"):
        parts = expectation.replace("between_", "").split("_and_")
        low, high = float(parts[0]), float(parts[1])
        mask = field.between(low, high) | field.isna()
    elif expectation.startswith("below_"):
        threshold = float(expectation.replace("below_", "").split("_")[0])
        mask = (field < threshold) | field.isna()
    elif expectation == "non_negative":
        mask = (field >= 0) | field.isna()
    elif expectation.startswith("referential_"):
        ref_table, ref_field = rule["reference"]["table"], rule["reference"]["field"]
        valid_values = set(tables[ref_table][ref_field].dropna())
        mask = field.isin(valid_values)
    else:
        mask = pd.Series([True] * len(field))

    pass_rate = float(mask.mean()) if len(mask) else float("nan")
    threshold = rule.get("threshold", 1.0)
    return {
        **rule, "pass_rate": round(pass_rate, 4), "rows_checked": int(len(field)),
        "rows_failed": int((~mask).sum()), "passed": bool(pass_rate >= threshold),
    }


def run_data_quality_checks(rules_path: Path, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rules = load_rules(rules_path)
    results = [_evaluate_rule(rule, tables) for rule in rules]
    return pd.DataFrame(results)


def validate_master_data(products: pd.DataFrame, skus: pd.DataFrame, stores: pd.DataFrame,
                          warehouses: pd.DataFrame, suppliers: pd.DataFrame,
                          purchase_orders: pd.DataFrame) -> pd.DataFrame:
    checks = []
    checks.append({"check": "product_id uniqueness", "domain": "Product master",
                    "passed": bool(products.product_id.is_unique), "detail": f"{products.product_id.duplicated().sum()} duplicates"})
    checks.append({"check": "sku references known product_id", "domain": "Product master",
                    "passed": bool(skus.product_id.isin(products.product_id).all()),
                    "detail": f"{(~skus.product_id.isin(products.product_id)).sum()} orphaned SKUs"})
    checks.append({"check": "store references known warehouse_id", "domain": "Location master",
                    "passed": bool(stores.warehouse_id.isin(warehouses.warehouse_id).all()),
                    "detail": f"{(~stores.warehouse_id.isin(warehouses.warehouse_id)).sum()} orphaned stores"})
    checks.append({"check": "supplier_id uniqueness", "domain": "Supplier master",
                    "passed": bool(suppliers.supplier_id.is_unique), "detail": "no duplicates" if suppliers.supplier_id.is_unique else "duplicates found"})
    bad_po = purchase_orders[~purchase_orders.sku_id.isin(skus.sku_id)]
    checks.append({"check": "purchase order references known sku_id", "domain": "Supplier master",
                    "passed": bool(len(bad_po) == 0), "detail": f"{len(bad_po)} purchase orders reference an unknown SKU"})
    return pd.DataFrame(checks)


def override_tracking_summary(replenishment_decisions: pd.DataFrame) -> dict:
    total = len(replenishment_decisions)
    overrides = replenishment_decisions.override_flag.sum()
    reasons = (replenishment_decisions[replenishment_decisions.override_flag]
               .override_reason.value_counts().to_dict())
    return {
        "total_decisions": int(total), "override_count": int(overrides),
        "override_rate": round(overrides / total, 4) if total else float("nan"),
        "auto_approved_rate": round(1 - overrides / total, 4) if total else float("nan"),
        "override_reasons": reasons,
    }
