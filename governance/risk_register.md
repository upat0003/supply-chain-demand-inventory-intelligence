# Risk Register

| ID | Risk | Inherent rating | Key control | Trigger / threshold | Owner |
|---|---|---:|---|---|---|
| SC-01 | Forecast accuracy deteriorates (model or demand-pattern shift) | High | Weekly WMAPE monitoring vs baseline and challenger comparison | Weekly WMAPE ≥ 0.20 (warning), ≥ 0.28 (critical) | Demand Planning Lead |
| SC-02 | Demand or feature drift undetected | High | PSI monitoring on demand, price and weather features | PSI ≥ 0.10 (warning), ≥ 0.25 (critical) | Data Science |
| SC-03 | Stock-outs on fast-moving SKUs erode revenue and customer trust | High | Reorder-point automation, stock-out risk view, safety-stock scenario modelling | Stock-out rate above target band | Inventory Analyst |
| SC-04 | Excess inventory ties up working capital and increases markdown risk | Medium | Days-of-supply monitoring, excess-stock threshold alerting | Days of supply > 6 for a sustained period | Inventory Analyst |
| SC-05 | Supplier delivery unreliability cascades into warehouse and store stock-outs | High | Lead-time risk model, supplier scorecard, on-time-delivery SLA tracking | Predicted late-delivery risk ≥ 0.30 or on-time rate < 70% | Supply Chain Manager |
| SC-06 | Data-quality defects (missing cost, bad SKU references, negative on-hand) propagate into decisions | High | Blocking critical data-quality rules before gold publication | Any critical rule below threshold | Data Steward |
| SC-07 | Unexplained manual overrides of system replenishment recommendations | Medium | Mandatory override reason capture and override-rate monitoring | Override rate trending upward without documented cause | Supply Chain Manager |
| SC-08 | Promotion uplift over- or under-estimated, causing over-ordering or stock-outs during campaigns | Medium | Promotion uplift model with planned-vs-actual variance tracking | Variance beyond ±15 percentage points | Category Data Steward |
| SC-09 | Unauthorised change to a production forecast or inventory model | Critical | Versioned model registry, approval workflow, deployment gate | Deployed artifact does not match registry record | Platform Owner |
| SC-10 | Scenario assumptions used for planning are stale or undocumented | Medium | Scenario provenance log (author, timestamp, assumptions) reviewed monthly | Scenario older than 90 days still in active use | Demand Planning Lead |

Residual risk after controls is Low-Medium for all items except SC-05 (Medium-High, given genuine supplier variability observed in the data) and SC-09 (Low, given the deployment gate). Risks are reviewed monthly at the supply chain governance forum and escalated to the risk register owner (Supply Chain Manager) on any critical threshold breach.
