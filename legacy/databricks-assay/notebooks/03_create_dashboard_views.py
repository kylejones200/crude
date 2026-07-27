# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Create views for Databricks SQL dashboard
# MAGIC This notebook creates or replaces views in `crude.assay` that are convenient for dashboards.

# COMMAND ----------
CATALOG = "crude"
SCHEMA = "assay"

# Top netbacks enriched with basic crude attributes
spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{SCHEMA}.vw_top_netbacks AS
SELECT v.crude_id,
       c.name,
       c.api,
       c.sulfur_wt,
       v.netback_usd_bbl
FROM {CATALOG}.{SCHEMA}.gold_crude_valuations v
LEFT JOIN {CATALOG}.{SCHEMA}.gold_crude_catalog c USING (crude_id)
ORDER BY netback_usd_bbl DESC
""")

# Latest blend run id helper
spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{SCHEMA}.vw_latest_blend_run AS
SELECT run_id
FROM {CATALOG}.{SCHEMA}.gold_blend_runs
ORDER BY run_id DESC
LIMIT 1
""")

# Latest blend recommendations (resolved via latest run view)
spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{SCHEMA}.vw_latest_blend AS
WITH latest AS (
  SELECT run_id FROM {CATALOG}.{SCHEMA}.vw_latest_blend_run
)
SELECT r.run_id,
       b.crude_id,
       b.vol_bbl,
       b.cost_usd_bbl
FROM {CATALOG}.{SCHEMA}.gold_blend_recommendations b
CROSS JOIN latest r
WHERE b.run_id = r.run_id
ORDER BY vol_bbl DESC
""")

# Blend summary metrics
spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{SCHEMA}.vw_latest_blend_summary AS
WITH latest AS (
  SELECT run_id FROM {CATALOG}.{SCHEMA}.vw_latest_blend_run
),
agg AS (
  SELECT b.run_id,
         SUM(b.vol_bbl) AS total_vol_bbl,
         SUM(b.vol_bbl * b.cost_usd_bbl) AS total_cost_usd
  FROM {CATALOG}.{SCHEMA}.gold_blend_recommendations b
  JOIN latest l ON b.run_id = l.run_id
  GROUP BY b.run_id
)
SELECT a.run_id,
       a.total_vol_bbl,
       a.total_cost_usd
FROM agg a
""")

print("Views created: vw_top_netbacks, vw_latest_blend_run, vw_latest_blend, vw_latest_blend_summary")
