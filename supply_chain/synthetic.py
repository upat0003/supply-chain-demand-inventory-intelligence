"""Synthetic data generation for the supply chain demand and inventory platform.

Generates a linked, internally consistent set of source extracts for a
regional retailer: product and SKU master data, the store and warehouse
network, supplier master data, a two-echelon daily inventory simulation
(supplier -> warehouse -> store) driven by a seasonal, promotion- and
weather-aware demand model, and the operational tables (purchase orders,
replenishment decisions, stock-outs, returns, markdowns) that a demand
planning team would work from.

Deliberate data-quality defects are injected (missing values, duplicate
extracts, out-of-range readings, a bad foreign key) so the bronze/silver
quality rules and governance controls have real defects to catch — see
governance/data_quality_rules.yml.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .config import CATEGORIES, REGIONS, ScaleConfig

BRAND_NAMES = [
    "Coastline", "Redgum", "Northbank", "Harborside", "Wattlecrest", "Farmgate",
    "Southern Fields", "Bluepeak", "Everwell", "Harvestry", "Truewest", "Ridgeline",
]

CATEGORY_BASE_DEMAND = {
    "Beverages": 13.0, "Snacks": 11.0, "Dairy": 9.5,
    "Household": 4.5, "Personal Care": 3.6, "Frozen": 5.8,
}
# Southern-hemisphere seasonal peak day-of-year (~mid-January) and amplitude
CATEGORY_SEASONALITY = {
    "Beverages": (15, 0.34), "Snacks": (15, 0.14), "Dairy": (200, 0.06),
    "Household": (15, 0.02), "Personal Care": (15, 0.02), "Frozen": (200, 0.20),
}
CATEGORY_WEATHER_SENSITIVITY = {
    "Beverages": 0.021, "Snacks": 0.006, "Dairy": 0.0, "Household": 0.0,
    "Personal Care": 0.0, "Frozen": 0.012,
}
# Base supplier lead time in days by category (imported/ambient goods take longer)
CATEGORY_LEAD_TIME_DAYS = {
    "Beverages": 8, "Snacks": 9, "Dairy": 4, "Household": 18, "Personal Care": 16, "Frozen": 7,
}
STORE_FORMAT_MULTIPLIER = {"Metro": 1.35, "Regional": 1.0, "Express": 0.5}
PROMO_UPLIFT = {"BOGO": 0.75, "Multi-buy": 0.40, "Percent Off": 0.25, "Feature Display": 0.15}

HOLIDAYS = [
    ("2025-11-04", "Melbourne Cup Day", "VIC", "Medium"),
    ("2025-12-25", "Christmas Day", "ALL", "High"),
    ("2025-12-26", "Boxing Day", "ALL", "High"),
    ("2026-01-01", "New Year's Day", "ALL", "Medium"),
    ("2026-01-26", "Australia Day", "ALL", "Medium"),
    ("2026-04-03", "Good Friday", "ALL", "High"),
    ("2026-04-06", "Easter Monday", "ALL", "Medium"),
    ("2026-04-25", "ANZAC Day", "ALL", "Low"),
    ("2026-06-08", "King's Birthday", "ALL", "Low"),
]
HOLIDAY_MULTIPLIER = {"High": 1.55, "Medium": 1.25, "Low": 1.08}

REGION_WEATHER = {
    "VIC": {"mean_temp": 15.0, "amp": 8.0, "rain_scale": 2.6, "storm_months": {6, 7, 8}},
    "NSW": {"mean_temp": 18.0, "amp": 7.0, "rain_scale": 2.8, "storm_months": {2, 3}},
    "QLD": {"mean_temp": 24.0, "amp": 5.0, "rain_scale": 3.6, "storm_months": {12, 1, 2}},
    "WA": {"mean_temp": 20.5, "amp": 7.0, "rain_scale": 2.2, "storm_months": {1, 2}},
}


def _date_range(cfg: ScaleConfig) -> pd.DatetimeIndex:
    end = pd.Timestamp(cfg.end_date)
    start = end - pd.Timedelta(days=cfg.history_days - 1)
    return pd.date_range(start, end, freq="D")


def _make_products(rng, cfg: ScaleConfig) -> pd.DataFrame:
    rows = []
    cats = list(CATEGORIES.items())
    for i in range(cfg.n_products):
        category, subcats = cats[i % len(cats)]
        subcat = rng.choice(subcats)
        unit_cost = round(float(np.exp(rng.normal(1.05, 0.55))), 2)
        margin = rng.uniform(0.28, 0.55)
        unit_price = round(unit_cost / (1 - margin), 2)
        launch = pd.Timestamp("2019-01-01") + pd.Timedelta(days=int(rng.integers(0, 2200)))
        rows.append({
            "product_id": f"PROD-{i + 1:04d}",
            "category": category,
            "subcategory": subcat,
            "brand": rng.choice(BRAND_NAMES),
            "unit_cost": unit_cost,
            "unit_price": unit_price,
            "shelf_life_days": int({"Dairy": 21, "Frozen": 270, "Beverages": 270,
                                     "Snacks": 240, "Household": 720, "Personal Care": 720}[category]
                                    * rng.uniform(0.85, 1.15)),
            "is_seasonal": bool(category in ("Beverages", "Frozen") and rng.random() < 0.6),
            "launch_date": launch.date().isoformat(),
            "discontinued": bool(rng.random() < 0.06),
        })
    return pd.DataFrame(rows)


def _make_skus(rng, cfg: ScaleConfig, products: pd.DataFrame) -> pd.DataFrame:
    pack_options = {
        "Beverages": ["500ml", "1.25L", "6x330ml"], "Snacks": ["150g", "300g", "Multipack"],
        "Dairy": ["1L", "2L", "500g"], "Household": ["750ml", "2L", "4-pack"],
        "Personal Care": ["100ml", "250ml"], "Frozen": ["500g", "1kg"],
    }
    rows = []
    n = cfg.n_skus
    for i in range(n):
        product = products.iloc[i % len(products)]
        pack = rng.choice(pack_options[product.category])
        cost_adj = rng.uniform(0.9, 1.15)
        rows.append({
            "sku_id": f"SKU-{i + 1:05d}",
            "product_id": product.product_id,
            "category": product.category,
            "subcategory": product.subcategory,
            "pack_size": pack,
            "uom": "EA",
            "barcode": f"93{rng.integers(10**9, 10**10 - 1)}",
            "unit_cost": round(product.unit_cost * cost_adj, 2),
            "unit_price": round(product.unit_price * cost_adj, 2),
            "case_pack_qty": int(rng.choice([6, 12, 24, 8])),
            "discontinued": bool(product.discontinued and rng.random() < 0.7),
        })
    return pd.DataFrame(rows)


def _make_warehouses(cfg: ScaleConfig) -> pd.DataFrame:
    regions = REGIONS[: cfg.n_warehouses] if cfg.n_warehouses <= len(REGIONS) else (
        REGIONS * (cfg.n_warehouses // len(REGIONS) + 1))[: cfg.n_warehouses]
    rows = []
    for i, region in enumerate(regions):
        rows.append({
            "warehouse_id": f"WH-{region}",
            "region": region,
            "warehouse_type": "National DC" if i == 0 else "Regional DC",
            "capacity_units": int(60000 if i == 0 else 32000),
        })
    return pd.DataFrame(rows).drop_duplicates("warehouse_id").reset_index(drop=True)


def _make_stores(rng, cfg: ScaleConfig, warehouses: pd.DataFrame) -> pd.DataFrame:
    rows = []
    regions = warehouses.region.tolist()
    for i in range(cfg.n_stores):
        region = regions[i % len(regions)]
        fmt = rng.choice(["Metro", "Regional", "Express"], p=[0.45, 0.35, 0.20])
        size = {"Metro": rng.uniform(1800, 3200), "Regional": rng.uniform(900, 1800),
                "Express": rng.uniform(300, 700)}[fmt]
        rows.append({
            "store_id": f"STR-{i + 1:02d}",
            "region": region,
            "warehouse_id": f"WH-{region}",
            "store_format": fmt,
            "size_sqm": round(size, 0),
            "open_date": (pd.Timestamp("2015-01-01") + pd.Timedelta(days=int(rng.integers(0, 3600)))).date().isoformat(),
        })
    return pd.DataFrame(rows)


def _make_suppliers(rng, cfg: ScaleConfig) -> pd.DataFrame:
    names = ["Ausfresh Distribution", "Pacific Grocers Supply", "Bluewater Logistics",
             "National Household Imports", "Everclear Beverage Co", "Southern Cold Chain",
             "Metro Consumer Goods", "Riverland Produce", "Continental Home Imports"]
    rows = []
    for i in range(cfg.n_suppliers):
        reliability = float(np.clip(rng.normal(0.85, 0.11), 0.45, 0.99))
        rows.append({
            "supplier_id": f"SUP-{i + 1:02d}",
            "supplier_name": names[i % len(names)],
            "primary_category": rng.choice(list(CATEGORIES)),
            "region_of_origin": rng.choice(REGIONS + ["Overseas"], p=[0.16, 0.16, 0.16, 0.12, 0.40]),
            "reliability_score": round(reliability, 3),
            "onboarding_date": (pd.Timestamp("2017-01-01") + pd.Timedelta(days=int(rng.integers(0, 3000)))).date().isoformat(),
        })
    return pd.DataFrame(rows)


def _make_holidays(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    span = {d.date().isoformat() for d in dates}
    for d, name, region, impact in HOLIDAYS:
        if d in span:
            regions = REGIONS if region == "ALL" else [region]
            for r in regions:
                rows.append({"date": d, "holiday_name": name, "region": r, "impact_level": impact})
    return pd.DataFrame(rows)


def _make_weather(rng, dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for region, params in REGION_WEATHER.items():
        doy = dates.dayofyear.values
        temp = params["mean_temp"] + params["amp"] * np.cos(2 * np.pi * (doy - 15) / 365.25)
        temp = temp + rng.normal(0, 1.6, len(dates))
        rain = rng.gamma(1.0, params["rain_scale"], len(dates))
        storm_month = np.isin(dates.month, list(params["storm_months"]))
        severe = (rng.random(len(dates)) < np.where(storm_month, 0.035, 0.004))
        for i, d in enumerate(dates):
            rows.append({
                "date": d.date().isoformat(), "region": region,
                "avg_temp_c": round(float(temp[i]), 1),
                "precipitation_mm": round(float(rain[i]), 1),
                "severe_weather_flag": bool(severe[i]),
            })
    frame = pd.DataFrame(rows)
    # Sensor outage: a short run of missing precipitation readings in one region
    outage_idx = frame[(frame.region == "NSW")].index[40:47]
    frame.loc[outage_idx, "precipitation_mm"] = np.nan
    return frame


def _make_prices(rng, skus: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for _, sku in skus.iterrows():
        rows.append({"sku_id": sku.sku_id, "effective_date": dates.min().date().isoformat(),
                      "list_price": sku.unit_price, "currency": "AUD"})
        if rng.random() < 0.3:
            change_day = dates[int(rng.integers(len(dates) * 0.3, len(dates) * 0.85))]
            new_price = round(sku.unit_price * rng.uniform(1.02, 1.09), 2)
            rows.append({"sku_id": sku.sku_id, "effective_date": change_day.date().isoformat(),
                         "list_price": new_price, "currency": "AUD"})
    return pd.DataFrame(rows).sort_values(["sku_id", "effective_date"]).reset_index(drop=True)


def _make_promotions(rng, skus: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    promo_types = list(PROMO_UPLIFT)
    n_promo_skus = max(1, int(len(skus) * 0.6))
    promo_skus = rng.choice(skus.sku_id, n_promo_skus, replace=False)
    pid = 1
    for sku_id in promo_skus:
        n_events = int(rng.integers(1, 5))
        for _ in range(n_events):
            start_idx = int(rng.integers(0, max(1, len(dates) - 21)))
            duration = int(rng.integers(5, 15))
            start = dates[start_idx]
            end = dates[min(start_idx + duration, len(dates) - 1)]
            ptype = rng.choice(promo_types)
            rows.append({
                "promo_id": f"PROMO-{pid:05d}", "sku_id": sku_id,
                "start_date": start.date().isoformat(), "end_date": end.date().isoformat(),
                "promo_type": ptype, "discount_pct": {"BOGO": 50.0, "Multi-buy": 20.0,
                                                       "Percent Off": round(float(rng.uniform(10, 35)), 0),
                                                       "Feature Display": 0.0}[ptype],
                "planned_uplift_pct": round(PROMO_UPLIFT[ptype] * 100, 1),
            })
            pid += 1
    return pd.DataFrame(rows)


def _assign_suppliers(rng, skus: pd.DataFrame, suppliers: pd.DataFrame) -> dict:
    mapping = {}
    for _, sku in skus.iterrows():
        candidates = suppliers[suppliers.primary_category == sku.category]
        pool = candidates if len(candidates) else suppliers
        mapping[sku.sku_id] = rng.choice(pool.supplier_id.values)
    return mapping


def _build_assortment(rng, cfg: ScaleConfig, skus: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
    pairs = []
    for _, store in stores.iterrows():
        n_carry = max(1, int(len(skus) * cfg.assortment_rate))
        carried = rng.choice(skus.sku_id, n_carry, replace=False)
        for sku_id in carried:
            pairs.append((store.store_id, sku_id))
    return pd.DataFrame(pairs, columns=["store_id", "sku_id"])


def simulate_supply_chain(rng, cfg: ScaleConfig, skus, stores, warehouses, suppliers, sku_supplier,
                           dates, holidays, weather, promotions):
    """Two-echelon (supplier -> warehouse -> store) daily inventory simulation.

    Returns daily_sales, inventory_snapshots, purchase_orders, stock_outs and
    replenishment_decisions as a coherent, internally consistent set of tables.
    """
    assortment = _build_assortment(rng, cfg, skus, stores)
    sku_lookup = skus.set_index("sku_id")
    store_lookup = stores.set_index("store_id")

    holiday_by_region_date = {}
    for _, h in holidays.iterrows():
        holiday_by_region_date.setdefault((h.region, h.date), h.impact_level)

    weather_by_region_date = {(w.region, w.date): w for _, w in weather.iterrows()}
    promo_by_sku = {}
    for _, p in promotions.iterrows():
        promo_by_sku.setdefault(p.sku_id, []).append(p)

    n_days = len(dates)
    date_strs = [d.date().isoformat() for d in dates]

    def active_promo(sku_id, date_str):
        for p in promo_by_sku.get(sku_id, []):
            if p.start_date <= date_str <= p.end_date:
                return p
        return None

    # --- store-sku state -----------------------------------------------
    store_sku_keys = list(assortment.itertuples(index=False, name=None))
    n_ss = len(store_sku_keys)
    store_daily_mean = np.zeros(n_ss)
    store_on_hand = np.zeros(n_ss)
    store_pending = [[] for _ in range(n_ss)]  # list of (arrival_day_idx, qty)
    store_rop = np.zeros(n_ss)
    store_target = np.zeros(n_ss)
    store_wh = []
    store_sku_ids = []
    store_ids = []
    internal_lead = np.zeros(n_ss, dtype=int)

    for i, (store_id, sku_id) in enumerate(store_sku_keys):
        sku = sku_lookup.loc[sku_id]
        store = store_lookup.loc[store_id]
        base = CATEGORY_BASE_DEMAND[sku.category] * STORE_FORMAT_MULTIPLIER[store.store_format]
        base *= float(np.exp(rng.normal(0, 0.28)))
        store_daily_mean[i] = base
        lead = 2
        internal_lead[i] = lead
        store_rop[i] = base * (lead + 3)
        store_target[i] = store_rop[i] * 1.7
        store_on_hand[i] = store_target[i] * rng.uniform(0.7, 1.1)
        store_wh.append(store.warehouse_id)
        store_sku_ids.append(sku_id)
        store_ids.append(store_id)

    # --- warehouse-sku state --------------------------------------------
    wh_sku_keys = sorted(set(zip([w for w in store_wh], store_sku_ids)))
    wh_index = {k: idx for idx, k in enumerate(wh_sku_keys)}
    n_wh = len(wh_sku_keys)
    wh_on_hand = np.zeros(n_wh)
    wh_pending = [[] for _ in range(n_wh)]
    wh_rop = np.zeros(n_wh)
    wh_target = np.zeros(n_wh)
    wh_lead_quoted = np.zeros(n_wh, dtype=int)

    # aggregate downstream mean demand per warehouse-sku for sizing policy
    agg_mean = {}
    for i, key in enumerate(zip(store_wh, store_sku_ids)):
        agg_mean[key] = agg_mean.get(key, 0.0) + store_daily_mean[i]

    for key, idx in wh_index.items():
        wh_id, sku_id = key
        sku = sku_lookup.loc[sku_id]
        supplier_id = sku_supplier[sku_id]
        supplier = suppliers.set_index("supplier_id").loc[supplier_id]
        base_lead = CATEGORY_LEAD_TIME_DAYS[sku.category]
        quoted = int(round(base_lead * (1.6 - supplier.reliability_score * 0.6)))
        wh_lead_quoted[idx] = max(3, quoted)
        downstream = agg_mean.get(key, 1.0)
        wh_rop[idx] = downstream * (wh_lead_quoted[idx] + 5)
        wh_target[idx] = wh_rop[idx] * 1.6
        wh_on_hand[idx] = wh_target[idx] * rng.uniform(0.75, 1.15)

    sales_rows, snapshot_rows, po_rows, stockout_rows, decision_rows = [], [], [], [], []
    po_counter = 1
    decision_counter = 1

    for t in range(n_days):
        date_str = date_strs[t]
        doy = dates[t].dayofyear
        weekday = dates[t].dayofweek

        # receive warehouse deliveries due today
        for idx in range(n_wh):
            arrived = [q for (arr, q) in wh_pending[idx] if arr == t]
            if arrived:
                wh_on_hand[idx] += sum(arrived)
                wh_pending[idx] = [(a, q) for (a, q) in wh_pending[idx] if a != t]

        # receive store transfers due today
        for i in range(n_ss):
            arrived = [q for (arr, q) in store_pending[i] if arr == t]
            if arrived:
                store_on_hand[i] += sum(arrived)
                store_pending[i] = [(a, q) for (a, q) in store_pending[i] if a != t]

        # store demand realisation
        store_requests = {}
        for i, (store_id, sku_id) in enumerate(store_sku_keys):
            sku = sku_lookup.loc[sku_id]
            region = store_lookup.loc[store_id].region
            weekday_mult = 1.18 if weekday >= 5 else 1.0
            peak_day, amp = CATEGORY_SEASONALITY[sku.category]
            season_mult = 1 + amp * math.cos(2 * math.pi * (doy - peak_day) / 365.25)
            weather_row = weather_by_region_date.get((region, date_str))
            weather_mult = 1.0
            if weather_row is not None and CATEGORY_WEATHER_SENSITIVITY[sku.category] > 0:
                temp = weather_row.avg_temp_c
                if not pd.isna(temp):
                    weather_mult = 1 + CATEGORY_WEATHER_SENSITIVITY[sku.category] * (temp - 20)
            holiday_impact = holiday_by_region_date.get((region, date_str))
            holiday_mult = HOLIDAY_MULTIPLIER.get(holiday_impact, 1.0)
            promo = active_promo(sku_id, date_str)
            promo_mult = 1 + PROMO_UPLIFT[promo.promo_type] if promo is not None else 1.0
            trend_mult = 1 + 0.00025 * t
            lam = max(0.05, store_daily_mean[i] * weekday_mult * season_mult * weather_mult
                      * holiday_mult * promo_mult * trend_mult)
            demand = rng.poisson(lam)
            available = store_on_hand[i]
            actual = min(demand, available)
            actual_units = int(actual)  # a customer cannot buy a fractional unit
            lost_units = int(demand) - actual_units
            store_on_hand[i] -= actual
            revenue = round(actual_units * sku.unit_price, 2)
            sales_rows.append({
                "date": date_str, "store_id": store_id, "sku_id": sku_id,
                "units_sold": actual_units, "revenue": revenue,
                "promo_flag": promo is not None,
                "unconstrained_demand": int(demand),
            })
            if lost_units > 0:
                stockout_rows.append({
                    "date": date_str, "store_id": store_id, "sku_id": sku_id,
                    "stockout_flag": True, "lost_sales_units_estimate": lost_units,
                    "lost_sales_revenue_estimate": round(lost_units * sku.unit_price, 2),
                })

            on_order = sum(q for (_, q) in store_pending[i])
            if store_on_hand[i] + on_order < store_rop[i]:
                request_qty = max(0.0, store_target[i] - store_on_hand[i] - on_order)
                if request_qty > 0:
                    key = (store_wh[i], sku_id)
                    store_requests.setdefault(key, []).append((i, request_qty))

        # warehouse fulfils store transfer requests (pro-rata if short)
        for key, requesters in store_requests.items():
            idx = wh_index[key]
            total_req = sum(q for (_, q) in requesters)
            available = max(0.0, wh_on_hand[idx])
            fill_ratio = 1.0 if total_req <= available else (available / total_req if total_req > 0 else 0.0)
            for i, qty in requesters:
                fulfilled = qty * fill_ratio
                if fulfilled > 0:
                    wh_on_hand[idx] -= fulfilled
                    arrive_at = min(t + internal_lead[i] + int(rng.integers(0, 2)), n_days - 1)
                    store_pending[i].append((arrive_at, fulfilled))
            approved = round(total_req * fill_ratio, 1)
            decision_rows.append({
                "decision_id": f"DEC-{decision_counter:06d}", "date": date_str,
                "sku_id": key[1], "location_type": "Store", "location_id": store_ids[requesters[0][0]] if len(requesters) == 1 else "Multiple",
                "recommended_order_qty": round(total_req, 1), "reorder_point": round(store_rop[requesters[0][0]], 1),
                "safety_stock_units": round(store_rop[requesters[0][0]] - store_daily_mean[requesters[0][0]] * internal_lead[requesters[0][0]], 1),
                "approved_qty": approved,
                "approver": "System Auto-Replenishment" if fill_ratio >= 0.98 else "Planner Review",
                "override_flag": fill_ratio < 0.98,
                "override_reason": "" if fill_ratio >= 0.98 else "Warehouse supply shortfall - partial fulfilment",
                "decision_status": "Auto-approved" if fill_ratio >= 0.98 else "Manual override",
            })
            decision_counter += 1

        # warehouse reorders from supplier
        for key, idx in wh_index.items():
            wh_id, sku_id = key
            on_order = sum(q for (_, q) in wh_pending[idx])
            if wh_on_hand[idx] + on_order < wh_rop[idx]:
                order_qty = max(0.0, wh_target[idx] - wh_on_hand[idx] - on_order)
                if order_qty > 50:
                    supplier_id = sku_supplier[sku_id]
                    supplier = suppliers.set_index("supplier_id").loc[supplier_id]
                    quoted = wh_lead_quoted[idx]
                    reliability = supplier.reliability_score
                    variability = max(1, int(round((1 - reliability) * 10)))
                    delay = int(np.clip(rng.normal(0, variability), -2, variability * 2.4))
                    actual_lead = max(1, quoted + delay)
                    arrival = min(t + actual_lead, n_days - 1)
                    wh_pending[idx].append((arrival, order_qty))
                    expected_date = dates[min(t + quoted, n_days - 1)].date().isoformat()
                    actual_date = dates[arrival].date().isoformat()
                    sku_cost = sku_lookup.loc[sku_id].unit_cost
                    po_rows.append({
                        "po_id": f"PO-{po_counter:06d}", "supplier_id": supplier_id,
                        "sku_id": sku_id, "warehouse_id": wh_id,
                        "order_date": date_str, "expected_delivery_date": expected_date,
                        "actual_delivery_date": actual_date,
                        "quantity_ordered": round(order_qty, 0),
                        "quantity_received": round(order_qty * (1 if rng.random() > 0.02 else rng.uniform(0.7, 0.97)), 0),
                        "unit_cost": sku_cost,
                        "status": "Late" if actual_date > expected_date else "Received",
                    })
                    po_counter += 1

        # daily snapshots (subsample every 7th day to keep the export a manageable size,
        # always including the most recent 30 days at daily grain for operational drill-down)
        if t % 7 == 0 or t >= n_days - 30:
            for i, (store_id, sku_id) in enumerate(store_sku_keys):
                on_order = sum(q for (_, q) in store_pending[i])
                snapshot_rows.append({
                    "date": date_str, "location_type": "Store", "location_id": store_id,
                    "sku_id": sku_id, "on_hand_units": round(store_on_hand[i], 1),
                    "on_order_units": round(on_order, 1),
                    "safety_stock_units": round(store_rop[i] - store_daily_mean[i] * internal_lead[i], 1),
                    "days_of_supply": round(store_on_hand[i] / max(store_daily_mean[i], 0.1), 1),
                })
            for key, idx in wh_index.items():
                on_order = sum(q for (_, q) in wh_pending[idx])
                snapshot_rows.append({
                    "date": date_str, "location_type": "Warehouse", "location_id": key[0],
                    "sku_id": key[1], "on_hand_units": round(wh_on_hand[idx], 1),
                    "on_order_units": round(on_order, 1),
                    "safety_stock_units": round(wh_rop[idx] - agg_mean.get(key, 0) * wh_lead_quoted[idx], 1),
                    "days_of_supply": round(wh_on_hand[idx] / max(agg_mean.get(key, 0.1), 0.1), 1),
                })

    daily_sales = pd.DataFrame(sales_rows)
    inventory_snapshots = pd.DataFrame(snapshot_rows)
    purchase_orders = pd.DataFrame(po_rows)
    stock_outs = pd.DataFrame(stockout_rows)
    replenishment_decisions = pd.DataFrame(decision_rows)
    return daily_sales, inventory_snapshots, purchase_orders, stock_outs, replenishment_decisions


def _make_returns(rng, daily_sales: pd.DataFrame, skus: pd.DataFrame) -> pd.DataFrame:
    sample = daily_sales[daily_sales.units_sold > 0].sample(frac=0.015, random_state=int(rng.integers(1e6)))
    reasons = ["Damaged in transit", "Customer change of mind", "Quality issue", "Near expiry", "Incorrect item"]
    rows = []
    for i, (_, r) in enumerate(sample.iterrows()):
        return_date = (pd.Timestamp(r.date) + pd.Timedelta(days=int(rng.integers(1, 21)))).date().isoformat()
        rows.append({
            "return_id": f"RET-{i + 1:06d}", "date": return_date, "store_id": r.store_id,
            "sku_id": r.sku_id, "quantity": int(min(r.units_sold, rng.integers(1, 3))),
            "reason": rng.choice(reasons),
        })
    return pd.DataFrame(rows)


def _make_markdowns(rng, daily_sales: pd.DataFrame, skus: pd.DataFrame) -> pd.DataFrame:
    slow_movers = rng.choice(skus.sku_id, max(1, len(skus) // 4), replace=False)
    stores = daily_sales.store_id.unique()
    rows = []
    mid = 1
    for sku_id in slow_movers:
        n_events = int(rng.integers(1, 3))
        for _ in range(n_events):
            store_id = rng.choice(stores)
            dates = daily_sales.date.unique()
            d = rng.choice(dates)
            rows.append({
                "markdown_id": f"MKD-{mid:05d}", "sku_id": sku_id, "store_id": store_id,
                "date": d, "markdown_pct": int(rng.choice([15, 25, 35, 50])),
                "reason": rng.choice(["Clearance", "Near-expiry", "Season-end", "Damaged stock"]),
            })
            mid += 1
    return pd.DataFrame(rows)


def _inject_quality_defects(rng, data: dict) -> dict:
    """Inject realistic, boundedly-sized data-quality defects for governance to catch."""
    sales = data["daily_sales"].copy()
    # missing revenue (POS extract gap)
    miss_idx = rng.choice(sales.index, max(1, len(sales) // 400), replace=False)
    sales.loc[miss_idx, "revenue"] = np.nan
    # duplicate rows (double-loaded POS batch)
    dup_idx = rng.choice(sales.index, max(1, len(sales) // 900), replace=False)
    sales = pd.concat([sales, sales.loc[dup_idx]], ignore_index=True)
    # fat-finger outlier spike
    spike_idx = rng.choice(sales.index, max(1, len(sales) // 1500), replace=False)
    sales.loc[spike_idx, "units_sold"] = (sales.loc[spike_idx, "units_sold"] + 1) * rng.integers(12, 25)
    data["daily_sales"] = sales.drop(columns=["unconstrained_demand"], errors="ignore")

    inv = data["inventory_snapshots"].copy()
    neg_idx = rng.choice(inv.index, max(1, len(inv) // 2500), replace=False)
    inv.loc[neg_idx, "on_hand_units"] = -abs(inv.loc[neg_idx, "on_hand_units"])
    data["inventory_snapshots"] = inv

    po = data["purchase_orders"].copy()
    bad_rows = pd.DataFrame([
        {"po_id": "PO-900001", "supplier_id": po.iloc[0].supplier_id, "sku_id": "SKU-99999",
         "warehouse_id": po.iloc[0].warehouse_id, "order_date": po.iloc[0].order_date,
         "expected_delivery_date": po.iloc[0].expected_delivery_date,
         "actual_delivery_date": po.iloc[0].actual_delivery_date,
         "quantity_ordered": 500, "quantity_received": 500,
         "unit_cost": 4.2, "status": "Received"},
    ])
    data["purchase_orders"] = pd.concat([po, bad_rows], ignore_index=True)

    products = data["products"].copy()
    cost_gap_idx = rng.choice(products.index, 2, replace=False)
    products.loc[cost_gap_idx, "unit_cost"] = np.nan
    data["products"] = products
    return data


def generate_supply_chain(cfg: ScaleConfig, seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = _date_range(cfg)
    products = _make_products(rng, cfg)
    skus = _make_skus(rng, cfg, products)
    warehouses = _make_warehouses(cfg)
    stores = _make_stores(rng, cfg, warehouses)
    suppliers = _make_suppliers(rng, cfg)
    holidays = _make_holidays(dates)
    weather = _make_weather(rng, dates)
    prices = _make_prices(rng, skus, dates)
    promotions = _make_promotions(rng, skus, dates)
    sku_supplier = _assign_suppliers(rng, skus, suppliers)

    daily_sales, inventory_snapshots, purchase_orders, stock_outs, replenishment_decisions = simulate_supply_chain(
        rng, cfg, skus, stores, warehouses, suppliers, sku_supplier, dates, holidays, weather, promotions)

    returns = _make_returns(rng, daily_sales, skus)
    markdowns = _make_markdowns(rng, daily_sales, skus)

    lead_time_rows = []
    po_stats = purchase_orders.copy()
    po_stats["lead_time_actual"] = (pd.to_datetime(po_stats.actual_delivery_date) - pd.to_datetime(po_stats.order_date)).dt.days
    po_stats["lead_time_quoted"] = (pd.to_datetime(po_stats.expected_delivery_date) - pd.to_datetime(po_stats.order_date)).dt.days
    po_stats["on_time"] = po_stats.actual_delivery_date <= po_stats.expected_delivery_date
    for (supplier_id, sku_id), grp in po_stats.groupby(["supplier_id", "sku_id"]):
        if sku_id == "SKU-99999":
            continue
        lead_time_rows.append({
            "supplier_id": supplier_id, "sku_id": sku_id,
            "quoted_lead_time_days": round(grp.lead_time_quoted.mean(), 1),
            "observed_avg_lead_time_days": round(grp.lead_time_actual.mean(), 1),
            "observed_std_lead_time_days": round(grp.lead_time_actual.std(ddof=0) or 0.0, 2),
            "on_time_rate": round(grp.on_time.mean(), 3),
            "sample_size": int(len(grp)),
        })
    lead_times = pd.DataFrame(lead_time_rows)

    data = {
        "products": products, "skus": skus, "stores": stores, "warehouses": warehouses,
        "suppliers": suppliers, "daily_sales": daily_sales, "inventory_snapshots": inventory_snapshots,
        "purchase_orders": purchase_orders, "lead_times": lead_times, "promotions": promotions,
        "prices": prices, "markdowns": markdowns, "holidays": holidays, "weather": weather,
        "returns": returns, "stock_outs": stock_outs, "replenishment_decisions": replenishment_decisions,
    }
    data = _inject_quality_defects(rng, data)
    return data


def write_raw(data: dict[str, pd.DataFrame], root) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, frame in data.items():
        frame.to_csv(root / f"{name}.csv", index=False)
