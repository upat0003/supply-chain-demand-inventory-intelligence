"""Model performance and data drift monitoring.

Produces the same kind of weekly control-log output an MLOps/monitoring job
on Fabric would write to a monitoring lakehouse table: rolling forecast
accuracy, population stability index on demand and key features, and a
status (Healthy / Warning / Critical) against the thresholds in
configs/monitoring_thresholds.yml.
"""
from __future__ import annotations

import pandas as pd

from .metrics import psi, wmape

THRESHOLDS = {
    "wmape_warning": 0.20, "wmape_critical": 0.28,
    "psi_warning": 0.10, "psi_critical": 0.25,
    "dq_pass_rate_warning": 0.97, "dq_pass_rate_critical": 0.93,
    "late_delivery_rate_warning": 0.20, "late_delivery_rate_critical": 0.30,
}


def _status(value: float, warning: float, critical: float, higher_is_worse: bool = True) -> str:
    if pd.isna(value):
        return "Unknown"
    if higher_is_worse:
        if value >= critical:
            return "Critical"
        if value >= warning:
            return "Warning"
        return "Healthy"
    if value <= critical:
        return "Critical"
    if value <= warning:
        return "Warning"
    return "Healthy"


def rolling_forecast_performance(test_frame: pd.DataFrame) -> pd.DataFrame:
    """Weekly WMAPE trend over the holdout weeks, as the monitoring job would
    compute it once actuals land."""
    rows = []
    for week, g in test_frame.groupby("week"):
        w = wmape(g.units_sold, g.forecast_units)
        rows.append({"week": week, "wmape": round(w, 4), "n_series": len(g),
                     "status": _status(w, THRESHOLDS["wmape_warning"], THRESHOLDS["wmape_critical"])})
    return pd.DataFrame(rows).sort_values("week")


def demand_drift(panel: pd.DataFrame, reference_weeks: int = 12) -> pd.DataFrame:
    """PSI on total weekly demand and on average price/promo intensity between
    an early reference window and the most recent window."""
    weeks = sorted(panel.week.unique())
    if len(weeks) < reference_weeks * 2:
        reference_weeks = max(4, len(weeks) // 3)
    ref_weeks = weeks[:reference_weeks]
    cur_weeks = weeks[-reference_weeks:]

    rows = []
    for feature in ["units_sold", "unit_price", "avg_temp_c"]:
        ref = panel[panel.week.isin(ref_weeks)][feature]
        cur = panel[panel.week.isin(cur_weeks)][feature]
        value = psi(ref, cur)
        rows.append({"feature": feature, "psi": round(value, 4),
                     "status": _status(value, THRESHOLDS["psi_warning"], THRESHOLDS["psi_critical"])})
    return pd.DataFrame(rows)


def data_quality_status(dq_results: pd.DataFrame) -> str:
    pass_rate = dq_results.pass_rate.mean()
    return _status(pass_rate, THRESHOLDS["dq_pass_rate_warning"], THRESHOLDS["dq_pass_rate_critical"],
                    higher_is_worse=False)


def supplier_delivery_status(lead_times: pd.DataFrame) -> pd.DataFrame:
    lt = lead_times.copy()
    lt["late_rate"] = 1 - lt["on_time_rate"]
    lt["status"] = lt["late_rate"].apply(
        lambda v: _status(v, THRESHOLDS["late_delivery_rate_warning"], THRESHOLDS["late_delivery_rate_critical"]))
    return lt


def build_monitoring_summary(forecast_perf: pd.DataFrame, drift: pd.DataFrame, dq_status: str,
                              risk_auc: float, anomaly_count: int) -> dict:
    latest_wmape = forecast_perf.iloc[-1].wmape if len(forecast_perf) else float("nan")
    return {
        "latest_weekly_wmape": latest_wmape,
        "forecast_status": forecast_perf.iloc[-1].status if len(forecast_perf) else "Unknown",
        "max_feature_psi": float(drift.psi.max()) if len(drift) else float("nan"),
        "drift_status": drift.sort_values("psi", ascending=False).iloc[0].status if len(drift) else "Unknown",
        "data_quality_status": dq_status,
        "lead_time_risk_model_auc": risk_auc,
        "open_inventory_anomalies": anomaly_count,
        "thresholds": THRESHOLDS,
    }
