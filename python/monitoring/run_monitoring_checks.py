"""Fabric-notebook-equivalent entrypoint: run the weekly monitoring controls
(forecast performance trend, demand/feature drift, supplier delivery status)
against the current data/raw extracts and print a control-log summary.

Run: python -m python.monitoring.run_monitoring_checks
"""
from __future__ import annotations

import warnings

import pandas as pd

from supply_chain.config import ROOT
from supply_chain.forecasting import (build_weekly_panel, train_gradient_boosted,
                                       train_test_split_weekly)
from supply_chain.monitoring import demand_drift, rolling_forecast_performance, supplier_delivery_status


def main() -> None:
    warnings.filterwarnings("ignore")
    raw = ROOT / "data/raw"
    daily_sales = pd.read_csv(raw / "daily_sales.csv")
    skus = pd.read_csv(raw / "skus.csv")
    stores = pd.read_csv(raw / "stores.csv")
    holidays = pd.read_csv(raw / "holidays.csv")
    weather = pd.read_csv(raw / "weather.csv")
    lead_times = pd.read_csv(raw / "lead_times.csv")

    panel = build_weekly_panel(daily_sales, skus, stores, holidays, weather)
    train, test = train_test_split_weekly(panel)
    _, gbm_test = train_gradient_boosted(train, test)

    perf = rolling_forecast_performance(gbm_test)
    drift = demand_drift(panel)
    supplier_status = supplier_delivery_status(lead_times)

    print("Weekly forecast performance:\n", perf.to_string(index=False))
    print("\nDemand/feature drift:\n", drift.to_string(index=False))
    print("\nSupplier delivery status (worst 5):\n",
          supplier_status.sort_values("late_rate", ascending=False).head(5).to_string(index=False))


if __name__ == "__main__":
    main()
