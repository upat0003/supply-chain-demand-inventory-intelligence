"""Shared configuration and constants for the supply chain platform.

Dev mode keeps the default run small enough to regenerate and render in a
couple of minutes on a laptop. `scale=full` widens the assortment, store
network and history window to a size representative of a mid-size regional
retailer; see docs/architecture.md for the production sizing note.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REGIONS = ["VIC", "NSW", "QLD", "WA"]

CATEGORIES = {
    "Beverages": ["Soft Drinks", "Water", "Juice"],
    "Snacks": ["Chips", "Confectionery", "Biscuits"],
    "Dairy": ["Milk", "Yoghurt", "Cheese"],
    "Household": ["Laundry", "Paper Goods", "Cleaning"],
    "Personal Care": ["Oral Care", "Hair Care"],
    "Frozen": ["Frozen Meals", "Ice Cream"],
}

SUPPLY_CHAIN_SEED = 42


@dataclass(frozen=True)
class ScaleConfig:
    """Controls the size of the synthetic supply chain generated."""

    n_products: int
    n_skus: int
    n_stores: int
    n_warehouses: int
    n_suppliers: int
    history_days: int
    assortment_rate: float
    end_date: date


DEV_SCALE = ScaleConfig(
    n_products=16,
    n_skus=24,
    n_stores=8,
    n_warehouses=4,
    n_suppliers=7,
    history_days=400,
    assortment_rate=0.82,
    end_date=date(2026, 7, 31),
)

FULL_SCALE = ScaleConfig(
    n_products=60,
    n_skus=180,
    n_stores=140,
    n_warehouses=10,
    n_suppliers=45,
    history_days=1095,
    assortment_rate=0.78,
    end_date=date(2026, 7, 31),
)

SCALES = {"dev": DEV_SCALE, "full": FULL_SCALE}

# Business targets used throughout the monitoring, reporting and business-case
# layers. Baselines are computed from the generated data at pipeline run time
# and written to artifacts/run_summary.json; targets are the improvement goals
# this solution is designed against.
TARGETS = {
    "stockout_rate_reduction_low": 0.10,
    "stockout_rate_reduction_high": 0.20,
    "excess_inventory_reduction_low": 0.08,
    "excess_inventory_reduction_high": 0.15,
    "forecast_accuracy_improvement": 0.10,
    "inventory_turns_improvement": 0.05,
    "manual_effort_reduction": 0.20,
}

# Safety-stock service-level target (z-score for ~95% cycle service level)
DEFAULT_SERVICE_LEVEL_Z = 1.65

RAW_DIR = ROOT / "data/raw"
REFERENCE_DIR = ROOT / "data/reference"
PROCESSED_DIR = ROOT / "data/processed"
POWERBI_DATA_DIR = ROOT / "powerbi/data"
ARTIFACTS_DIR = ROOT / "artifacts"
MODEL_DIR = ARTIFACTS_DIR / "models"
