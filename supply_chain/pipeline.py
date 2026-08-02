"""End-to-end local pipeline: generate -> bronze -> silver -> gold -> models ->
governance -> monitoring -> Power BI export.

Mirrors what would run as a scheduled Fabric notebook / Data Factory
pipeline: DuckDB stands in for the Fabric Warehouse, and the bronze/silver/
gold SQL scripts in sql/ are executed verbatim against it so the medallion
boundaries are real, inspectable SQL rather than an implicit pandas chain.
"""
from __future__ import annotations

import argparse
import json
import logging
import warnings
from pathlib import Path

import duckdb
import joblib
import pandas as pd

from . import anomaly, forecasting, governance, inventory, monitoring, risk, uplift
from .config import ARTIFACTS_DIR, MODEL_DIR, ROOT, SCALES, TARGETS
from .synthetic import generate_supply_chain, write_raw

LOG = logging.getLogger("supply_chain")


def _run_sql_layer(con: duckdb.DuckDBPyConnection, sql_path: Path) -> None:
    # Strip full-line comments first so a semicolon mentioned in prose (e.g.
    # "a physical impossibility (system sync defect); clip to zero...") is
    # never mistaken for a statement terminator.
    lines = [ln for ln in sql_path.read_text().splitlines() if not ln.strip().startswith("--")]
    sql = "\n".join(lines)
    for statement in [s.strip() for s in sql.split(";")]:
        if statement:
            con.execute(statement)


def build_warehouse(root: Path) -> duckdb.DuckDBPyConnection:
    import os
    (root / "data/processed").mkdir(parents=True, exist_ok=True)
    db_path = root / "data/processed/supply_chain.duckdb"
    con = duckdb.connect(str(db_path))
    os.chdir(root)  # sql/*.sql reference paths (e.g. data/raw/...) relative to the project root
    for layer in ["bronze", "silver", "gold"]:
        folder = root / "sql" / layer
        for sql_file in sorted(folder.glob("*.sql")):
            _run_sql_layer(con, sql_file)
            LOG.info("Executed %s", sql_file.relative_to(root))
    return con


def compute_business_kpis(data: dict, dq_results: pd.DataFrame, forecast_metrics: dict,
                           override_summary: dict) -> dict:
    daily_sales = data["daily_sales"]
    stock_outs = data["stock_outs"]
    inventory_snapshots = data["inventory_snapshots"]
    skus = data["skus"]

    stockout_rate = len(stock_outs) / len(daily_sales) if len(daily_sales) else float("nan")

    store_inv = inventory_snapshots[inventory_snapshots.location_type == "Store"]
    excess_threshold_days = 6  # a fast-turn grocery network norm; see configs/monitoring_thresholds.yml
    excess_rate = (store_inv.days_of_supply > excess_threshold_days).mean() if len(store_inv) else float("nan")

    sales_cost = daily_sales.merge(skus[["sku_id", "unit_cost"]], on="sku_id", how="left")
    history_days = pd.to_datetime(daily_sales.date).max() - pd.to_datetime(daily_sales.date).min()
    n_days = max(history_days.days, 1)
    cogs_annual = (sales_cost.units_sold * sales_cost.unit_cost).sum() * (365 / n_days)
    unit_cost_map = skus.set_index("sku_id").unit_cost
    row_value = store_inv.on_hand_units.clip(lower=0) * store_inv.sku_id.map(unit_cost_map)
    inv_value = row_value.groupby(store_inv.date).sum().mean() if len(store_inv) else float("nan")
    turns = cogs_annual / inv_value if inv_value else float("nan")

    dq_pass_rate = dq_results.pass_rate.mean()
    annual_lost_sales = float(stock_outs.lost_sales_revenue_estimate.sum()) * (365 / n_days)

    kpis = {
        "stockout_rate_baseline": round(float(stockout_rate), 4),
        "stockout_rate_target": round(float(stockout_rate) * (1 - TARGETS["stockout_rate_reduction_high"]), 4),
        "excess_inventory_rate_baseline": round(float(excess_rate), 4),
        "excess_inventory_rate_target": round(float(excess_rate) * (1 - TARGETS["excess_inventory_reduction_high"]), 4),
        "inventory_turns_baseline": round(float(turns), 2) if pd.notna(turns) else None,
        "inventory_turns_target": round(float(turns) * (1 + TARGETS["inventory_turns_improvement"]), 2) if pd.notna(turns) else None,
        "forecast_wmape_baseline": forecast_metrics.get("baseline_wmape"),
        "forecast_wmape_advanced": forecast_metrics.get("gbm_wmape"),
        "forecast_accuracy_relative_improvement_pct": forecast_metrics.get("relative_improvement_pct"),
        "manual_override_rate_baseline": override_summary.get("override_rate"),
        "data_quality_pass_rate": round(float(dq_pass_rate), 4),
        "annualised_cogs_estimate_aud": round(float(cogs_annual), 0),
        "annual_lost_sales_estimate_aud": round(annual_lost_sales, 0),
        "targets": TARGETS,
    }
    return kpis


