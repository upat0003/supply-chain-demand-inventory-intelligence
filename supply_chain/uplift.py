"""Promotion uplift estimation.

For every promoted SKU we build a same-weekday counterfactual baseline from
the three weeks immediately before the promotion starts, then compare actual
sell-through during the promotion window against that baseline. This is a
simple, auditable difference-in-differences design - deliberately not a
black box - because promotion uplift numbers feed supplier negotiations and
need to be explainable to a category manager.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def estimate_promotion_uplift(daily_sales: pd.DataFrame, promotions: pd.DataFrame,
                               skus: pd.DataFrame) -> pd.DataFrame:
    sales = daily_sales.copy()
    sales["date"] = pd.to_datetime(sales["date"])
    sales["weekday"] = sales["date"].dt.dayofweek

    rows = []
    for _, promo in promotions.iterrows():
        start = pd.Timestamp(promo.start_date)
        end = pd.Timestamp(promo.end_date)
        baseline_start = start - pd.Timedelta(days=21)
        baseline_end = start - pd.Timedelta(days=1)

        promo_sales = sales[(sales.sku_id == promo.sku_id) & (sales.date >= start) & (sales.date <= end)]
        baseline_sales = sales[(sales.sku_id == promo.sku_id) & (sales.date >= baseline_start) & (sales.date <= baseline_end)]
        if promo_sales.empty or baseline_sales.empty:
            continue

        baseline_by_weekday = baseline_sales.groupby("weekday").units_sold.mean()
        promo_sales = promo_sales.copy()
        promo_sales["expected_units"] = promo_sales["weekday"].map(baseline_by_weekday).fillna(baseline_sales.units_sold.mean())
        actual_total = promo_sales.units_sold.sum()
        expected_total = promo_sales.expected_units.sum()
        uplift_units = actual_total - expected_total
        uplift_pct = (uplift_units / expected_total) if expected_total > 0 else np.nan

        rows.append({
            "promo_id": promo.promo_id, "sku_id": promo.sku_id, "promo_type": promo.promo_type,
            "start_date": promo.start_date, "end_date": promo.end_date,
            "duration_days": int((end - start).days) + 1,
            "actual_units": int(actual_total), "expected_units_baseline": round(expected_total, 1),
            "uplift_units": round(uplift_units, 1), "uplift_pct": round(uplift_pct * 100, 1) if pd.notna(uplift_pct) else np.nan,
            "planned_uplift_pct": promo.planned_uplift_pct,
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result = result.merge(skus[["sku_id", "category"]], on="sku_id", how="left")
    return result


def uplift_summary_by_type(uplift_detail: pd.DataFrame) -> pd.DataFrame:
    if uplift_detail.empty:
        return pd.DataFrame(columns=["promo_type", "events", "avg_uplift_pct", "avg_planned_uplift_pct", "variance_pp"])
    summary = uplift_detail.groupby("promo_type").agg(
        events=("promo_id", "count"), avg_uplift_pct=("uplift_pct", "mean"),
        avg_planned_uplift_pct=("planned_uplift_pct", "mean"),
    ).reset_index()
    summary["variance_pp"] = round(summary.avg_uplift_pct - summary.avg_planned_uplift_pct, 1)
    summary["avg_uplift_pct"] = summary.avg_uplift_pct.round(1)
    summary["avg_planned_uplift_pct"] = summary.avg_planned_uplift_pct.round(1)
    return summary
