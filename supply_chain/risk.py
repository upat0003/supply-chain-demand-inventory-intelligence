"""Lead-time / supplier delivery risk prediction.

Trains a classifier on historical purchase orders to estimate the
probability that a new order will arrive late, using supplier reliability,
order size, sourcing region and category lead-time profile as predictors.
Used to flag purchase orders that need an earlier release date or an
expedited freight option before they turn into a stock-out.
"""
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder


def _prepare(purchase_orders: pd.DataFrame, suppliers: pd.DataFrame, skus: pd.DataFrame) -> pd.DataFrame:
    df = purchase_orders[purchase_orders.sku_id.isin(skus.sku_id)].copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["expected_delivery_date"] = pd.to_datetime(df["expected_delivery_date"])
    df["actual_delivery_date"] = pd.to_datetime(df["actual_delivery_date"])
    df["is_late"] = (df.actual_delivery_date > df.expected_delivery_date).astype(int)
    df["quoted_lead_time_days"] = (df.expected_delivery_date - df.order_date).dt.days
    df["order_month"] = df.order_date.dt.month
    df = df.merge(suppliers[["supplier_id", "reliability_score", "region_of_origin"]], on="supplier_id", how="left")
    df = df.merge(skus[["sku_id", "category"]], on="sku_id", how="left")
    return df


def train_lead_time_risk_model(purchase_orders: pd.DataFrame, suppliers: pd.DataFrame,
                                skus: pd.DataFrame, seed: int = 42):
    df = _prepare(purchase_orders, suppliers, skus)
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    df[["region_enc", "category_enc"]] = encoder.fit_transform(df[["region_of_origin", "category"]])
    features = ["reliability_score", "quantity_ordered", "quoted_lead_time_days", "order_month",
                "region_enc", "category_enc"]
    X = df[features].fillna(0)
    y = df["is_late"]

    X_train, X_test, y_train, y_test, df_train, df_test = train_test_split(
        X, y, df, test_size=0.25, random_state=seed, stratify=y)

    model = GradientBoostingClassifier(n_estimators=180, max_depth=3, learning_rate=0.08, random_state=seed)
    model.fit(X_train, y_train)
    proba_test = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba_test) if y_test.nunique() > 1 else float("nan")

    importance = pd.DataFrame({"feature": features, "importance": model.feature_importances_}).sort_values(
        "importance", ascending=False)

    df["late_risk_score"] = model.predict_proba(X[features])[:, 1]
    supplier_risk = df.groupby("supplier_id").agg(
        orders=("po_id", "count"), observed_late_rate=("is_late", "mean"),
        avg_predicted_risk=("late_risk_score", "mean"), reliability_score=("reliability_score", "first"),
    ).reset_index().sort_values("avg_predicted_risk", ascending=False)

    metrics = {
        "auc": round(float(auc), 4), "n_train": int(len(X_train)), "n_test": int(len(X_test)),
        "base_late_rate": round(float(y.mean()), 4),
    }
    return model, metrics, importance, supplier_risk, df
