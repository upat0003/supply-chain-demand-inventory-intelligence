"""Shared pytest fixtures. Uses a deliberately small scale configuration so
the full test suite runs in seconds, while still exercising every table and
every documented data-quality defect."""
from __future__ import annotations

import warnings

import pytest

from supply_chain.config import ScaleConfig
from supply_chain.synthetic import generate_supply_chain

warnings.filterwarnings("ignore")

TEST_SCALE = ScaleConfig(
    n_products=10, n_skus=14, n_stores=5, n_warehouses=3, n_suppliers=4,
    history_days=150, assortment_rate=0.85, end_date=__import__("datetime").date(2026, 7, 31),
)


@pytest.fixture(scope="session")
def supply_chain_data():
    return generate_supply_chain(TEST_SCALE, seed=7)
