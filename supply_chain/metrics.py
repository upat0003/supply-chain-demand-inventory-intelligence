"""Shared forecast-accuracy, inventory and drift metric functions.

Kept dependency-free (pandas/numpy only) so the same functions can run inside
the pipeline, the test suite, or a Fabric notebook without pulling in the
heavier modelling libraries.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def wmape(actual: pd.Series, forecast: pd.Series) -> float:
    """Weighted mean absolute percentage error - the standard demand-planning
    accuracy metric because it is not distorted by low-volume periods the way
    plain MAPE is."""
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    denom = np.abs(actual).sum()
    if denom == 0:
        return float("nan")
    return float(np.abs(actual - forecast).sum() / denom)


def mape(actual: pd.Series, forecast: pd.Series, epsilon: float = 1e-6) -> float:
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    mask = np.abs(actual) > epsilon
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - forecast[mask]) / actual[mask])))


def bias(actual: pd.Series, forecast: pd.Series) -> float:
    """Signed mean error as a share of average actual demand. Positive means
    the forecast systematically over-predicts; negative means under-predicts."""
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    mean_actual = actual.mean()
    if mean_actual == 0:
        return float("nan")
    return float((forecast - actual).mean() / mean_actual)


def forecast_accuracy(actual: pd.Series, forecast: pd.Series) -> dict:
    return {
        "wmape": round(wmape(actual, forecast), 4),
        "mape": round(mape(actual, forecast), 4),
        "bias": round(bias(actual, forecast), 4),
        "accuracy_pct": round((1 - wmape(actual, forecast)) * 100, 2),
    }


def psi(reference: pd.Series, current: pd.Series, buckets: int = 10) -> float:
    """Population stability index between a reference and current distribution."""
    reference = pd.Series(reference).dropna()
    current = pd.Series(current).dropna()
    if len(reference) < 10 or len(current) < 10:
        return float("nan")
    quantiles = np.linspace(0, 1, buckets + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    if len(edges) < 3:
        return 0.0
    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)
    ref_pct = np.clip(ref_counts / max(ref_counts.sum(), 1), 1e-4, None)
    cur_pct = np.clip(cur_counts / max(cur_counts.sum(), 1), 1e-4, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def safety_stock(demand_std: float, lead_time_days: float, lead_time_std: float,
                  demand_mean: float, z: float) -> float:
    """Safety stock accounting for variability in both demand and lead time -
    the standard combined-variance formulation used in inventory planning."""
    variance = lead_time_days * (demand_std ** 2) + (demand_mean ** 2) * (lead_time_std ** 2)
    return float(z * np.sqrt(max(variance, 0.0)))


def reorder_point(demand_mean: float, lead_time_days: float, ss: float) -> float:
    return float(demand_mean * lead_time_days + ss)


def economic_order_quantity(annual_demand: float, order_cost: float, holding_cost_per_unit: float) -> float:
    if holding_cost_per_unit <= 0 or annual_demand <= 0:
        return 0.0
    return float(np.sqrt((2 * annual_demand * order_cost) / holding_cost_per_unit))


def inventory_turns(cogs_annual: float, avg_inventory_value: float) -> float:
    if avg_inventory_value <= 0:
        return float("nan")
    return float(cogs_annual / avg_inventory_value)
