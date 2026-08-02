import warnings

import pandas as pd

from supply_chain.anomaly import detect_anomalies
from supply_chain.inventory import build_reorder_recommendations, run_scenarios
from supply_chain.risk import train_lead_time_risk_model
from supply_chain.uplift import estimate_promotion_uplift, uplift_summary_by_type

warnings.filterwarnings("ignore")


def _demand_stats(daily_sales: pd.DataFrame) -> pd.DataFrame:
    stats = daily_sales.groupby(["store_id", "sku_id"]).units_sold.agg(["mean", "std"]).reset_index()
    stats.columns = ["store_id", "sku_id", "demand_mean", "demand_std"]
    stats["demand_std"] = stats["demand_std"].fillna(stats["demand_mean"] * 0.3)
    return stats


def test_reorder_recommendations_are_internally_consistent(supply_chain_data):
    data = supply_chain_data
    stats = _demand_stats(data["daily_sales"])
    rec = build_reorder_recommendations(stats, data["lead_times"], data["skus"])
    assert (rec.safety_stock_units >= 0).all()
    assert (rec.reorder_point_units >= rec.safety_stock_units - 1e-6).all()


def test_scenarios_increase_safety_stock_under_stress(supply_chain_data):
    data = supply_chain_data
    stats = _demand_stats(data["daily_sales"])
    rec = build_reorder_recommendations(stats, data["lead_times"], data["skus"])
    scenarios = run_scenarios(rec)
    baseline_ss = scenarios.loc[scenarios.scenario == "Baseline", "avg_safety_stock_units"].iloc[0]
    disruption_ss = scenarios.loc[
        scenarios.scenario == "Supplier disruption (+50% lead time)", "avg_safety_stock_units"].iloc[0]
    assert disruption_ss > baseline_ss


def test_anomaly_detection_flags_injected_negative_on_hand(supply_chain_data):
    anomalies = detect_anomalies(supply_chain_data["inventory_snapshots"])
    assert "Negative on-hand (data defect)" in anomalies.anomaly_type.tolist()


def test_lead_time_risk_model_produces_valid_auc(supply_chain_data):
    data = supply_chain_data
    _, metrics, importance, supplier_risk, _ = train_lead_time_risk_model(
        data["purchase_orders"], data["suppliers"], data["skus"])
    assert 0 <= metrics["auc"] <= 1
    assert len(importance) == 6
    assert len(supplier_risk) > 0


def test_promotion_uplift_estimates_are_reasonable(supply_chain_data):
    data = supply_chain_data
    detail = estimate_promotion_uplift(data["daily_sales"], data["promotions"], data["skus"])
    if len(detail):
        summary = uplift_summary_by_type(detail)
        assert (summary.events > 0).all()
