"""Fabric-notebook-equivalent entrypoint: build the weekly demand feature panel
used by every forecasting model, and write it to data/processed for reuse
without recomputation.

Run: python -m python.features.build_demand_panel
"""
from __future__ import annotations

import pandas as pd

from supply_chain.config import ROOT
from supply_chain.forecasting import build_weekly_panel


def main() -> None:
    raw = ROOT / "data/raw"
    daily_sales = pd.read_csv(raw / "daily_sales.csv")
    skus = pd.read_csv(raw / "skus.csv")
    stores = pd.read_csv(raw / "stores.csv")
    holidays = pd.read_csv(raw / "holidays.csv")
    weather = pd.read_csv(raw / "weather.csv")

    panel = build_weekly_panel(daily_sales, skus, stores, holidays, weather)
    out_path = ROOT / "data/processed/weekly_demand_panel.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_path, index=False)
    print(f"Weekly demand panel: {panel.shape[0]} rows, {panel.shape[1]} columns -> {out_path}")


if __name__ == "__main__":
    main()
