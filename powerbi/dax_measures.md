# DAX Measure Library

```DAX
Units Sold := SUM('Fact Daily Sales'[units_sold])
Revenue := SUM('Fact Daily Sales'[revenue])
Promo Units := CALCULATE([Units Sold], 'Fact Daily Sales'[promo_flag] = TRUE())
Promo Share := DIVIDE([Promo Units], [Units Sold])

Store SKU Days := COUNTROWS('Fact Daily Sales')
Stockout Days := CALCULATE(COUNTROWS('Fact Stockouts'), 'Fact Stockouts'[stockout_flag] = TRUE())
Stockout Rate := DIVIDE([Stockout Days], [Store SKU Days])
Lost Sales Units := SUM('Fact Stockouts'[lost_sales_units_estimate])
Lost Sales Revenue := SUM('Fact Stockouts'[lost_sales_revenue_estimate])
Annualised Lost Sales := [Lost Sales Revenue] * DIVIDE(365, DATEDIFF(MIN('Dim Date'[Date]), MAX('Dim Date'[Date]), DAY))

Avg Days Of Supply := AVERAGE('Fact Inventory'[days_of_supply])
Excess Stock Rows := CALCULATE(COUNTROWS('Fact Inventory'), 'Fact Inventory'[days_of_supply] > 6, 'Fact Inventory'[location_type] = "Store")
Store Inventory Rows := CALCULATE(COUNTROWS('Fact Inventory'), 'Fact Inventory'[location_type] = "Store")
Excess Inventory Rate := DIVIDE([Excess Stock Rows], [Store Inventory Rows])
Inventory Value := SUMX('Fact Inventory', 'Fact Inventory'[on_hand_units] * RELATED('Dim Product'[unit_cost]))
COGS Annualised := SUMX('Fact Daily Sales', 'Fact Daily Sales'[units_sold] * RELATED('Dim Product'[unit_cost])) * DIVIDE(365, DATEDIFF(MIN('Dim Date'[Date]), MAX('Dim Date'[Date]), DAY))
Inventory Turns := DIVIDE([COGS Annualised], [Inventory Value])

Purchase Orders := COUNTROWS('Fact Purchase Orders')
Late Purchase Orders := CALCULATE([Purchase Orders], 'Fact Purchase Orders'[is_late] = TRUE())
Late Delivery Rate := DIVIDE([Late Purchase Orders], [Purchase Orders])
Avg Fill Rate := AVERAGEX('Fact Purchase Orders', DIVIDE('Fact Purchase Orders'[quantity_received], 'Fact Purchase Orders'[quantity_ordered]))
Supplier Status := SWITCH(TRUE(), [Late Delivery Rate] >= 0.30, "Critical", [Late Delivery Rate] >= 0.20, "Watch", "Healthy")

Replenishment Decisions := COUNTROWS('Fact Replenishment Decisions')
Auto Approved Decisions := CALCULATE([Replenishment Decisions], 'Fact Replenishment Decisions'[decision_status] = "Auto-approved")
Auto Approved Rate := DIVIDE([Auto Approved Decisions], [Replenishment Decisions])
Override Rate := 1 - [Auto Approved Rate]

WMAPE := DIVIDE(SUMX('Fact Forecast', ABS('Fact Forecast'[actual_units] - 'Fact Forecast'[forecast_units])), SUMX('Fact Forecast', ABS('Fact Forecast'[actual_units])))
Forecast Accuracy Pct := (1 - [WMAPE]) * 100
Forecast Bias := DIVIDE(AVERAGEX('Fact Forecast', 'Fact Forecast'[forecast_units] - 'Fact Forecast'[actual_units]), AVERAGE('Fact Forecast'[actual_units]))
Forecast Status := SWITCH(TRUE(), [WMAPE] >= 0.28, "Critical", [WMAPE] >= 0.20, "Warning", "Healthy")

Max Feature PSI := MAX('Fact Drift'[psi])
Drift Status := SWITCH(TRUE(), [Max Feature PSI] >= 0.25, "Critical", [Max Feature PSI] >= 0.10, "Warning", "Healthy")

DQ Pass Rate := AVERAGE('Fact Data Quality'[pass_rate])
DQ Rules Failing := CALCULATE(COUNTROWS('Fact Data Quality'), 'Fact Data Quality'[passed] = FALSE())
DQ Status := IF([DQ Pass Rate] < 0.93, "Critical", IF([DQ Pass Rate] < 0.97, "Warning", "Healthy"))

Inventory Anomalies := COUNTROWS('Fact Inventory Anomalies')

Promo Events := COUNTROWS('Fact Promotion Uplift')
Avg Uplift Pct := AVERAGE('Fact Promotion Uplift'[uplift_pct])
Avg Planned Uplift Pct := AVERAGE('Fact Promotion Uplift'[planned_uplift_pct])
Uplift Variance Pp := [Avg Uplift Pct] - [Avg Planned Uplift Pct]

Units Sold MoM % := DIVIDE([Units Sold] - CALCULATE([Units Sold], DATEADD('Dim Date'[Date], -1, MONTH)), CALCULATE([Units Sold], DATEADD('Dim Date'[Date], -1, MONTH)))
Stockout Rate YoY Δ := [Stockout Rate] - CALCULATE([Stockout Rate], SAMEPERIODLASTYEAR('Dim Date'[Date]))
Selected KPI := SWITCH(SELECTEDVALUE('KPI Selector'[KPI]), "Stockout Rate", [Stockout Rate], "Excess Inventory Rate", [Excess Inventory Rate], "Forecast Accuracy", [Forecast Accuracy Pct], [Inventory Turns])
Status Colour := SWITCH(TRUE(), [Forecast Status] = "Critical" || [DQ Status] = "Critical", "#A23A3A", [Forecast Status] = "Warning" || [DQ Status] = "Warning", "#B3791D", "#3F7D5C")
Dynamic Title := SELECTEDVALUE('Dim Product'[category], "All categories") & " — " & SELECTEDVALUE('Dim Date'[Month Year], "All periods")
```
