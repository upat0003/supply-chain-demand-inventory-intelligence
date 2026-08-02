# Model Card - Demand Forecasting and Lead-Time Risk Models

## Inventory and risk classification

Two models are in production scope:

1. **`demand_gbm`** (champion demand forecast) - a gradient-boosted regression model (`sklearn.ensemble.HistGradientBoostingRegressor`) forecasting weekly units sold at store-SKU grain. Challenged by a 4-week moving-average baseline (the incumbent spreadsheet method) and a SKU-level Holt-Winters exponential-smoothing model.
2. **`lead_time_risk`** (supplier delivery risk) - a gradient-boosted classifier (`sklearn.ensemble.GradientBoostingClassifier`) estimating the probability that a new purchase order will arrive after its expected delivery date.

Both are classified **medium-high impact**: outputs drive automated reorder quantities and purchase-order timing, but every recommendation passes through a human-reviewable replenishment decision workflow rather than executing unattended. Model owner: Demand Planning Lead (`demand_gbm`) and Supply Chain Manager (`lead_time_risk`). Independent validation: Data Science. Production operation: Data Platform.

## Intended use

`demand_gbm` estimates expected weekly demand per store-SKU to size safety stock, reorder points and purchase quantities. `lead_time_risk` flags purchase orders at elevated risk of late delivery so a planner can expedite freight or source from an alternate supplier before a stock-out occurs. Neither model should be used to make supplier contractual or disciplinary decisions on its own; the risk score is a prioritisation signal, not a determination of fault.

## Prohibited use

Do not use `lead_time_risk` scores as the sole basis for terminating a supplier relationship. Do not apply either model outside the product categories, regions or seasonal windows represented in its training data without revalidation. Do not remove the human review step for override-flagged or high-value replenishment decisions.

## Data and performance

Training data is synthetic and generated deterministically from seed 42 (see `supply_chain/synthetic.py`). Reported metrics below come from an actual holdout evaluation on the most recent 8 weeks of the generated series (demand model) and a stratified 25% holdout of historical purchase orders (risk model) - see `artifacts/run_summary.json` for the exact run that produced them.

| Model | Metric | Result |
|---|---|---|
| Baseline (4-week moving average) | WMAPE | see `artifacts/run_summary.json.forecast_metrics.baseline_wmape` |
| `demand_gbm` (champion) | WMAPE | see `forecast_metrics.gbm_wmape`; relative improvement over baseline in `forecast_metrics.relative_improvement_pct` |
| SKU-level Holt-Winters (ETS) | WMAPE | see `forecast_metrics.ets_wmape` |
| `lead_time_risk` | ROC-AUC | see `risk_model_metrics.auc` |

The lead-time risk model's discrimination is intentionally reported honestly rather than tuned to look stronger than the signal supports: order quantity, supplier reliability and order month are the dominant predictors, and AUC in the 0.55-0.65 range is realistic for a first-generation model built on the fields available in a typical PO extract. The documented improvement path is to add supplier-level rolling recent performance, carrier/freight-mode data and port/customs congestion indicators, which are not present in this dataset.

## Bias and fairness assessment

Neither model uses or has access to personal or customer-identifying attributes - the input features are demand, price, promotion, calendar, weather, supplier and lead-time signals at store/SKU/supplier grain, so individual-level fairness metrics (e.g. protected-attribute parity) do not apply. The relevant fairness question here is *operational* rather than demographic: whether the models systematically underserve a subset of the network. That is checked directly - forecast accuracy is reported by category and by hierarchy level (see Demand Forecast Accuracy page) rather than as a single blended figure, and the lead-time risk model's feature importance is reviewed to confirm supplier region and category are not the model's only real signal (reliability score and order quantity dominate, which is expected and desired). Store-format performance (Metro/Regional/Express) is monitored so that smaller-format stores are not systematically left under-forecast simply because they carry lower volume.

## Model registry

Both models are tracked in `governance/forecast_version_register.csv` alongside the incumbent baseline and the exponential-smoothing reference model, with version, status, training window and key metric recorded for every entry. Promotion from challenger to champion status requires the independent validation and sign-off described in the change-control section below.

## Explainability

`demand_gbm` feature importances and the weekly monitoring log are exported to `powerbi/data/`. `lead_time_risk` feature importances are exported to `powerbi/data/lead_time_risk_feature_importance.csv`. Both are tree-ensemble models chosen for interoperability with SHAP-style importance and partial dependence in a future iteration; the current build reports built-in impurity-based feature importance as an auditable, dependency-light substitute.

## Human oversight

Every replenishment decision generated by the reorder-point logic carries a `decision_status` of `Auto-approved` or `Manual override`; overrides require a documented `override_reason`. Purchase orders flagged by `lead_time_risk` above the warning threshold are routed to the Supply Chain Manager for review, not auto-expedited. Scenario model outputs (`powerbi/data/scenario_model.csv`) are advisory only and require planner sign-off before assumptions are applied to live reorder points.

## Monitoring and change control

Weekly controls: forecast WMAPE trend, demand/feature PSI, data-quality pass rate, supplier on-time delivery rate, inventory anomaly count. Warning-level breaches require triage within 5 business days; critical breaches require an incident entry in the risk register and may trigger reversion to the baseline moving-average forecast while the champion is retrained. Any change to `demand_gbm` or `lead_time_risk` requires: retraining on a documented data window, holdout evaluation against the current champion, sign-off from Data Science and the relevant business owner, and a version increment in the model registry before deployment.

## Retraining criteria

Retrain `demand_gbm` when weekly WMAPE breaches the warning threshold for three consecutive weeks, when a new product category or store region is added, or on a standing quarterly schedule, whichever comes first. Retrain `lead_time_risk` when a new supplier is onboarded, when the observed late-delivery base rate shifts by more than 5 percentage points, or on the same quarterly schedule.

## Limitations

All performance figures describe behaviour on synthetic data with realistic but simulated demand, weather and supplier variability; they are illustrative of the modelling approach, not evidence of performance on a real retailer's data. Small-volume SKU-store combinations have noisier forecasts than high-volume ones; the monitoring dashboard reports accuracy by level (store-SKU, SKU, category, total) so this is visible rather than hidden by aggregation. Forecast reconciliation approximates top-down disaggregation using historical share and does not implement a full trace-minimisation reconciliation (e.g. MinT); this is a documented simplification appropriate to the scale of this build.
