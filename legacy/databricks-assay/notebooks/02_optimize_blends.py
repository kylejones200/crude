# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Optimize crude blend with Pyomo
# MAGIC 
# MAGIC This notebook reads assay qualities and a sample supply curve, then solves a linear blending problem
# MAGIC to meet API and sulfur specs at minimum cost. Results are written to Delta tables under `crude.assay`.

# COMMAND ----------
from pyspark.sql import functions as F
import pandas as pd
from datetime import datetime

from src.optimization.blend_pyomo import optimize_blend

BASE_PATH = spark.conf.get("assay.data.base_path", "dbfs:/FileStore/assay")
CATALOG = "crude"
SCHEMA = "assay"

supply_path = f"{BASE_PATH}/blend_supply.csv"

# Read inputs
assays_pdf = spark.table(f"{CATALOG}.{SCHEMA}.silver_assays").select("crude_id", "api", "sulfur_wt").toPandas()
supply_pdf = spark.read.option("header", True).csv(supply_path).select(
    F.col("crude_id"),
    F.col("cost_usd_bbl").cast("double"),
    F.col("available_bbl").cast("double")
).toPandas()

# Parameters (edit as needed)
TARGET_VOL = 120_000.0
MIN_API = 33.0
MAX_SULFUR = 1.5
try:
    SOLVER = dbutils.widgets.get("solver")
    if SOLVER is None or SOLVER.strip() == "":
        SOLVER = "appsi_highs"
except Exception:
    SOLVER = "appsi_highs"

# Solve
blend_df, metrics = optimize_blend(
    supply_df=supply_pdf,
    assays_df=assays_pdf,
    target_volume_bbl=TARGET_VOL,
    min_api=MIN_API,
    max_sulfur_wt=MAX_SULFUR,
    solver=SOLVER,
)

run_id = f"run_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
blend_df["run_id"] = run_id

metrics_row = {"run_id": run_id, **metrics, "min_api": MIN_API, "max_sulfur_wt": MAX_SULFUR, "target_volume_bbl": TARGET_VOL}

# Write outputs
spark.createDataFrame(pd.DataFrame([metrics_row])).write.mode("append").saveAsTable(f"{CATALOG}.{SCHEMA}.gold_blend_runs")
spark.createDataFrame(blend_df).write.mode("append").saveAsTable(f"{CATALOG}.{SCHEMA}.gold_blend_recommendations")

# Display
print("Metrics:")
for k, v in metrics.items():
    print(f"  {k}: {v}")

spark.table(f"{CATALOG}.{SCHEMA}.gold_blend_recommendations").filter(F.col("run_id") == run_id).show()
