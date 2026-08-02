"""Supply chain demand and inventory intelligence platform.

Executable package that generates the synthetic source data, builds the
bronze/silver/gold layers in DuckDB, trains and evaluates the forecasting and
inventory models, runs the governance and monitoring controls, and exports
the Power BI-ready datasets. Every module here is designed to map cleanly
onto a Microsoft Fabric implementation: bronze/silver/gold become Lakehouse
layers, the DuckDB warehouse stands in for a Fabric Warehouse, and the
pipeline entrypoint mirrors what would run as a scheduled Fabric notebook or
Data Factory pipeline.
"""

__version__ = "1.0.0"
