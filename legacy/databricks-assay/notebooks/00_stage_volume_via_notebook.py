# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Stage sample CSVs into Unity Catalog Volume via notebook
# MAGIC This notebook copies files from Workspace Files into the UC Volume
# MAGIC `crude.assay.assay_data` when CLI access to `/Volumes` is restricted.

# COMMAND ----------
from pyspark.sql import functions as F

catalog = "crude"
schema = "assay"
volume_name = "assay_data"

# Resolve your workspace user and the repo import path for Workspace Files
current_user = spark.sql("select current_user()").collect()[0][0]
base_workspace = f"dbfs:/Workspace/Users/{current_user}/assay/resources/sample_data"
volume_base = f"/Volumes/{catalog}/{schema}/{volume_name}"

print(f"Workspace files: {base_workspace}")
print(f"Volume dest:    {volume_base}")

# Ensure destination exists
_ = dbutils.fs.mkdirs(volume_base)

files = [
    (f"{base_workspace}/assays.csv",         f"{volume_base}/assays.csv"),
    (f"{base_workspace}/prices.csv",         f"{volume_base}/prices.csv"),
    (f"{base_workspace}/freight_routes.csv", f"{volume_base}/freight_routes.csv"),
    (f"{base_workspace}/blend_supply.csv",   f"{volume_base}/blend_supply.csv"),
]

for src, dst in files:
    print(f"Copy: {src} -> {dst}")
    dbutils.fs.cp(src, dst, recurse=False)

print("Done. Verify:")
dbutils.fs.ls(volume_base)