def run(scale: str = "dev", seed: int = 42, root: Path | None = None) -> dict:
    warnings.filterwarnings("ignore")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    root = root or ROOT
    cfg = SCALES[scale]

    LOG.info("Generating synthetic supply chain data (scale=%s, seed=%s)", scale, seed)
    data = generate_supply_chain(cfg, seed=seed)
    write_raw(data, root / "data/raw")

    LOG.info("Building bronze/silver/gold layers in DuckDB")
    con = build_warehouse(root)

    LOG.info("Running governance data-quality checks")
    dq_results = governance.run_data_quality_checks(root / "governance/data_quality_rules.yml", data)
    master_data_checks = governance.validate_master_data(
        data["products"], data["skus"], data["stores"], data["warehouses"], data["suppliers"], data["purchase_orders"])
    override_summary = governance.override_tracking_summary(data["replenishment_decisions"])

    LOG.info("Building weekly demand panel and training forecast models")
    panel = forecasting.build_weekly_panel(data["daily_sales"], data["skus"], data["stores"],
                                            data["holidays"], data["weather"])
    train, test = forecasting.train_test_split_weekly(panel)
    baseline_test = forecasting.baseline_moving_average(train, test)
    model, gbm_test = forecasting.train_gradient_boosted(train, test)
    ets_test = forecasting.exponential_smoothing_by_sku(panel)
    reconciliation = forecasting.hierarchical_reconciliation(gbm_test, ets_test, baseline_test)

    from .metrics import forecast_accuracy as _facc
    baseline_acc = _facc(baseline_test.units_sold, baseline_test.forecast_units)
    gbm_acc = _facc(gbm_test.units_sold, gbm_test.forecast_units)
    ets_acc = _facc(ets_test.actual_units, ets_test.forecast_units)
    relative_improvement = round((baseline_acc["wmape"] - gbm_acc["wmape"]) / baseline_acc["wmape"] * 100, 2)
    forecast_metrics = {
        "baseline_wmape": baseline_acc["wmape"], "gbm_wmape": gbm_acc["wmape"], "ets_wmape": ets_acc["wmape"],
        "baseline_accuracy_pct": baseline_acc["accuracy_pct"], "gbm_accuracy_pct": gbm_acc["accuracy_pct"],
        "ets_accuracy_pct": ets_acc["accuracy_pct"], "relative_improvement_pct": relative_improvement,
    }
    LOG.info("Forecast accuracy - baseline WMAPE %.4f, gradient-boosted WMAPE %.4f (%.1f%% relative improvement)",
              baseline_acc["wmape"], gbm_acc["wmape"], relative_improvement)

    LOG.info("Computing safety stock and reorder-point recommendations")
    recent_cutoff = pd.to_datetime(data["daily_sales"].date).max() - pd.Timedelta(days=56)
    recent_sales = data["daily_sales"][pd.to_datetime(data["daily_sales"].date) > recent_cutoff]
    demand_stats = recent_sales.groupby(["store_id", "sku_id"]).units_sold.agg(["mean", "std"]).reset_index()
    demand_stats.columns = ["store_id", "sku_id", "demand_mean", "demand_std"]
    demand_stats["demand_std"] = demand_stats["demand_std"].fillna(demand_stats["demand_mean"] * 0.3)
    reorder_recommendations = inventory.build_reorder_recommendations(demand_stats, data["lead_times"], data["skus"])
    scenarios = inventory.run_scenarios(reorder_recommendations)

    LOG.info("Detecting inventory anomalies")
    anomalies = anomaly.detect_anomalies(data["inventory_snapshots"])

    LOG.info("Estimating promotion uplift")
    uplift_detail = uplift.estimate_promotion_uplift(data["daily_sales"], data["promotions"], data["skus"])
    uplift_summary = uplift.uplift_summary_by_type(uplift_detail)

    LOG.info("Training lead-time risk model")
    risk_model, risk_metrics, risk_importance, supplier_risk, risk_scored = risk.train_lead_time_risk_model(
        data["purchase_orders"], data["suppliers"], data["skus"])

    LOG.info("Running monitoring controls")
    forecast_perf = monitoring.rolling_forecast_performance(gbm_test)
    drift = monitoring.demand_drift(panel)
    dq_status = monitoring.data_quality_status(dq_results)
    supplier_status = monitoring.supplier_delivery_status(data["lead_times"])
    monitoring_summary = monitoring.build_monitoring_summary(
        forecast_perf, drift, dq_status, risk_metrics["auc"], len(anomalies))

    kpis = compute_business_kpis(data, dq_results, forecast_metrics, override_summary)

    LOG.info("Exporting Power BI datasets")
    export = root / "powerbi/data"
    export.mkdir(parents=True, exist_ok=True)

    fact_sales = data["daily_sales"].merge(data["skus"][["sku_id", "category", "subcategory", "unit_price", "unit_cost"]], on="sku_id") \
        .merge(data["stores"][["store_id", "region", "store_format", "warehouse_id"]], on="store_id")
    fact_sales.to_csv(export / "fact_daily_sales.csv", index=False)
    data["stock_outs"].to_csv(export / "fact_stockouts.csv", index=False)
    data["inventory_snapshots"].to_csv(export / "fact_inventory.csv", index=False)
    data["purchase_orders"].to_csv(export / "fact_purchase_orders.csv", index=False)
    data["replenishment_decisions"].to_csv(export / "fact_replenishment_decisions.csv", index=False)
    reorder_recommendations.to_csv(export / "reorder_recommendations.csv", index=False)
    scenarios.to_csv(export / "scenario_model.csv", index=False)
    anomalies.to_csv(export / "inventory_anomalies.csv", index=False)
    uplift_detail.to_csv(export / "promotion_uplift_detail.csv", index=False)
    uplift_summary.to_csv(export / "promotion_uplift_summary.csv", index=False)
    reconciliation.to_csv(export / "forecast_reconciliation.csv", index=False)
    forecast_perf.to_csv(export / "forecast_monitoring_weekly.csv", index=False)
    drift.to_csv(export / "drift_metrics.csv", index=False)
    dq_results.to_csv(export / "data_quality_results.csv", index=False)
    master_data_checks.to_csv(export / "master_data_checks.csv", index=False)
    supplier_risk.to_csv(export / "supplier_risk_scores.csv", index=False)
    risk_importance.to_csv(export / "lead_time_risk_feature_importance.csv", index=False)
    supplier_status.to_csv(export / "supplier_delivery_status.csv", index=False)
    data["suppliers"].to_csv(export / "dim_suppliers.csv", index=False)
    data["skus"].merge(data["products"][["product_id", "brand", "shelf_life_days"]], on="product_id") \
        .to_csv(export / "dim_products.csv", index=False)
    data["stores"].to_csv(export / "dim_stores.csv", index=False)

    combo_test = gbm_test.merge(baseline_test[["store_id", "sku_id", "week", "forecast_units"]],
                                 on=["store_id", "sku_id", "week"], suffixes=("_gbm", "_baseline"))
    combo_test.rename(columns={"forecast_units_gbm": "forecast_units_advanced",
                                "forecast_units_baseline": "forecast_units_baseline"}, inplace=True)
    combo_test.to_csv(export / "forecast_detail.csv", index=False)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_DIR / "demand_gbm.joblib")
    joblib.dump(risk_model, MODEL_DIR / "lead_time_risk.joblib")

    supplier_scorecard = con.execute((root / "sql/analytics/01_supplier_scorecard.sql").read_text()).df()
    inventory_health = con.execute((root / "sql/analytics/02_inventory_health_summary.sql").read_text()).df()
    (root / "data/samples").mkdir(parents=True, exist_ok=True)
    supplier_scorecard.to_csv(root / "data/samples/supplier_scorecard.csv", index=False)
    inventory_health.to_csv(root / "data/samples/inventory_health_summary.csv", index=False)
    con.close()

    ARTIFACTS_DIR.mkdir(exist_ok=True)
    run_summary = {
        "scale": scale, "seed": seed,
        "rows": {name: len(df) for name, df in data.items()},
        "forecast_metrics": forecast_metrics,
        "reconciliation": reconciliation.to_dict(orient="records"),
        "risk_model_metrics": risk_metrics,
        "monitoring_summary": {k: v for k, v in monitoring_summary.items() if k != "thresholds"},
        "governance": {
            "data_quality_pass_rate": round(float(dq_results.pass_rate.mean()), 4),
            "data_quality_rules_failed": dq_results[~dq_results.passed].id.tolist(),
            "master_data_checks_failed": master_data_checks[~master_data_checks.passed].check.tolist(),
            "override_summary": override_summary,
        },
        "business_kpis": kpis,
        "inventory_anomalies_detected": int(len(anomalies)),
        "promotion_events_evaluated": int(len(uplift_detail)),
    }
    (ARTIFACTS_DIR / "run_summary.json").write_text(json.dumps(run_summary, indent=2, default=str))
    LOG.info("Pipeline complete. Run summary written to artifacts/run_summary.json")
    return run_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the supply chain demand and inventory intelligence pipeline")
    parser.add_argument("--scale", choices=list(SCALES), default="dev")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    run(args.scale, args.seed, args.root)
