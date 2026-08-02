import pandas as pd

from supply_chain.metrics import (economic_order_quantity, forecast_accuracy, psi,
                                   reorder_point, safety_stock, wmape)


def test_wmape_zero_for_perfect_forecast():
    actual = pd.Series([10, 20, 30])
    assert wmape(actual, actual) == 0.0


def test_wmape_bounded_and_directional():
    actual = pd.Series([10, 20, 30])
    forecast = pd.Series([15, 15, 15])
    assert wmape(actual, forecast) > 0


def test_forecast_accuracy_returns_expected_keys():
    result = forecast_accuracy(pd.Series([10, 20, 30]), pd.Series([12, 18, 33]))
    assert set(result) == {"wmape", "mape", "bias", "accuracy_pct"}
    assert 0 <= result["wmape"] <= 1


def test_psi_detects_shift():
    ref = pd.Series(range(200))
    cur = pd.Series(range(200, 400))
    assert psi(ref, cur) > 0.25


def test_psi_near_zero_for_identical_distributions():
    ref = pd.Series(range(200))
    assert psi(ref, ref) < 0.05


def test_safety_stock_increases_with_variability():
    low = safety_stock(demand_std=1, lead_time_days=7, lead_time_std=0.5, demand_mean=10, z=1.65)
    high = safety_stock(demand_std=5, lead_time_days=7, lead_time_std=3, demand_mean=10, z=1.65)
    assert high > low


def test_reorder_point_includes_safety_stock():
    rop_no_ss = reorder_point(demand_mean=10, lead_time_days=5, ss=0)
    rop_with_ss = reorder_point(demand_mean=10, lead_time_days=5, ss=20)
    assert rop_with_ss == rop_no_ss + 20


def test_eoq_is_non_negative():
    assert economic_order_quantity(annual_demand=3650, order_cost=45, holding_cost_per_unit=2.2) > 0
    assert economic_order_quantity(annual_demand=0, order_cost=45, holding_cost_per_unit=2.2) == 0
