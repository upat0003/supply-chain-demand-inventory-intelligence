# Executive Presentation Script (five-minute walkthrough)

## 1 — Why this matters (30 seconds)
Demand planning today runs on spreadsheets and trailing averages. This platform replaces that with a governed forecasting and inventory system that accounts for promotions, seasonality, weather and supplier variability, and shows exactly where stock-outs, excess inventory and manual effort are concentrated today.

## 2 — The numbers that matter (60 seconds)
Open the Executive Overview page. Lead with the four headline KPIs: stock-out rate, excess inventory rate, forecast accuracy and inventory turns, each shown against its target band. Anchor the investment case on the annualised lost-sales estimate and the working-capital value of reducing excess inventory - both computed from the same data driving the dashboard, not a separate slide.

## 3 — Forecast accuracy (60 seconds)
Move to Demand Forecast Accuracy. Show the baseline moving-average method next to the gradient-boosted model and the hierarchical reconciliation view. Make the point explicitly: accuracy is best at the total and category level and hardest at store-SKU level - that's expected, and the dashboard shows it honestly rather than hiding it behind an aggregate number.

## 4 — Where the risk is (60 seconds)
Move to Stock-Out Risk and Inventory Health together. Show which store-SKU combinations are trending toward a stock-out this week and which locations are carrying excess days of supply. Connect this to Replenishment Recommendations: every recommendation is either auto-approved or routed for planner review with a documented reason - nothing moves without an audit trail.

## 5 — Supplier and promotion performance (45 seconds)
Move to Supplier Performance. Point out the supplier scorecard and the lead-time risk model - which suppliers are trending toward "Watch" or "Critical" before it becomes a stock-out. Then Promotion Impact: actual uplift versus planned uplift by promotion type, so category managers can hold supplier and vendor-funded promotions to an evidence-based standard.

## 6 — Governance and close (45 seconds)
Close on Data Quality and Model Monitoring: data-quality pass rate, drift status, and the two data-quality issues this build genuinely surfaces (a missing-cost gap and a bad SKU reference) - proof the controls catch real problems rather than reporting a suspiciously perfect scorecard. Ask for agreement on: which category to shadow-run first, who owns the weekly review cadence, and the go/no-go criteria for moving from shadow to auto-approval.

---

## Technical interview explanation

Be ready to explain: why WMAPE rather than plain MAPE for demand data (it isn't distorted by near-zero weeks); why the champion is a pooled gradient-boosted model rather than one model per SKU-store (data efficiency - low-volume combinations borrow strength from the pooled fit); why statsmodels' Holt-Winters exponential smoothing stands in for Prophet (no external compiled sampler dependency, trivial to install in CI, well-understood for series of this length); how safety stock combines demand and lead-time variance (the standard combined-variance formulation, not a fixed multiple of average demand); why the lead-time risk model's AUC is reported honestly in the 0.55-0.65 range rather than inflated - and what additional features (rolling supplier performance, freight/carrier data) would improve it in a real deployment; and how the medallion architecture (bronze/silver/gold in real SQL, executed against DuckDB locally and Fabric in production) keeps local development and production deployment on the same transformation logic.

## Business interview explanation

Be ready to explain in plain language: the four outcomes this solves (fewer stock-outs, less excess stock, more accurate forecasts, less manual firefighting); why targets are expressed as ranges (10-20% stock-out reduction, 8-15% excess-inventory reduction) rather than single numbers - because the achievable gain depends on category and starting maturity; how a planner's day changes (most routine reorders auto-approve, judgement is spent on the exceptions the system flags, not on re-deriving every order from scratch); and what governance exists so the business can trust the automation (every override is logged with a reason, every model change goes through independent review before deployment, and the data-quality scorecard is visible on the same dashboard as the KPIs it feeds).
