import streamlit as st
import pandas as pd

# Ensure the project root (parent of app/) is on sys.path so `src` imports resolve in Apps
import os, sys
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from pyspark.sql import functions as F
    spark  # type: ignore[name-defined]
except Exception:
    # Running as a Code App may not define 'spark' implicitly; create one
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    from pyspark.sql import functions as F

try:
    from src.optimization.blend_pyomo import optimize_blend
except Exception as e:
    optimize_blend = None
    _import_err = e

CATALOG = "crude"
SCHEMA = "assay"

st.set_page_config(page_title="Crude Assay App", layout="wide")
st.title("Crude Assay App")

@st.cache_data(ttl=120)
def load_catalog():
    return spark.table(f"{CATALOG}.{SCHEMA}.gold_crude_catalog").toPandas()

@st.cache_data(ttl=120)
def load_valuations():
    return spark.table(f"{CATALOG}.{SCHEMA}.gold_crude_valuations").toPandas()

@st.cache_data(ttl=120)
def load_assays():
    return spark.table(f"{CATALOG}.{SCHEMA}.silver_assays").select("crude_id","api","sulfur_wt").toPandas()

@st.cache_data(ttl=120)
def load_supply(path:str):
    df = spark.read.option("header", True).csv(path).select(
        F.col("crude_id"),
        F.col("cost_usd_bbl").cast("double"),
        F.col("available_bbl").cast("double"),
    ).toPandas()
    return df

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("Catalog")
    try:
        cat_pdf = load_catalog()
        st.dataframe(cat_pdf)
    except Exception as e:
        st.error(f"Failed to load catalog: {e}")
with col2:
    st.subheader("Netbacks")
    try:
        vals_pdf = load_valuations().sort_values("netback_usd_bbl", ascending=False)
        st.dataframe(vals_pdf)
    except Exception as e:
        st.error(f"Failed to load valuations: {e}")
with col3:
    st.subheader("Filters")
    min_api = st.number_input("Min API", min_value=0.0, max_value=60.0, value=33.0, step=0.1)
    max_sulfur = st.number_input("Max Sulfur (wt%)", min_value=0.0, max_value=5.0, value=1.5, step=0.1)
    target_vol = st.number_input("Target Volume (bbl)", min_value=0.0, value=120000.0, step=1000.0)
    data_path = st.text_input("Supply CSV (Volume path)", value="/Volumes/crude/assay/assay_data/blend_supply.csv")

st.divider()
st.subheader("Blend Optimization")
if optimize_blend is None:
    st.warning("Pyomo optimizer is unavailable. Ensure 'pyomo' and 'highspy' are installed on the app cluster. Import error: {}".format(_import_err))
else:
    if st.button("Run Optimizer"):
        try:
            assays_pdf = load_assays()
            supply_pdf = load_supply(data_path)
            blend_df, metrics = optimize_blend(
                supply_df=supply_pdf,
                assays_df=assays_pdf,
                target_volume_bbl=float(target_vol),
                min_api=float(min_api),
                max_sulfur_wt=float(max_sulfur),
                solver="appsi_highs",
            )
            st.success("Optimization complete")
            st.json(metrics)
            st.dataframe(blend_df.sort_values("vol_bbl", ascending=False))
        except Exception as e:
            st.error(f"Optimization failed: {e}")

st.divider()
st.subheader("Price Sensitivity (if computed)")
try:
    ps = spark.table(f"{CATALOG}.{SCHEMA}.gold_price_sensitivity").toPandas()
    st.dataframe(ps.head(100))
except Exception:
    st.info("Run notebooks/04_price_sensitivity to populate gold_price_sensitivity.")
