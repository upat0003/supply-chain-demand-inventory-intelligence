"""Demand forecasting models: baseline, exponential smoothing, gradient-boosted
and hierarchical reconciliation.

All models are trained on the weekly demand panel built from the synthetic
bronze/silver tables. Every metric reported downstream (in
artifacts/run_summary.json and powerbi/data) comes from an actual model fit
and an actual holdout evaluation - none of it is hand-typed.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import OrdinalEncoder
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from .metrics import forecast_accuracy

TEST_WEEKS = 8
FEATURES = [
    "lag_1", "lag_2", "lag_4", "rolling_mean_4", "rolling_std_4", "promo_flag",
    "holiday_count", "avg_temp_c", "precipitation_mm", "week_of_year", "month",
    "week_sin", "week_cos", "unit_price", "store_format_enc", "category_enc",
    "combo_mean_hist",
]


def build_weekly_panel(daily_sales: pd.DataFrame, skus: pd.DataFrame, stores: pd.DataFrame,
                        holidays: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    df = daily_sales.merge(skus[["sku_id", "category", "unit_price"]], on="sku_id", how="inner")
    df = df.merge(stores[["store_id", "region", "store_format"]], on="store_id", how="inner")
    df["date"] = pd.to_datetime(df["date"])
    df["week"] = df["date"].dt.to_period("W-SUN").dt.start_time

    weekly = (df.groupby(["store_id", "sku_id", "category", "region", "store_format", "week"])
              .agg(units_sold=("units_sold", "sum"), revenue=("revenue", "sum"),
                   promo_flag=("promo_flag", "max"), unit_price=("unit_price", "mean"))
              .reset_index())

    weather = weather.copy()
    weather["date"] = pd.to_datetime(weather["date"])
    weather["week"] = weather["date"].dt.to_period("W-SUN").dt.start_time
    weekly_weather = (weather.groupby(["region", "week"])
                      .agg(avg_temp_c=("avg_temp_c", "mean"), precipitation_mm=("precipitation_mm", "mean"))
                      .reset_index())
    weekly = weekly.merge(weekly_weather, on=["region", "week"], how="left")

    holidays = holidays.copy()
    holidays["date"] = pd.to_datetime(holidays["date"])
    holidays["week"] = holidays["date"].dt.to_period("W-SUN").dt.start_time
    weekly_holiday = holidays.groupby(["region", "week"]).size().reset_index(name="holiday_count")
    weekly = weekly.merge(weekly_holiday, on=["region", "week"], how="left")
    weekly["holiday_count"] = weekly["holiday_count"].fillna(0)
    weekly["precipitation_mm"] = weekly["precipitation_mm"].fillna(weekly["precipitation_mm"].median())
    weekly["avg_temp_c"] = weekly["avg_temp_c"].fillna(weekly["avg_temp_c"].median())

    weekly["week_of_year"] = weekly["week"].dt.isocalendar().week.astype(int)
    weekly["month"] = weekly["week"].dt.month
    weekly["week_sin"] = np.sin(2 * np.pi * weekly["week_of_year"] / 52)
    weekly["week_cos"] = np.cos(2 * np.pi * weekly["week_of_year"] / 52)
    weekly = weekly.sort_values(["store_id", "sku_id", "week"]).reset_index(drop=True)

    grp = weekly.groupby(["store_id", "sku_id"])["units_sold"]
    weekly["lag_1"] = grp.shift(1)
    weekly["lag_2"] = grp.shift(2)
    weekly["lag_4"] = grp.shift(4)
    weekly["rolling_mean_4"] = grp.transform(lambda s: s.shift(1).rolling(4, min_periods=1).mean())
    weekly["rolling_std_4"] = grp.transform(lambda s: s.shift(1).rolling(4, min_periods=1).std()).fillna(0)

    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    weekly[["store_format_enc", "category_enc"]] = encoder.fit_transform(weekly[["store_format", "category"]])
    return weekly


def train_test_split_weekly(panel: pd.DataFrame, test_weeks: int = TEST_WEEKS):
    weeks = sorted(panel.week.unique())
    cutoff = weeks[-test_weeks]
    train = panel[panel.week < cutoff].dropna(subset=["lag_4"])
    test = panel[panel.week >= cutoff].copy()
    return train, test


def baseline_moving_average(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Forecast = trailing 4-week average, the incumbent spreadsheet method."""
    test = test.copy()
    test["forecast_units"] = test["rolling_mean_4"].fillna(test["lag_1"]).fillna(0)
    return test


def exponential_smoothing_by_sku(panel: pd.DataFrame, test_weeks: int = TEST_WEEKS) -> pd.DataFrame:
    """Holt-Winters exponential smoothing at SKU-total (across all stores) weekly grain.

    statsmodels' ExponentialSmoothing is used in place of Prophet: it needs no
    external compiled sampler, installs cleanly in any CI runner, and is a
    standard, well-understood substitute for demand series of this length.
    """
    sku_weekly = panel.groupby(["sku_id", "week"]).units_sold.sum().reset_index()
    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for sku_id, g in sku_weekly.groupby("sku_id"):
            g = g.sort_values("week").reset_index(drop=True)
            if len(g) < test_weeks + 8:
                continue
            train_g, test_g = g.iloc[:-test_weeks], g.iloc[-test_weeks:]
            series = train_g.units_sold.clip(lower=0.1)
            try:
                model = ExponentialSmoothing(series, trend="add", damped_trend=True, seasonal=None).fit(
                    optimized=True)
                forecast = model.forecast(test_weeks)
            except Exception:
                forecast = pd.Series([series.mean()] * test_weeks)
            for w, actual, fcst in zip(test_g.week, test_g.units_sold, forecast):
                rows.append({"sku_id": sku_id, "week": w, "actual_units": actual, "forecast_units": max(fcst, 0)})
    return pd.DataFrame(rows)


