"""Fabric-notebook-equivalent entrypoint: train and evaluate the baseline,
exponential-smoothing and gradient-boosted forecast models, and print the
holdout comparison. Equivalent to the forecasting stage of
supply_chain.pipeline, runnable in isolation for iteration.

Run: python -m python.models.train_forecast_models
"""
from __future__ import annotations

import warnings

import pandas as pd

from supply_chain.config import ROOT
from supply_chain.forecasting import (baseline_moving_average, build_weekly_panel,
                                       exponential_smoothing_by_sku, hierarchical_reconciliation,
                                       train_gradient_boosted, train_test_split_weekly)
from supply_chain.metrics import forecast_accuracy


def main() -> None:
    warnings.filterwarnings("ignore")
    raw = ROOT / "data/raw"
    daily_sales = pd.read_csv(raw / "daily_sales.csv")
    skus = pd.read_csv(raw / "skus.csv")
    stores = pd.read_csv(raw / "stores.csv")
    holidays = pd.read_csv(raw / "holidays.csv")
    weather = pd.read_csv(raw / "weather.csv")

    panel = build_weekly_panel(daily_sales, skus, stores, holidays, weather)
    train, test = train_test_split_weekly(panel)
    baseline_test = baseline_moving_average(train, test)
    _, gbm_test = train_gradient_boosted(train, test)
    ets_test = exponential_smoothing_by_sku(panel)
    reconciliation = hierarchical_reconciliation(gbm_test, ets_test, baseline_test)

    print("Baseline (4-week moving average):", forecast_accuracy(baseline_test.units_sold, baseline_test.forecast_units))
    print("Gradient-boosted champion:       ", forecast_accuracy(gbm_test.units_sold, gbm_test.forecast_units))
    print("Exponential smoothing (SKU-total):", forecast_accuracy(ets_test.actual_units, ets_test.forecast_units))
    print("\nHierarchical reconciliation:\n", reconciliation.to_string(index=False))


if __name__ == "__main__":
    main()
