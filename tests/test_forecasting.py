import warnings

import pytest

from supply_chain.forecasting import (baseline_moving_average, build_weekly_panel,
                                       exponential_smoothing_by_sku, hierarchical_reconciliation,
                                       train_gradient_boosted, train_test_split_weekly)
from supply_chain.metrics import forecast_accuracy

warnings.filterwarnings("ignore")


@pytest.fixture(scope="module")
def weekly_panel(supply_chain_data):
    data = supply_chain_data
    return build_weekly_panel(data["daily_sales"], data["skus"], data["stores"], data["holidays"], data["weather"])


def test_weekly_panel_has_expected_shape_and_no_leakage(weekly_panel):
    assert len(weekly_panel) > 0
    assert {"lag_1", "lag_4", "rolling_mean_4", "week_sin", "week_cos"}.issubset(weekly_panel.columns)


def test_train_test_split_is_time_ordered(weekly_panel):
    train, test = train_test_split_weekly(weekly_panel, test_weeks=4)
    assert train.week.max() < test.week.min()


def test_baseline_forecast_produces_bounded_accuracy(weekly_panel):
    train, test = train_test_split_weekly(weekly_panel, test_weeks=4)
    baseline_test = baseline_moving_average(train, test)
    acc = forecast_accuracy(baseline_test.units_sold, baseline_test.forecast_units)
    assert 0 <= acc["wmape"] <= 2


def test_gradient_boosted_model_trains_and_predicts_non_negative(weekly_panel):
    train, test = train_test_split_weekly(weekly_panel, test_weeks=4)
    _, gbm_test = train_gradient_boosted(train, test)
    assert (gbm_test.forecast_units >= 0).all()
    acc = forecast_accuracy(gbm_test.units_sold, gbm_test.forecast_units)
    assert 0 <= acc["wmape"] <= 2


def test_hierarchical_reconciliation_improves_or_holds_at_higher_levels(weekly_panel):
    train, test = train_test_split_weekly(weekly_panel, test_weeks=4)
    baseline_test = baseline_moving_average(train, test)
    _, gbm_test = train_gradient_boosted(train, test)
    ets_test = exponential_smoothing_by_sku(weekly_panel, test_weeks=4)
    reconciliation = hierarchical_reconciliation(gbm_test, ets_test, baseline_test)
    bottom_up = reconciliation[reconciliation.method == "Bottom-up (GBM)"].set_index("level")
    # Aggregating up the hierarchy should never make WMAPE worse - averaging
    # out store-SKU level noise is the entire point of a hierarchy.
    assert bottom_up.loc["Total", "wmape"] <= bottom_up.loc["Store-SKU", "wmape"]
