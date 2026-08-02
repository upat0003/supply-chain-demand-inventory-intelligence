import pandas as pd


def test_master_data_is_unique_and_linked(supply_chain_data):
    data = supply_chain_data
    assert data["products"].product_id.is_unique
    assert data["skus"].sku_id.is_unique
    assert data["skus"].product_id.isin(data["products"].product_id).all()
    assert data["stores"].warehouse_id.isin(data["warehouses"].warehouse_id).all()


def test_generator_contains_expected_quality_conditions(supply_chain_data):
    data = supply_chain_data
    # missing unit cost injected on the product master
    assert data["products"].unit_cost.isna().sum() > 0
    # fat-finger spike injected on daily sales
    assert data["daily_sales"].units_sold.max() > 100
    # negative on-hand defect injected on inventory snapshots
    assert (data["inventory_snapshots"].on_hand_units < 0).sum() > 0
    # bad foreign key injected on purchase orders
    assert (~data["purchase_orders"].sku_id.isin(data["skus"].sku_id)).sum() > 0


def test_daily_sales_values_are_plausible(supply_chain_data):
    sales = supply_chain_data["daily_sales"]
    assert (sales.units_sold >= 0).all()
    assert pd.to_datetime(sales.date).notna().all()


def test_stock_outs_are_a_subset_of_observed_demand(supply_chain_data):
    data = supply_chain_data
    stock_outs = data["stock_outs"]
    assert stock_outs.lost_sales_units_estimate.gt(0).all()
    assert len(stock_outs) < len(data["daily_sales"])


def test_lead_times_are_derived_consistently(supply_chain_data):
    lead_times = supply_chain_data["lead_times"]
    assert (lead_times.on_time_rate.between(0, 1)).all()
    assert (lead_times.observed_avg_lead_time_days > 0).all()
