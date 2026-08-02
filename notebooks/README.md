# Notebooks

Fabric notebooks in this project should call the tested `supply_chain` package rather than duplicate business logic - the same discipline applied to the `python/` entrypoints. Recommended notebooks for a production build-out: exploratory analysis of the weekly demand panel, independent validation of the champion forecast model against a challenger, supplier scorecard deep-dive, and a scenario-planning workbook built on `supply_chain.inventory.run_scenarios`.

No notebooks are checked into this repository - every analysis shown in the documentation and dashboards is reproducible directly from `python -m supply_chain.pipeline` and the scripts under `python/`, so there is nothing notebook-only to maintain or go stale.
