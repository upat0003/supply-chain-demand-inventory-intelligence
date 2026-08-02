"""Safety stock, reorder points and inventory scenario modelling.

Uses the forecast error and lead-time variability actually observed in the
generated data (not assumed constants) to size safety stock, so a change in
supplier reliability or forecast accuracy flows straight through to the
recommended reorder points.
"""
from __future__ import annotations

import pandas as pd

from .config import DEFAULT_SERVICE_LEVEL_Z
from .metrics import economic_order_quantity, reorder_point, safety_stock


def build_reorder_recommendations(demand_stats: pd.DataFrame, lead_times: pd.DataFrame,
                                   skus: pd.DataFrame, z: float = DEFAULT_SERVICE_LEVEL_Z) -> pd.DataFrame:
    """demand_stats: one row per store_id/sku_id with demand_mean, demand_std
    (both daily, from recent actuals). lead_times: per supplier/sku observed
    lead-time mean and std."""
    sku_supplier = skus[["sku_id"]].merge(lead_times, on="sku_id", how="left")
    merged = demand_stats.merge(
        sku_supplier[["sku_id", "supplier_id", "observed_avg_lead_time_days", "observed_std_lead_time_days", "on_time_rate"]],
        on="sku_id", how="left")
    merged["observed_avg_lead_time_days"] = merged["observed_avg_lead_time_days"].fillna(
        merged["observed_avg_lead_time_days"].median())
    merged["observed_std_lead_time_days"] = merged["observed_std_lead_time_days"].fillna(1.5)

    rows = []
    for _, r in merged.iterrows():
        ss = safety_stock(r.demand_std, r.observed_avg_lead_time_days, r.observed_std_lead_time_days,
                           r.demand_mean, z)
        rop = reorder_point(r.demand_mean, r.observed_avg_lead_time_days, ss)
        annual_demand = r.demand_mean * 365
        eoq = economic_order_quantity(annual_demand, order_cost=45.0, holding_cost_per_unit=max(r.demand_mean, 0.1) * 0.22)
        rows.append({
            "store_id": r.store_id, "sku_id": r.sku_id, "demand_mean_daily": round(r.demand_mean, 2),
            "demand_std_daily": round(r.demand_std, 2), "lead_time_days": round(r.observed_avg_lead_time_days, 1),
            "lead_time_std_days": round(r.observed_std_lead_time_days, 2),
            "service_level_z": z, "safety_stock_units": round(ss, 1),
            "reorder_point_units": round(rop, 1), "economic_order_qty_units": round(eoq, 0),
            "supplier_on_time_rate": r.get("on_time_rate", None),
        })
    return pd.DataFrame(rows)


def scenario_model(recommendations: pd.DataFrame, demand_shock_pct: float = 0.0,
                    lead_time_shock_pct: float = 0.0, z: float = DEFAULT_SERVICE_LEVEL_Z) -> pd.DataFrame:
    """Recompute safety stock and reorder points under a demand or supply shock,
    e.g. a promotional surge or a supplier disruption, for planning what-if analysis."""
    scenario = recommendations.copy()
    scenario["demand_mean_daily"] *= (1 + demand_shock_pct)
    scenario["demand_std_daily"] *= (1 + max(demand_shock_pct, 0) * 0.6 + abs(min(demand_shock_pct, 0)) * 0.3)
    scenario["lead_time_days"] *= (1 + lead_time_shock_pct)
    scenario["lead_time_std_days"] *= (1 + max(lead_time_shock_pct, 0) * 0.8)
    ss = [safety_stock(row.demand_std_daily, row.lead_time_days, row.lead_time_std_days, row.demand_mean_daily, z)
          for row in scenario.itertuples()]
    scenario["safety_stock_units"] = [round(s, 1) for s in ss]
    scenario["reorder_point_units"] = [round(reorder_point(row.demand_mean_daily, row.lead_time_days, s), 1)
                                        for row, s in zip(scenario.itertuples(), ss)]
    return scenario


def run_scenarios(recommendations: pd.DataFrame) -> pd.DataFrame:
    scenarios = {
        "Baseline": (0.0, 0.0),
        "Promotional demand surge (+35%)": (0.35, 0.0),
        "Supplier disruption (+50% lead time)": (0.0, 0.50),
        "Combined peak-season stress": (0.25, 0.30),
        "Demand slowdown (-20%)": (-0.20, 0.0),
    }
    frames = []
    for name, (d_shock, l_shock) in scenarios.items():
        s = scenario_model(recommendations, d_shock, l_shock)
        summary = pd.DataFrame([{
            "scenario": name, "demand_shock_pct": d_shock, "lead_time_shock_pct": l_shock,
            "avg_safety_stock_units": round(s.safety_stock_units.mean(), 1),
            "avg_reorder_point_units": round(s.reorder_point_units.mean(), 1),
            "total_safety_stock_units": round(s.safety_stock_units.sum(), 0),
        }])
        frames.append(summary)
    return pd.concat(frames, ignore_index=True)
