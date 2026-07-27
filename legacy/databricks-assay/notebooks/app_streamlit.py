# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Crude Assay App (Streamlit on Databricks)
# MAGIC 
# MAGIC Use this app to explore crude catalog, netback valuations, and run a simple blend optimization.
# MAGIC 
# MAGIC How to run:
# MAGIC 1) In the notebook toolbar, click the Streamlit button or use `File > New > App` and point to this notebook.
# MAGIC 2) Ensure the DLT pipeline has populated gold tables in `crude.assay` and that the volume data is staged.
# MAGIC 3) First time on a cluster, run once: `%pip install pyomo highspy`.

# COMMAND ----------
# MAGIC %%streamlit
# MAGIC import streamlit as st
# MAGIC import pandas as pd
# MAGIC from pyspark.sql import functions as F
# MAGIC 
# MAGIC from src.optimization.blend_pyomo import optimize_blend
# MAGIC 
# MAGIC CATALOG = "crude"
# MAGIC SCHEMA = "assay"
# MAGIC 
# MAGIC st.set_page_config(page_title="Crude Assay App", layout="wide")
# MAGIC st.title("Crude Assay App")
# MAGIC 
# MAGIC # --- Data loaders ---
# MAGIC @st.cache_data(ttl=120)
# MAGIC def load_catalog():
# MAGIC     return spark.table(f"{CATALOG}.{SCHEMA}.gold_crude_catalog").toPandas()
# MAGIC 
# MAGIC @st.cache_data(ttl=120)
# MAGIC def load_valuations():
# MAGIC     return spark.table(f"{CATALOG}.{SCHEMA}.gold_crude_valuations").toPandas()
# MAGIC 
# MAGIC @st.cache_data(ttl=120)
# MAGIC def load_assays():
# MAGIC     return spark.table(f"{CATALOG}.{SCHEMA}.silver_assays").select("crude_id","api","sulfur_wt").toPandas()
# MAGIC 
# MAGIC @st.cache_data(ttl=120)
# MAGIC def load_supply(path:str):
# MAGIC     df = spark.read.option("header", True).csv(path).select(
# MAGIC         F.col("crude_id"),
# MAGIC         F.col("cost_usd_bbl").cast("double"),
# MAGIC         F.col("available_bbl").cast("double"),
# MAGIC     ).toPandas()
# MAGIC     return df
# MAGIC 
# MAGIC col1, col2, col3 = st.columns(3)
# MAGIC with col1:
# MAGIC     st.subheader("Catalog")
# MAGIC     cat_pdf = load_catalog()
# MAGIC     st.dataframe(cat_pdf)
# MAGIC with col2:
# MAGIC     st.subheader("Netbacks")
# MAGIC     vals_pdf = load_valuations().sort_values("netback_usd_bbl", ascending=False)
# MAGIC     st.dataframe(vals_pdf)
# MAGIC with col3:
# MAGIC     st.subheader("Filters")
# MAGIC     min_api = st.number_input("Min API", min_value=0.0, max_value=60.0, value=33.0, step=0.1)
# MAGIC     max_sulfur = st.number_input("Max Sulfur (wt%)", min_value=0.0, max_value=5.0, value=1.5, step=0.1)
# MAGIC     target_vol = st.number_input("Target Volume (bbl)", min_value=0.0, value=120000.0, step=1000.0)
# MAGIC     data_path = st.text_input("Supply CSV (Volume path)", value="/Volumes/crude/assay/assay_data/blend_supply.csv")
# MAGIC 
# MAGIC st.divider()
# MAGIC st.subheader("Blend Optimization")
# MAGIC if st.button("Run Optimizer"):
# MAGIC     assays_pdf = load_assays()
# MAGIC     supply_pdf = load_supply(data_path)
# MAGIC     try:
# MAGIC         blend_df, metrics = optimize_blend(
# MAGIC             supply_df=supply_pdf,
# MAGIC             assays_df=assays_pdf,
# MAGIC             target_volume_bbl=float(target_vol),
# MAGIC             min_api=float(min_api),
# MAGIC             max_sulfur_wt=float(max_sulfur),
# MAGIC             solver="appsi_highs",
# MAGIC         )
# MAGIC         st.success("Optimization complete")
# MAGIC         st.write(metrics)
# MAGIC         st.dataframe(blend_df.sort_values("vol_bbl", ascending=False))
# MAGIC     except Exception as e:
# MAGIC         st.error(f"Optimization failed: {e}")
# MAGIC 
# MAGIC st.divider()
# MAGIC st.subheader("Price Sensitivity (if computed)")
# MAGIC try:
# MAGIC     ps = spark.table(f"{CATALOG}.{SCHEMA}.gold_price_sensitivity").toPandas()
# MAGIC     st.dataframe(ps.head(100))
# MAGIC except Exception:
# MAGIC     st.info("Run notebooks/04_price_sensitivity to populate gold_price_sensitivity.")
