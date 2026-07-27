# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Generate and stage sample CSVs directly into UC Volume
# MAGIC 
# MAGIC Use this if Workspace DBFS is restricted and you cannot copy from `/Workspace`.
# MAGIC It will generate representative sample datasets and write them to:
# MAGIC `/Volumes/crude/assay/assay_data/`

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql import types as T

CATALOG = "crude"
SCHEMA = "assay"
VOLUME = "/Volumes/crude/assay/assay_data"

# Ensure destination exists
_ = dbutils.fs.mkdirs(VOLUME)

# Helper to write small datasets

def write_rows(path: str, schema: T.StructType, rows: list[tuple]):
    df = spark.createDataFrame(rows, schema=schema)
    (df.coalesce(1)
       .write.mode("overwrite").option("header", True).csv(path))
    print(f"Wrote {path}")

# COMMAND ----------
# Assays (very simple cut split)
assays_schema = T.StructType([
    T.StructField("crude_id", T.StringType(), False),
    T.StructField("name", T.StringType(), True),
    T.StructField("api", T.DoubleType(), True),
    T.StructField("sulfur_wt", T.DoubleType(), True),
    T.StructField("cut_light_pct", T.DoubleType(), True),
    T.StructField("cut_middle_pct", T.DoubleType(), True),
    T.StructField("cut_heavy_pct", T.DoubleType(), True),
])
assays_rows = [
    ("ARB", "Arab Light", 33.0, 1.8, 0.35, 0.45, 0.20),
    ("WAF", "West African Blend", 36.5, 0.25, 0.40, 0.45, 0.15),
    ("MARS", "Mars", 29.0, 2.0, 0.25, 0.45, 0.30),
]
write_rows(f"{VOLUME}/assays.csv", assays_schema, assays_rows)

# Prices (product baskets)
prices_schema = T.StructType([
    T.StructField("product", T.StringType(), False),
    T.StructField("price_usd_bbl", T.DoubleType(), True),
])
prices_rows = [("LIGHTS", 88.0), ("MIDDLES", 82.0), ("HEAVIES", 75.0)]
write_rows(f"{VOLUME}/prices.csv", prices_schema, prices_rows)

# Freight
freight_schema = T.StructType([
    T.StructField("origin", T.StringType(), False),
    T.StructField("destination", T.StringType(), False),
    T.StructField("rate_usd_bbl", T.DoubleType(), True),
])
freight_rows = [("ME", "GulfCoast", 1.75), ("WAF", "GulfCoast", 1.25), ("USG", "GulfCoast", 0.50)]
write_rows(f"{VOLUME}/freight_routes.csv", freight_schema, freight_rows)

# Blend supply
supply_schema = T.StructType([
    T.StructField("crude_id", T.StringType(), False),
    T.StructField("cost_usd_bbl", T.DoubleType(), True),
    T.StructField("available_bbl", T.DoubleType(), True),
])
supply_rows = [("ARB", 76.0, 100000.0), ("WAF", 79.5, 80000.0), ("MARS", 71.0, 120000.0)]
write_rows(f"{VOLUME}/blend_supply.csv", supply_schema, supply_rows)

# Live prices (optional market feed placeholder)
live_prices_schema = T.StructType([
    T.StructField("symbol", T.StringType(), False),
    T.StructField("price", T.DoubleType(), True),
    T.StructField("as_of", T.TimestampType(), True),
])
live_prices_rows = [("BRENT", 92.3, F.current_timestamp()), ("WTI", 88.7, F.current_timestamp())]
# Convert timestamp literals properly
_live_df = spark.createDataFrame([(r[0], r[1]) for r in live_prices_rows], ["symbol", "price"]).withColumn("as_of", F.current_timestamp())
(_live_df.coalesce(1).write.mode("overwrite").option("header", True).csv(f"{VOLUME}/live_prices.csv"))
print(f"Wrote {VOLUME}/live_prices.csv")

# Source systems mock files used by your extended DLT
simple_two_schema = T.StructType([
    T.StructField("record_id", T.StringType(), False),
    T.StructField("value", T.DoubleType(), True),
])
write_rows(f"{VOLUME}/pi_system_data.csv", simple_two_schema, [("p1", 1.0), ("p2", 2.0)])

intertek_schema = T.StructType([
    T.StructField("sample_id", T.StringType(), False),
    T.StructField("crude_id", T.StringType(), False),
    T.StructField("api", T.DoubleType(), True),
    T.StructField("sulfur_wt", T.DoubleType(), True),
])
write_rows(f"{VOLUME}/intertek_lab_reports.csv", intertek_schema, [("s1", "ARB", 33.2, 1.78), ("s2", "WAF", 36.6, 0.26)])

bliss_schema = T.StructType([
    T.StructField("recipe_id", T.StringType(), False),
    T.StructField("desc", T.StringType(), True),
])
write_rows(f"{VOLUME}/bliss_blend_recipes.csv", bliss_schema, [("r1", "Std ARB/WAF"), ("r2", "Heavy USG")])

lims_schema = T.StructType([
    T.StructField("test_id", T.StringType(), False),
    T.StructField("crude_id", T.StringType(), False),
    T.StructField("measure", T.StringType(), True),
    T.StructField("value", T.DoubleType(), True),
])
write_rows(f"{VOLUME}/lims_quality_tests.csv", lims_schema, [("t1", "ARB", "TAN", 0.3), ("t2", "MARS", "Ni", 8.0)])

asp_schema = T.StructType([
    T.StructField("scenario_id", T.StringType(), False),
    T.StructField("note", T.StringType(), True),
])
write_rows(f"{VOLUME}/aspentech_planning.csv", asp_schema, [("sA", "Base plan"), ("sB", "High diesel")])

hav_schema = T.StructType([
    T.StructField("run_id", T.StringType(), False),
    T.StructField("objective", T.StringType(), True),
    T.StructField("value", T.DoubleType(), True),
])
write_rows(f"{VOLUME}/haverly_optimization.csv", hav_schema, [("h1", "Max margin", 12.3)])

print("All sample files generated in volume.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Validate tables after DLT run
# MAGIC - Configure DLT with `assay.data.base_path = /Volumes/crude/assay/assay_data`
# MAGIC - Start the pipeline, then query gold tables.
