try:
    import dlt  # real DLT decorators available when running as a pipeline
except Exception:
    # Fallback shim so this module can be imported outside a DLT pipeline without errors
    class _DLTShim:
        def table(self, *args, **kwargs):
            def _decorator(fn):
                return fn
            return _decorator

        def view(self, *args, **kwargs):
            def _decorator(fn):
                return fn
            return _decorator

    dlt = _DLTShim()  # type: ignore
from pyspark.sql import functions as F
from pyspark.sql import types as T

from src.schemas import assays_schema, prices_schema, freight_schema
from src.valuation_engine import compute_crude_value, apply_freight
from src.regression_engine_spark import add_regression_predictions, create_crude_ranking, create_regression_summary_stats

# Resolve data base path from pipeline configuration; fall back to UC Volume.
try:
    BASE_PATH = spark.conf.get("assay.data.base_path")
except Exception:
    BASE_PATH = "/Volumes/crude/assay/assay_data"

@dlt.view(name="bronze_assays")
def bronze_assays():
    return (
        spark.read.option("header", True)
             .schema(assays_schema)
             .csv(f"{BASE_PATH}/assays.csv")
    )

@dlt.view(name="bronze_prices")
def bronze_prices():
    return (
        spark.read.option("header", True)
             .schema(prices_schema)
             .csv(f"{BASE_PATH}/prices.csv")
    )

@dlt.view(name="bronze_freight")
def bronze_freight():
    return (
        spark.read.option("header", True)
             .schema(freight_schema)
             .csv(f"{BASE_PATH}/freight_routes.csv")
    )

@dlt.table(name="silver_assays")
def silver_assays():
    df = dlt.read("bronze_assays")
    return (
        df.withColumn("cut_light_pct", F.col("cut_light_pct").cast("double"))
          .withColumn("cut_middle_pct", F.col("cut_middle_pct").cast("double"))
          .withColumn("cut_heavy_pct", F.col("cut_heavy_pct").cast("double"))
          .withColumn("api", F.col("api").cast("double"))
          .withColumn("sulfur_wt", F.col("sulfur_wt").cast("double"))
          .withColumn("total_pct", F.col("cut_light_pct") + F.col("cut_middle_pct") + F.col("cut_heavy_pct"))
          .filter(F.abs(F.col("total_pct") - F.lit(1.0)) <= 0.0001)
          .drop("total_pct")
    )

@dlt.table(name="silver_prices")
def silver_prices():
    return dlt.read("bronze_prices").dropna()

@dlt.table(name="silver_freight")
def silver_freight():
    return dlt.read("bronze_freight").dropna()

@dlt.table(name="gold_crude_catalog")
def gold_crude_catalog():
    return dlt.read("silver_assays").select("crude_id", "name", "api", "sulfur_wt")

@dlt.table(name="gold_crude_valuations")
def gold_crude_valuations():
    assays = dlt.read("silver_assays")
    prices = dlt.read("silver_prices")
    freight = dlt.read("silver_freight")

    gross = compute_crude_value(assays, prices)
    net = apply_freight(gross, freight)

    return net

@dlt.table(name="gold_crude_predictions")
def gold_crude_predictions():
    """
    Comprehensive regression predictions for crude assays including:
    - Quality scores
    - Processing complexity indices
    - Refinery margins
    - Enhanced valuations
    - Crude categorization
    """
    assays = dlt.read("silver_assays")
    
    # Add regression predictions
    predictions = add_regression_predictions(assays)
    
    return predictions

@dlt.table(name="gold_crude_rankings")
def gold_crude_rankings():
    """
    Ranked crude oils based on composite scoring of multiple regression predictions.
    """
    predictions = dlt.read("gold_crude_predictions")
    
    # Create comprehensive rankings
    rankings = create_crude_ranking(predictions)
    
    return rankings

@dlt.table(name="gold_regression_summary")
def gold_regression_summary():
    """
    Summary statistics for all regression predictions across the crude portfolio.
    """
    predictions = dlt.read("gold_crude_predictions")
    
    return create_regression_summary_stats(predictions)

