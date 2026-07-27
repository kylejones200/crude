# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Crude Assay Regression Analysis
# MAGIC 
# MAGIC This notebook demonstrates advanced regression modeling for crude oil analytics including:
# MAGIC - Quality score predictions
# MAGIC - Processing complexity indices  
# MAGIC - Refinery margin estimation
# MAGIC - Comprehensive crude rankings
# MAGIC - Interactive visualization of regression relationships

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql import types as T
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set visualization style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Load Regression Predictions from Gold Tables

# COMMAND ----------
# Load the comprehensive analytics table with all predictions
analytics = spark.table("gold_crude_analytics")

# Display schema
print("Analytics Table Schema:")
analytics.printSchema()

# Show sample data
print("\nSample Analytics Data:")
analytics.orderBy(F.desc("composite_score")).show(10, truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Regression Summary Statistics

# COMMAND ----------
# Get regression summary statistics
summary_stats = spark.table("gold_regression_summary")
summary_stats.show(truncate=False)

# Convert to Pandas for easier analysis
summary_pd = summary_stats.toPandas()

print("\nRegression Prediction Ranges:")
print(f"Quality Score: {summary_pd['min_quality_score'].iloc[0]:.2f} - {summary_pd['max_quality_score'].iloc[0]:.2f}")
print(f"Processing Index: {summary_pd['min_processing_index'].iloc[0]:.2f} - {summary_pd['max_processing_index'].iloc[0]:.2f}")
print(f"Refinery Margin: {summary_pd['min_refinery_margin'].iloc[0]:.2f} - {summary_pd['max_refinery_margin'].iloc[0]:.2f}")
print(f"Enhanced Gross Value: ${summary_pd['min_enhanced_gross_value'].iloc[0]:.2f} - ${summary_pd['max_enhanced_gross_value'].iloc[0]:.2f}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Top Ranked Crudes Analysis

# COMMAND ----------
# Get top and bottom ranked crudes
top_crudes = analytics.orderBy(F.desc("composite_score")).limit(5)
bottom_crudes = analytics.orderBy(F.asc("composite_score")).limit(5)

print("🏆 TOP 5 RANKED CRUDES")
print("=" * 50)
top_crudes.select(
    "crude_rank", "crude_id", "name", "crude_category",
    "composite_score", "quality_score", "enhanced_gross_value", 
    "refinery_margin", "processing_index"
).show(truncate=False)

print("⚠️  BOTTOM 5 RANKED CRUDES")  
print("=" * 50)
bottom_crudes.select(
    "crude_rank", "crude_id", "name", "crude_category",
    "composite_score", "quality_score", "enhanced_gross_value",
    "refinery_margin", "processing_index"
).show(truncate=False)

# COMMAND ----------
# MAGIC %md  
# MAGIC ## Regression Relationship Visualizations

# COMMAND ----------
# Convert to Pandas for matplotlib visualizations
analytics_pd = analytics.toPandas()

# Create comprehensive regression analysis plots
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('Crude Assay Regression Analysis', fontsize=16, fontweight='bold')

# 1. API Gravity vs Quality Score
axes[0, 0].scatter(analytics_pd['api'], analytics_pd['quality_score'], alpha=0.7, s=60)
axes[0, 0].set_xlabel('API Gravity (°API)')
axes[0, 0].set_ylabel('Quality Score')
axes[0, 0].set_title('API Gravity vs Quality Score')
axes[0, 0].grid(True, alpha=0.3)

# Add trend line
z = np.polyfit(analytics_pd['api'], analytics_pd['quality_score'], 1)
p = np.poly1d(z)
axes[0, 0].plot(analytics_pd['api'], p(analytics_pd['api']), "r--", alpha=0.8)

# 2. Sulfur Content vs Quality Score  
axes[0, 1].scatter(analytics_pd['sulfur_wt'], analytics_pd['quality_score'], alpha=0.7, s=60, color='orange')
axes[0, 1].set_xlabel('Sulfur Content (wt%)')
axes[0, 1].set_ylabel('Quality Score')
axes[0, 1].set_title('Sulfur Content vs Quality Score')
axes[0, 1].grid(True, alpha=0.3)

# 3. Enhanced Gross Value vs Netback Value
axes[0, 2].scatter(analytics_pd['enhanced_gross_value'], analytics_pd['netback_usd_bbl'], alpha=0.7, s=60, color='green')
axes[0, 2].set_xlabel('Enhanced Gross Value ($/bbl)')
axes[0, 2].set_ylabel('Netback Value ($/bbl)')
axes[0, 2].set_title('Enhanced vs Traditional Valuation')
axes[0, 2].grid(True, alpha=0.3)

# 4. Processing Index vs Refinery Margin
axes[1, 0].scatter(analytics_pd['processing_index'], analytics_pd['refinery_margin'], alpha=0.7, s=60, color='red')
axes[1, 0].set_xlabel('Processing Index')
axes[1, 0].set_ylabel('Refinery Margin ($/bbl)')
axes[1, 0].set_title('Processing Complexity vs Margin')
axes[1, 0].grid(True, alpha=0.3)

# 5. Composite Score Distribution
axes[1, 1].hist(analytics_pd['composite_score'], bins=15, alpha=0.7, color='purple')
axes[1, 1].set_xlabel('Composite Score')
axes[1, 1].set_ylabel('Number of Crudes')
axes[1, 1].set_title('Composite Score Distribution')
axes[1, 1].grid(True, alpha=0.3)

# 6. Crude Category Analysis
category_counts = analytics_pd['crude_category'].value_counts()
axes[1, 2].pie(category_counts.values, labels=category_counts.index, autopct='%1.1f%%', startangle=90)
axes[1, 2].set_title('Crude Oil Categories')

plt.tight_layout()
plt.show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Correlation Analysis

# COMMAND ----------
# Calculate correlation matrix for key regression variables
correlation_vars = [
    'api', 'sulfur_wt', 'cut_light_pct', 'cut_middle_pct', 'cut_heavy_pct',
    'quality_score', 'processing_index', 'refinery_margin', 'enhanced_gross_value',
    'netback_usd_bbl', 'composite_score'
]

correlation_data = analytics_pd[correlation_vars]
correlation_matrix = correlation_data.corr()

# Create correlation heatmap
plt.figure(figsize=(14, 10))
sns.heatmap(correlation_matrix, annot=True, cmap='RdBu_r', center=0, 
           square=True, linewidths=0.5, cbar_kws={"shrink": 0.5})
plt.title('Crude Assay Variables Correlation Matrix', fontsize=16, fontweight='bold', pad=20)
plt.tight_layout()
plt.show()

# Print strongest correlations
print("🔍 STRONGEST CORRELATIONS")
print("=" * 40)
correlation_pairs = []
for i in range(len(correlation_matrix.columns)):
    for j in range(i+1, len(correlation_matrix.columns)):
        var1 = correlation_matrix.columns[i]
        var2 = correlation_matrix.columns[j]
        corr = correlation_matrix.iloc[i, j]
        correlation_pairs.append((abs(corr), var1, var2, corr))

# Sort by absolute correlation and show top 10
correlation_pairs.sort(reverse=True)
for _, var1, var2, corr in correlation_pairs[:10]:
    print(f"{var1:20s} ↔ {var2:20s}: {corr:6.3f}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Crude Portfolio Optimization Insights

# COMMAND ----------
# Identify optimal crude portfolio characteristics
print("📊 CRUDE PORTFOLIO OPTIMIZATION INSIGHTS")
print("=" * 50)

# Sweet vs Sour analysis
sweet_crudes = analytics.filter(F.col("sulfur_wt") < 0.5)
sour_crudes = analytics.filter(F.col("sulfur_wt") >= 0.5)

print(f"Sweet Crudes (S < 0.5%): {sweet_crudes.count()} crudes")
print(f"Average Quality Score: {sweet_crudes.agg(F.avg('quality_score')).collect()[0][0]:.2f}")
print(f"Average Enhanced Value: ${sweet_crudes.agg(F.avg('enhanced_gross_value')).collect()[0][0]:.2f}/bbl")

print(f"\nSour Crudes (S >= 0.5%): {sour_crudes.count()} crudes")  
print(f"Average Quality Score: {sour_crudes.agg(F.avg('quality_score')).collect()[0][0]:.2f}")
print(f"Average Enhanced Value: ${sour_crudes.agg(F.avg('enhanced_gross_value')).collect()[0][0]:.2f}/bbl")

# Light vs Heavy analysis
light_crudes = analytics.filter(F.col("api") > 31.1)
heavy_crudes = analytics.filter(F.col("api") <= 22.3)

print(f"\nLight Crudes (API > 31.1°): {light_crudes.count()} crudes")
print(f"Average Processing Index: {light_crudes.agg(F.avg('processing_index')).collect()[0][0]:.2f}")
print(f"Average Refinery Margin: ${light_crudes.agg(F.avg('refinery_margin')).collect()[0][0]:.2f}/bbl")

print(f"\nHeavy Crudes (API <= 22.3°): {heavy_crudes.count()} crudes")
print(f"Average Processing Index: {heavy_crudes.agg(F.avg('processing_index')).collect()[0][0]:.2f}")
print(f"Average Refinery Margin: ${heavy_crudes.agg(F.avg('refinery_margin')).collect()[0][0]:.2f}/bbl")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Regression Model Validation

# COMMAND ----------
# Compare enhanced valuation with traditional valuation
valuation_comparison = analytics.select(
    "crude_id", "name", 
    F.col("netback_usd_bbl").alias("traditional_netback"),
    F.col("enhanced_gross_value").alias("enhanced_gross_value"), 
    (F.col("enhanced_gross_value") - F.col("netback_usd_bbl")).alias("valuation_diff"),
    "quality_score", "processing_index"
).orderBy(F.desc("valuation_diff"))

print("🔍 VALUATION MODEL COMPARISON")
print("=" * 60)
print("Crudes with largest positive differences (enhanced > traditional):")
valuation_comparison.limit(5).show(truncate=False)

print("\nCrudes with largest negative differences (traditional > enhanced):")
valuation_comparison.orderBy("valuation_diff").limit(5).show(truncate=False)

# Calculate correlation between models
correlation = analytics.stat.corr("netback_usd_bbl", "enhanced_gross_value")
print(f"\nCorrelation between Traditional and Enhanced Valuations: {correlation:.4f}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Export Regression Results for Downstream Use

# COMMAND ----------
# Create a summary table for optimization and reporting
optimization_summary = analytics.select(
    "crude_id", "name", "crude_category", "crude_rank",
    "api", "sulfur_wt", 
    "cut_light_pct", "cut_middle_pct", "cut_heavy_pct",
    "quality_score", "processing_index", "refinery_margin",
    "netback_usd_bbl", "enhanced_gross_value", "composite_score"
).orderBy("crude_rank")

# Save as a temporary view for other notebooks
optimization_summary.createOrReplaceTempView("crude_optimization_data")

print("✅ Created 'crude_optimization_data' temporary view for downstream analysis")
print(f"   Contains {optimization_summary.count()} crude records with regression predictions")

# Show final summary
print("\n📋 FINAL REGRESSION ANALYSIS SUMMARY")
print("=" * 50)
optimization_summary.show(20, truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Interactive Regression Dashboard Query Examples

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Query examples for interactive dashboards
# MAGIC 
# MAGIC -- Top 10 crudes by composite score
# MAGIC SELECT crude_id, name, crude_category, composite_score, quality_score, enhanced_gross_value
# MAGIC FROM gold_crude_analytics
# MAGIC ORDER BY composite_score DESC
# MAGIC LIMIT 10;

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Sweet vs Sour crude performance comparison
# MAGIC SELECT 
# MAGIC   CASE WHEN sulfur_wt < 0.5 THEN 'Sweet' ELSE 'Sour' END as sweetness,
# MAGIC   COUNT(*) as crude_count,
# MAGIC   AVG(quality_score) as avg_quality_score,
# MAGIC   AVG(enhanced_gross_value) as avg_enhanced_value,
# MAGIC   AVG(refinery_margin) as avg_refinery_margin,
# MAGIC   AVG(processing_index) as avg_processing_index
# MAGIC FROM gold_crude_analytics
# MAGIC GROUP BY CASE WHEN sulfur_wt < 0.5 THEN 'Sweet' ELSE 'Sour' END
# MAGIC ORDER BY avg_quality_score DESC;

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Crude category performance matrix
# MAGIC SELECT 
# MAGIC   crude_category,
# MAGIC   COUNT(*) as count,
# MAGIC   AVG(composite_score) as avg_composite_score,
# MAGIC   MIN(composite_score) as min_composite_score, 
# MAGIC   MAX(composite_score) as max_composite_score,
# MAGIC   AVG(enhanced_gross_value) as avg_value,
# MAGIC   AVG(quality_score) as avg_quality
# MAGIC FROM gold_crude_analytics
# MAGIC GROUP BY crude_category
# MAGIC ORDER BY avg_composite_score DESC;