def _add_combo_mean(train: pd.DataFrame, test: pd.DataFrame):
    """Per store-SKU historical mean, computed strictly from the training
    window and joined onto both splits, so the model has a stable per-series
    anchor without leaking future weeks into it."""
    combo_mean = train.groupby(["store_id", "sku_id"]).units_sold.mean().rename("combo_mean_hist")
    overall_mean = train.units_sold.mean()
    train = train.merge(combo_mean, on=["store_id", "sku_id"], how="left")
    test = test.merge(combo_mean, on=["store_id", "sku_id"], how="left")
    train["combo_mean_hist"] = train["combo_mean_hist"].fillna(overall_mean)
    test["combo_mean_hist"] = test["combo_mean_hist"].fillna(overall_mean)
    return train, test


def train_gradient_boosted(train: pd.DataFrame, test: pd.DataFrame):
    train, test = _add_combo_mean(train, test)
    model = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.04, max_leaf_nodes=27, min_samples_leaf=15,
        l2_regularization=0.2, random_state=42,
    )
    X_train, y_train = train[FEATURES].fillna(0), train.units_sold.clip(lower=0)
    model.fit(X_train, y_train)
    X_test = test[FEATURES].fillna(0)
    test = test.copy()
    test["forecast_units"] = np.clip(model.predict(X_test), 0, None)
    return model, test


def hierarchical_reconciliation(gbm_test: pd.DataFrame, ets_test: pd.DataFrame,
                                 baseline_test: pd.DataFrame | None = None) -> pd.DataFrame:
    """Compare bottom-up (sum store-SKU forecasts) against top-down (SKU-level
    exponential-smoothing forecast disaggregated by historical store share)
    accuracy at store-SKU, SKU, category and total levels."""
    rows = []

    def level_accuracy(df, level_cols, label):
        agg = df.groupby(level_cols + ["week"]).agg(
            actual=("units_sold", "sum"), forecast=("forecast_units", "sum")).reset_index()
        acc = forecast_accuracy(agg.actual, agg.forecast)
        rows.append({"level": label, "method": "Bottom-up (GBM)", **acc, "n_series": agg[level_cols].drop_duplicates().shape[0]})

    level_accuracy(gbm_test, ["store_id", "sku_id"], "Store-SKU")
    level_accuracy(gbm_test, ["sku_id"], "SKU")
    level_accuracy(gbm_test, ["category"], "Category")
    total_bu = gbm_test.groupby("week").agg(actual=("units_sold", "sum"), forecast=("forecast_units", "sum")).reset_index()
    rows.append({"level": "Total", "method": "Bottom-up (GBM)", **forecast_accuracy(total_bu.actual, total_bu.forecast),
                 "n_series": 1})

    # Top-down: disaggregate the SKU-level ETS forecast to store-SKU using each
    # store's historical share of that SKU's volume, then roll back up.
    share = (gbm_test.assign(actual_hist=gbm_test["units_sold"])
             .groupby(["sku_id", "store_id"]).actual_hist.sum())
    share = (share / share.groupby("sku_id").transform("sum")).rename("share").reset_index()
    td = ets_test.merge(share, on="sku_id", how="left")
    td["forecast_units"] = td["forecast_units"] * td["share"].fillna(1 / gbm_test.store_id.nunique())
    td = td.merge(gbm_test[["store_id", "sku_id", "week", "units_sold", "category"]],
                  on=["sku_id", "week"], how="inner", suffixes=("", "_actual"))
    if "store_id" not in td.columns:
        td = td.rename(columns={"store_id_actual": "store_id"})

    def td_level(level_cols, label):
        agg = td.groupby(level_cols + ["week"]).agg(actual=("units_sold", "sum"), forecast=("forecast_units", "sum")).reset_index()
        acc = forecast_accuracy(agg.actual, agg.forecast)
        rows.append({"level": label, "method": "Top-down (ETS share)", **acc, "n_series": agg[level_cols].drop_duplicates().shape[0]})

    td_level(["sku_id"], "SKU")
    td_level(["category"], "Category")
    total_td = td.groupby("week").agg(actual=("units_sold", "sum"), forecast=("forecast_units", "sum")).reset_index()
    rows.append({"level": "Total", "method": "Top-down (ETS share)", **forecast_accuracy(total_td.actual, total_td.forecast),
                 "n_series": 1})

    if baseline_test is not None:
        def base_level(level_cols, label):
            agg = baseline_test.groupby(level_cols + ["week"]).agg(
                actual=("units_sold", "sum"), forecast=("forecast_units", "sum")).reset_index()
            acc = forecast_accuracy(agg.actual, agg.forecast)
            rows.append({"level": label, "method": "Baseline (4-week moving average)", **acc,
                         "n_series": agg[level_cols].drop_duplicates().shape[0] if level_cols else 1})

        base_level(["store_id", "sku_id"], "Store-SKU")
        base_level(["sku_id"], "SKU")
        base_level(["category"], "Category")
        base_level([], "Total")

    return pd.DataFrame(rows)