@dlt.table(name="gold_crude_analytics")
def gold_crude_analytics():
    """
    Combined analytics table joining valuations with regression predictions.
    This provides a comprehensive view for downstream analysis and optimization.
    """
    valuations = dlt.read("gold_crude_valuations")
    predictions = dlt.read("gold_crude_predictions") 
    rankings = dlt.read("gold_crude_rankings")
    
    # Join all analytics together
    analytics = (valuations
                 .join(predictions, on="crude_id", how="inner")
                 .join(rankings.select("crude_id", "composite_score", "crude_rank"), 
                       on="crude_id", how="inner")
                )
    
    return analytics

@dlt.table(name="gold_market_data")
def gold_market_data():
    """
    Live market data for crude oil prices and market indicators.
    Updated from Yahoo Finance integration.
    """
    try:
        # Try to read live prices from market data
        live_prices = (spark.read.option("header", "true")
                           .option("inferSchema", "true")
                           .csv(f"{BASE_PATH}/live_prices.csv"))
        return live_prices
    except:
        # Fallback to static prices if live data unavailable
        return dlt.read("silver_prices")

@dlt.table(name="gold_source_system_data") 
def gold_source_system_data():
    """
    Consolidated view of data from various source systems
    (PI, Intertek, BLISS, LIMS, AspenTech, Haverly).
    """
    
    # Read source system data files
    try:
        pi_data = (spark.read.option("header", "true")
                      .option("inferSchema", "true") 
                      .csv(f"{BASE_PATH}/pi_system_data.csv")
                      .withColumn("source_system", F.lit("PI")))
        
        intertek_data = (spark.read.option("header", "true")
                            .option("inferSchema", "true")
                            .csv(f"{BASE_PATH}/intertek_lab_reports.csv")
                            .withColumn("source_system", F.lit("Intertek")))
        
        bliss_data = (spark.read.option("header", "true")
                         .option("inferSchema", "true")
                         .csv(f"{BASE_PATH}/bliss_blend_recipes.csv")
                         .withColumn("source_system", F.lit("BLISS")))
        
        lims_data = (spark.read.option("header", "true")
                        .option("inferSchema", "true")
                        .csv(f"{BASE_PATH}/lims_quality_tests.csv")
                        .withColumn("source_system", F.lit("LIMS")))
        
        aspentech_data = (spark.read.option("header", "true")
                             .option("inferSchema", "true")
                             .csv(f"{BASE_PATH}/aspentech_planning.csv")
                             .withColumn("source_system", F.lit("AspenTech")))
        
        haverly_data = (spark.read.option("header", "true")
                           .option("inferSchema", "true")
                           .csv(f"{BASE_PATH}/haverly_optimization.csv")
                           .withColumn("source_system", F.lit("Haverly")))
        
        # Create summary of source system data quality and availability
        source_summary = spark.createDataFrame([
            ("PI", pi_data.count(), "Real-time operational data"),
            ("Intertek", intertek_data.count(), "Laboratory analysis reports"),
            ("BLISS", bliss_data.count(), "Blend optimization recipes"),
            ("LIMS", lims_data.count(), "Quality control tests"),
            ("AspenTech", aspentech_data.count(), "Planning scenarios"),
            ("Haverly", haverly_data.count(), "Optimization results")
        ], ["system_name", "record_count", "data_type"])
        
        return source_summary
        
    except Exception as e:
        # Return empty DataFrame with schema if files not available
        return spark.createDataFrame([], 
            schema="system_name string, record_count int, data_type string")

@dlt.table(name="gold_quality_analytics")
def gold_quality_analytics():
    """
    Enhanced quality analytics combining lab data with regression predictions.
    """
    assays = dlt.read("silver_assays") 
    predictions = dlt.read("gold_crude_predictions")
    
    # Join assay data with predictions
    quality_analytics = (assays
                        .join(predictions.select("crude_id", "quality_score", "crude_category"), 
                              on="crude_id", how="left")
                        .withColumn("sweet_sour_flag", 
                                   F.when(F.col("sulfur_wt") < 0.5, "Sweet")
                                    .otherwise("Sour"))
                        .withColumn("gravity_category",
                                   F.when(F.col("api") > 31.1, "Light")
                                    .when(F.col("api") > 22.3, "Medium")
                                    .otherwise("Heavy"))
                        .withColumn("quality_tier",
                                   F.when(F.col("quality_score") >= 8, "Premium")
                                    .when(F.col("quality_score") >= 6, "Standard")
                                    .otherwise("Discount")))
    
    return quality_analytics
