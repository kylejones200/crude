# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Explore Crude Valuations with Regression Analytics

# COMMAND ----------
from pyspark.sql import functions as F
import matplotlib.pyplot as plt
import seaborn as sns

# Load traditional valuation data
assays = spark.table("gold_crude_catalog")
vals = spark.table("gold_crude_valuations")

# Load enhanced analytics with regression predictions
analytics = spark.table("gold_crude_analytics")

print("🛢️ TRADITIONAL VALUATION ANALYSIS")
print("=" * 50)
traditional = assays.join(vals, on="crude_id").orderBy(F.desc("netback_usd_bbl"))
traditional.show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Enhanced Valuation with Regression Predictions

# COMMAND ----------
print("🧠 ENHANCED ANALYTICS WITH REGRESSION")
print("=" * 50)

# Show top crudes by composite ranking
analytics.select(
    "crude_id", "name", "crude_rank", "crude_category",
    "netback_usd_bbl", "enhanced_gross_value", "quality_score", 
    "processing_index", "composite_score"
).orderBy("crude_rank").show(10, truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Valuation Comparison: Traditional vs Enhanced

# COMMAND ----------
# Compare traditional netback with enhanced predictions
comparison = analytics.select(
    "crude_id", "name",
    F.col("netback_usd_bbl").alias("traditional_netback"),
    F.col("enhanced_gross_value").alias("enhanced_value"),
    (F.col("enhanced_gross_value") - F.col("netback_usd_bbl")).alias("value_difference"),
    "quality_score", "composite_score"
).orderBy(F.desc("value_difference"))

print("📊 Crudes with Enhanced Value > Traditional Netback:")
comparison.filter(F.col("value_difference") > 0).show(10, truncate=False)

print("📉 Crudes with Traditional Netback > Enhanced Value:")
comparison.filter(F.col("value_difference") < 0).show(5, truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Quality-Based Insights

# COMMAND ----------
# Analyze crudes by quality tiers
analytics.withColumn(
    "quality_tier",
    F.when(F.col("quality_score") >= 8, "Premium")
     .when(F.col("quality_score") >= 6, "Standard") 
     .otherwise("Discount")
).groupBy("quality_tier").agg(
    F.count("crude_id").alias("crude_count"),
    F.avg("netback_usd_bbl").alias("avg_traditional_netback"),
    F.avg("enhanced_gross_value").alias("avg_enhanced_value"),
    F.avg("refinery_margin").alias("avg_refinery_margin")
).orderBy(F.desc("avg_enhanced_value")).show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Processing Complexity Analysis

# COMMAND ----------
# Analyze processing requirements
analytics.withColumn(
    "processing_complexity",
    F.when(F.col("processing_index") >= 80, "High Complexity")
     .when(F.col("processing_index") >= 60, "Medium Complexity")
     .otherwise("Low Complexity")
).groupBy("processing_complexity").agg(
    F.count("crude_id").alias("crude_count"),
    F.avg("refinery_margin").alias("avg_refinery_margin"),
    F.avg("quality_score").alias("avg_quality_score")
).show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Summary Insights

# COMMAND ----------
# Get key insights
total_crudes = analytics.count()
premium_crudes = analytics.filter(F.col("quality_score") >= 8).count()
high_value_crudes = analytics.filter(F.col("enhanced_gross_value") >= 85).count()

print(f"📈 PORTFOLIO INSIGHTS")
print(f"Total Crudes Analyzed: {total_crudes}")
print(f"Premium Quality Crudes (Score ≥ 8): {premium_crudes} ({premium_crudes/total_crudes*100:.1f}%)")
print(f"High Value Crudes (≥ $85/bbl): {high_value_crudes} ({high_value_crudes/total_crudes*100:.1f}%)")

# Best overall crude
best_crude = analytics.orderBy(F.desc("composite_score")).first()
print(f"\n🏆 Top Ranked Crude: {best_crude['name']} (Score: {best_crude['composite_score']:.1f})")
