# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Price sensitivity analysis
# MAGIC Apply simple percentage shocks to product basket prices and recompute crude valuations.
# MAGIC Results are written to `crude.assay.gold_price_sensitivity`.

# COMMAND ----------
from pyspark.sql import functions as F
from datetime import datetime
import pandas as pd

from src.valuation_engine import compute_crude_value

CATALOG = "crude"
SCHEMA = "assay"

# Sensitivity grid (% change)
LIGHTS_SHOCKS = [-0.05, 0.0, 0.05]
MIDDLES_SHOCKS = [-0.05, 0.0, 0.05]
HEAVIES_SHOCKS = [-0.05, 0.0, 0.05]

assays = spark.table(f"{CATALOG}.{SCHEMA}.silver_assays")
base_prices = spark.table(f"{CATALOG}.{SCHEMA}.silver_prices")

rows = []
for dl in LIGHTS_SHOCKS:
    for dm in MIDDLES_SHOCKS:
        for dh in HEAVIES_SHOCKS:
            scenario_id = f"ps_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{int((dl+0.1)*10000)}_{int((dm+0.1)*10000)}_{int((dh+0.1)*10000)}"
            # Build shocked price DF
            shocked = (base_prices
                .withColumn("price_usd_bbl", F.when(F.col("product") == F.lit("LIGHTS"), F.col("price_usd_bbl")*(1+dl))
                                            .when(F.col("product") == F.lit("MIDDLES"), F.col("price_usd_bbl")*(1+dm))
                                            .when(F.col("product") == F.lit("HEAVIES"), F.col("price_usd_bbl")*(1+dh))
                                            .otherwise(F.col("price_usd_bbl")))
            )
            gross = compute_crude_value(assays, shocked)
            out = gross.withColumn("scenario_id", F.lit(scenario_id)) \
                       .withColumn("lights_shock", F.lit(dl)) \
                       .withColumn("middles_shock", F.lit(dm)) \
                       .withColumn("heavies_shock", F.lit(dh))
            rows.append(out)

result_df = rows[0]
for r in rows[1:]:
    result_df = result_df.unionByName(r)

# Persist results
(result_df
 .write
 .mode("append")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_price_sensitivity"))

# Preview
spark.table(f"{CATALOG}.{SCHEMA}.gold_price_sensitivity").orderBy(F.desc("gross_value_usd_bbl")).show(20)
