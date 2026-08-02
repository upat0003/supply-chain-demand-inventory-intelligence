from pathlib import Path

from supply_chain.governance import (override_tracking_summary, run_data_quality_checks,
                                      validate_master_data)

RULES_PATH = Path(__file__).resolve().parent.parent / "governance/data_quality_rules.yml"


def test_data_quality_rules_execute_and_detect_known_defects(supply_chain_data):
    results = run_data_quality_checks(RULES_PATH, supply_chain_data)
    assert len(results) == 11
    failed = set(results[~results.passed].id)
    # DQ-006 (bad SKU reference) and DQ-007 (missing unit cost) are deliberately
    # injected defects that the rule set must catch, not silently pass.
    assert "DQ-006" in failed
    assert "DQ-007" in failed
    # a critical uniqueness/referential rule on clean master data must pass
    assert results.loc[results.id == "DQ-001", "passed"].iloc[0]


def test_master_data_validation_flags_orphan_purchase_orders(supply_chain_data):
    data = supply_chain_data
    checks = validate_master_data(data["products"], data["skus"], data["stores"],
                                   data["warehouses"], data["suppliers"], data["purchase_orders"])
    failing = checks[~checks.passed]
    assert "purchase order references known sku_id" in failing.check.tolist()


def test_override_tracking_summary_is_consistent(supply_chain_data):
    summary = override_tracking_summary(supply_chain_data["replenishment_decisions"])
    assert summary["total_decisions"] > 0
    assert 0 <= summary["override_rate"] <= 1
    assert abs(summary["override_rate"] + summary["auto_approved_rate"] - 1) < 1e-9
