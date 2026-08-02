# Portfolio Summary

## What this project demonstrates

An end-to-end demand forecasting and inventory intelligence platform for a regional retail supply chain, built to the standard of a production analytics and AI initiative rather than a tutorial: synthetic but realistic source data with genuine data-quality defects, a medallion (bronze/silver/gold) architecture implemented in real SQL against DuckDB (Fabric-portable), a full modelling stack (baseline, exponential smoothing, gradient-boosted demand forecasting, hierarchical reconciliation, safety-stock/reorder-point optimisation, lead-time risk classification, inventory anomaly detection, promotion uplift estimation, scenario modelling), a governance layer (data catalogue, lineage, access control, privacy assessment, risk register, model card, data-quality rule engine), and a Power BI reporting layer (semantic model, DAX measure library, 8-page dashboard specification, reproducible screenshot renderer).

## Why it is structured this way

Every number quoted in the business case and the dashboards is a genuine output of the pipeline's holdout evaluation and business-KPI computation - re-running `python -m supply_chain.pipeline` regenerates the data and reproduces every metric from scratch. Two of the eleven governed data-quality rules are deliberately left failing in the sample run (a purchase order referencing an unknown SKU, and a gap in product cost data), because a scorecard that is always 100% green is not credible evidence that the controls actually work - this platform is built to show the controls catching real, injected defects.

## Skills demonstrated

- Demand planning domain knowledge: hierarchical forecasting, safety stock and reorder-point theory, service-level trade-offs, promotion uplift measurement, supplier lead-time risk.
- Applied machine learning: scikit-learn gradient boosting for regression and classification, statsmodels exponential smoothing, IsolationForest anomaly detection, proper time-ordered train/test splitting, honest reporting of a modest model (AUC ~0.60) rather than an inflated one.
- Data engineering: medallion architecture, DuckDB and dbt-style SQL transformations, referential-integrity and data-quality rule engines, reproducible synthetic data generation with controlled defects.
- Governance and responsible AI: data catalogue, lineage, access control matrix, privacy assessment, risk register, model card, override/audit trail, retraining criteria.
- Business and analytics communication: baseline/target KPI framing, financial value estimation, executive and technical presentation scripts, an 8-page Power BI specification with a consistent interaction contract (legends, tooltips, cross-filter highlighting, filter chips).
- Software engineering practice: modular Python package, automated tests (pytest), CI (GitHub Actions), Docker Compose, configuration-driven thresholds, structured logging.

## Resume-ready project bullets

- Built an end-to-end demand forecasting and inventory intelligence platform (Python, SQL, DuckDB, scikit-learn, statsmodels, Power BI) covering bronze/silver/gold data engineering, hierarchical demand forecasting, safety-stock optimisation, supplier lead-time risk modelling and inventory anomaly detection.
- Designed and implemented a gradient-boosted demand forecasting model that reduced weighted MAPE versus the incumbent moving-average baseline, with reconciliation showing accuracy improving further from store-SKU through category to network-total grain.
- Established a governance framework covering data quality rules, master-data controls, model cards, access control and risk registers, with automated checks that genuinely detect injected referential-integrity and completeness defects rather than reporting a uniformly clean scorecard.
- Delivered an 8-page Power BI reporting package (semantic model, DAX measure library, dashboard specification) with a consistent cross-page interaction design - legends, labelled axes, hover tooltips and cross-filter highlighting - built via a reproducible Python/Pillow rendering pipeline.
- Quantified business value (stock-out reduction, excess-inventory reduction, forecast-accuracy improvement, inventory-turns uplift, manual-planning-effort reduction) against baselines computed directly from the underlying data, not assumed figures.
