"""Inventory anomaly detection.

Flags store-SKU-days where the inventory position is implausible given
recent history: negative on-hand (system sync defects), sudden unexplained
drops or spikes in days-of-supply, and stock sitting far outside its normal
operating band. Uses IsolationForest over engineered features rather than
fixed thresholds so the detector adapts to each SKU's normal variability.
"""
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest


def _engineer_features(snapshots: pd.DataFrame) -> pd.DataFrame:
    df = snapshots.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["location_id", "sku_id", "date"])
    grp = df.groupby(["location_id", "sku_id"])["days_of_supply"]
    df["dos_rolling_mean"] = grp.transform(lambda s: s.rolling(4, min_periods=1).mean())
    df["dos_rolling_std"] = grp.transform(lambda s: s.rolling(4, min_periods=2).std()).fillna(0)
    df["dos_change"] = grp.diff().fillna(0)
    df["is_negative_on_hand"] = df["on_hand_units"] < 0
    return df


def detect_anomalies(snapshots: pd.DataFrame, contamination: float = 0.02) -> pd.DataFrame:
    df = _engineer_features(snapshots)
    features = ["on_hand_units", "on_order_units", "days_of_supply", "dos_rolling_mean",
                "dos_rolling_std", "dos_change"]
    X = df[features].fillna(0)
    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=42)
    df["anomaly_score"] = -model.fit(X).score_samples(X)
    threshold = df["anomaly_score"].quantile(1 - contamination)
    df["is_anomaly"] = (df["anomaly_score"] >= threshold) | df["is_negative_on_hand"]

    def classify(row):
        if row.is_negative_on_hand:
            return "Negative on-hand (data defect)"
        if row.dos_change < -3 and row.is_anomaly:
            return "Unexplained inventory drop"
        if row.dos_change > 3 and row.is_anomaly:
            return "Unexplained inventory build-up"
        if row.is_anomaly:
            return "Abnormal stock position"
        return "Normal"

    df["anomaly_type"] = df.apply(classify, axis=1)
    result = df[df.is_anomaly][
        ["date", "location_type", "location_id", "sku_id", "on_hand_units", "on_order_units",
         "days_of_supply", "anomaly_score", "anomaly_type"]
    ].sort_values("anomaly_score", ascending=False).reset_index(drop=True)
    result["date"] = result["date"].dt.date.astype(str)
    return result
