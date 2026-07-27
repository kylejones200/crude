# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # Enhanced Blend Optimization with Regression Analytics
# MAGIC 
# MAGIC This notebook demonstrates advanced crude oil blend optimization that incorporates:
# MAGIC - Regression-based quality scores and processing indices
# MAGIC - Enhanced valuation models 
# MAGIC - Multiple optimization strategies comparison
# MAGIC - Processing complexity constraints
# MAGIC - Quality-based blending optimization

# COMMAND ----------
import sys
sys.path.append("/dbfs/FileStore/assay")  # Adjust path as needed

from src.optimization.enhanced_blend_optimization import EnhancedBlendOptimizer, compare_optimization_strategies
from pyspark.sql import functions as F
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# COMMAND ----------
# MAGIC %md
# MAGIC ## Load Enhanced Analytics Data

# COMMAND ----------
# Load the comprehensive analytics data with regression predictions
analytics_spark = spark.table("gold_crude_analytics")
analytics_spark.show(10, truncate=False)

# Convert to Pandas for optimization
analytics_df = analytics_spark.toPandas()

print(f"Loaded {len(analytics_df)} crudes with enhanced analytics")
print("\nAvailable columns:")
print(analytics_df.columns.tolist())

# COMMAND ----------
# MAGIC %md
# MAGIC ## Setup Optimization Parameters

# COMMAND ----------
# Define supply limits (example - replace with real supply data)
supply_limits = {}
for crude_id in analytics_df['crude_id']:
    # Example: random supply between 10K and 100K barrels
    import random
    supply_limits[crude_id] = random.uniform(10000, 100000)

print("Sample Supply Limits:")
for i, (crude, limit) in enumerate(list(supply_limits.items())[:5]):
    print(f"  {crude}: {limit:,.0f} bbl")

# Define crude costs (example - could be based on market prices)
crude_costs = {}
for crude_id in analytics_df['crude_id']:
    # Example: cost as percentage of enhanced value
    enhanced_value = analytics_df[analytics_df['crude_id'] == crude_id]['enhanced_gross_value'].iloc[0]
    crude_costs[crude_id] = enhanced_value * random.uniform(0.85, 0.95)  # 85-95% of value

# Target blend volume
target_volume = 50000  # 50,000 barrels

print(f"\nTarget blend volume: {target_volume:,} barrels")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Define Optimization Constraints

# COMMAND ----------
# Quality constraints
quality_constraints = {
    'min_api': 28.0,           # Minimum API gravity
    'max_sulfur': 2.0,         # Maximum sulfur content
    'min_quality_score': 6.0,  # Minimum regression quality score
    'min_cut_light_pct': 0.25  # Minimum light cuts yield
}

# Processing constraints (using regression analytics)
processing_constraints = {
    'max_processing_index': 75.0,   # Maximum processing complexity
    'min_refinery_margin': 8.0      # Minimum refinery margin
}

print("Quality Constraints:")
for key, value in quality_constraints.items():
    print(f"  {key}: {value}")

print("\nProcessing Constraints:")
for key, value in processing_constraints.items():
    print(f"  {key}: {value}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Strategy Comparison: Multiple Optimization Approaches

# COMMAND ----------
print("🔄 Running optimization strategy comparison...")

# Compare different optimization strategies
comparison_results = compare_optimization_strategies(
    analytics_df,
    supply_limits,
    crude_costs,
    target_volume,
    quality_constraints,
    processing_constraints
)

print("✅ Optimization comparison complete!")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Results Analysis

# COMMAND ----------
print("📊 OPTIMIZATION STRATEGY COMPARISON")
print("=" * 60)

for strategy, result in comparison_results.items():
    print(f"\n🎯 {strategy.upper().replace('_', ' ')}")
    print("-" * 40)
    
    if result['status'] == 'optimal':
        print(f"Status: ✅ {result['status']}")
        print(f"Total Value: ${result['total_value']:,.2f}")
        print(f"Total Cost: ${result.get('total_cost', 0):,.2f}")
        print(f"Avg $/bbl: ${result['avg_value_per_barrel']:.2f}")
        print(f"Crudes Used: {len([k for k, v in result['blend_composition'].items() if v['volume'] > 100])}")
        
        # Blend properties
        props = result['blend_properties']
        print(f"Blended API: {props.get('blended_api', 0):.1f}°")
        print(f"Blended Sulfur: {props.get('blended_sulfur_wt', 0):.2f}%")
        if 'blended_quality_score' in props:
            print(f"Blended Quality Score: {props['blended_quality_score']:.1f}")
        if 'blended_processing_index' in props:
            print(f"Blended Processing Index: {props['blended_processing_index']:.1f}")
    else:
        print(f"Status: ❌ {result['status']}")
        if 'error' in result:
            print(f"Error: {result['error']}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Detailed Blend Composition Analysis

# COMMAND ----------
# Analyze the best performing strategy (enhanced value maximization)
best_result = comparison_results.get('enhanced_value_max', {})

if best_result.get('status') == 'optimal':
    print("🏆 ENHANCED VALUE MAXIMIZATION - DETAILED RESULTS")
    print("=" * 60)
    
    blend_composition = best_result['blend_composition']
    
    # Create detailed composition DataFrame
    composition_data = []
    for crude_id, details in blend_composition.items():
        if details['volume'] > 100:  # Only significant volumes
            composition_data.append({
                'crude_id': crude_id,
                'volume': details['volume'],
                'percentage': details['percentage'],
                'value_per_barrel': details['value_per_barrel'],
                'api': details['api'],
                'sulfur_wt': details['sulfur_wt'],
                'quality_score': details.get('quality_score', 0),
                'processing_index': details.get('processing_index', 0),
                'refinery_margin': details.get('refinery_margin', 0)
            })
    
    composition_df = pd.DataFrame(composition_data).sort_values('percentage', ascending=False)
    
    print("Blend Composition:")
    print(composition_df.to_string(index=False, float_format='%.2f'))
    
    # Visualize blend composition
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Enhanced Blend Optimization Results', fontsize=16, fontweight='bold')
    
    # Volume pie chart
    axes[0, 0].pie(composition_df['percentage'], labels=composition_df['crude_id'], 
                   autopct='%1.1f%%', startangle=90)
    axes[0, 0].set_title('Blend Composition by Volume')
    
    # Value contribution bar chart
    value_contribution = composition_df['volume'] * composition_df['value_per_barrel']
    axes[0, 1].bar(range(len(composition_df)), value_contribution)
    axes[0, 1].set_xlabel('Crude Index')
    axes[0, 1].set_ylabel('Total Value Contribution ($)')
    axes[0, 1].set_title('Value Contribution by Crude')
    axes[0, 1].set_xticks(range(len(composition_df)))
    axes[0, 1].set_xticklabels(composition_df['crude_id'], rotation=45)
    
    # Quality score vs processing index scatter
    axes[1, 0].scatter(composition_df['quality_score'], composition_df['processing_index'], 
                       s=composition_df['percentage']*10, alpha=0.7)
    axes[1, 0].set_xlabel('Quality Score')
    axes[1, 0].set_ylabel('Processing Index')
    axes[1, 0].set_title('Quality vs Processing Complexity\n(bubble size = blend %)')
    
    # API vs Sulfur scatter
    axes[1, 1].scatter(composition_df['api'], composition_df['sulfur_wt'],
                       s=composition_df['percentage']*10, alpha=0.7)
    axes[1, 1].set_xlabel('API Gravity')
    axes[1, 1].set_ylabel('Sulfur Content (wt%)')
    axes[1, 1].set_title('API vs Sulfur Content\n(bubble size = blend %)')
    
    plt.tight_layout()
    plt.show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Strategy Performance Comparison

# COMMAND ----------
# Create comparison summary
comparison_summary = []

for strategy, result in comparison_results.items():
    if result.get('status') == 'optimal':
        props = result.get('blend_properties', {})
        comparison_summary.append({
            'strategy': strategy.replace('_', ' ').title(),
            'total_value': result['total_value'],
            'total_cost': result.get('total_cost', 0),
            'value_per_barrel': result['avg_value_per_barrel'],
            'cost_per_barrel': result.get('avg_cost_per_barrel', 0),
            'blended_api': props.get('blended_api', 0),
            'blended_sulfur': props.get('blended_sulfur_wt', 0),
            'quality_score': props.get('blended_quality_score', 0),
            'processing_index': props.get('blended_processing_index', 0),
            'crudes_used': len([k for k, v in result['blend_composition'].items() if v['volume'] > 100])
        })

if comparison_summary:
    summary_df = pd.DataFrame(comparison_summary)
    
    print("📊 STRATEGY PERFORMANCE COMPARISON")
    print("=" * 60)
    print(summary_df.to_string(index=False, float_format='%.2f'))
    
    # Visualization
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Optimization Strategy Comparison', fontsize=16, fontweight='bold')
    
    # Total value comparison
    axes[0, 0].bar(summary_df['strategy'], summary_df['total_value'])
    axes[0, 0].set_ylabel('Total Value ($)')
    axes[0, 0].set_title('Total Value by Strategy')
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # Value per barrel comparison
    axes[0, 1].bar(summary_df['strategy'], summary_df['value_per_barrel'])
    axes[0, 1].set_ylabel('Value per Barrel ($/bbl)')
    axes[0, 1].set_title('Value per Barrel by Strategy')
    axes[0, 1].tick_params(axis='x', rotation=45)
    
    # Quality score comparison
    quality_data = summary_df[summary_df['quality_score'] > 0]
    if not quality_data.empty:
        axes[0, 2].bar(quality_data['strategy'], quality_data['quality_score'])
        axes[0, 2].set_ylabel('Blended Quality Score')
        axes[0, 2].set_title('Quality Score by Strategy')
        axes[0, 2].tick_params(axis='x', rotation=45)
    
    # Blended API
    axes[1, 0].bar(summary_df['strategy'], summary_df['blended_api'])
    axes[1, 0].set_ylabel('Blended API Gravity')
    axes[1, 0].set_title('API Gravity by Strategy')
    axes[1, 0].tick_params(axis='x', rotation=45)
    
    # Blended sulfur
    axes[1, 1].bar(summary_df['strategy'], summary_df['blended_sulfur'])
    axes[1, 1].set_ylabel('Blended Sulfur (wt%)')
    axes[1, 1].set_title('Sulfur Content by Strategy')
    axes[1, 1].tick_params(axis='x', rotation=45)
    
    # Number of crudes used
    axes[1, 2].bar(summary_df['strategy'], summary_df['crudes_used'])
    axes[1, 2].set_ylabel('Number of Crudes')
    axes[1, 2].set_title('Crudes Used by Strategy')
    axes[1, 2].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Sensitivity Analysis

# COMMAND ----------
# Analyze sensitivity to quality constraints
print("🔍 SENSITIVITY ANALYSIS")
print("=" * 50)

optimizer = EnhancedBlendOptimizer()

# Test different API requirements
api_sensitivity = []
api_values = [25.0, 27.0, 29.0, 31.0, 33.0, 35.0]

for min_api in api_values:
    test_constraints = quality_constraints.copy()
    test_constraints['min_api'] = min_api
    
    try:
        result = optimizer.optimize_value_maximization(
            analytics_df, supply_limits, target_volume,
            use_enhanced_value=True, quality_constraints=test_constraints
        )
        
        if result['status'] == 'optimal':
            api_sensitivity.append({
                'min_api': min_api,
                'total_value': result['total_value'],
                'value_per_barrel': result['avg_value_per_barrel'],
                'blended_api': result['blend_properties']['blended_api']
            })
    except Exception as e:
        print(f"Failed for min_api = {min_api}: {e}")

if api_sensitivity:
    sensitivity_df = pd.DataFrame(api_sensitivity)
    
    print("API Sensitivity Analysis:")
    print(sensitivity_df.to_string(index=False, float_format='%.2f'))
    
    # Plot sensitivity
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.plot(sensitivity_df['min_api'], sensitivity_df['value_per_barrel'], 'o-')
    plt.xlabel('Minimum API Requirement')
    plt.ylabel('Value per Barrel ($/bbl)')
    plt.title('Value Sensitivity to API Constraint')
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.plot(sensitivity_df['min_api'], sensitivity_df['blended_api'], 'o-')
    plt.xlabel('Minimum API Requirement')
    plt.ylabel('Actual Blended API')
    plt.title('Blended API vs Constraint')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Export Optimization Results

# COMMAND ----------
# Create summary for downstream use
if 'enhanced_value_max' in comparison_results and comparison_results['enhanced_value_max']['status'] == 'optimal':
    
    # Create optimization summary table
    opt_result = comparison_results['enhanced_value_max']
    
    # Blend composition
    composition_records = []
    for crude_id, details in opt_result['blend_composition'].items():
        if details['volume'] > 100:
            composition_records.append({
                'crude_id': crude_id,
                'volume_bbl': details['volume'],
                'percentage': details['percentage'],
                'value_per_barrel': details['value_per_barrel'],
                'api': details['api'],
                'sulfur_wt': details['sulfur_wt'],
                'quality_score': details.get('quality_score', 0),
                'processing_index': details.get('processing_index', 0),
                'refinery_margin': details.get('refinery_margin', 0),
                'total_contribution': details['volume'] * details['value_per_barrel']
            })
    
    composition_spark = spark.createDataFrame(pd.DataFrame(composition_records))
    composition_spark.createOrReplaceTempView("optimized_blend_composition")
    
    # Blend properties summary
    props = opt_result['blend_properties']
    summary_record = {
        'optimization_type': opt_result['optimization_type'],
        'total_value': opt_result['total_value'],
        'total_volume': opt_result['total_volume'],
        'avg_value_per_barrel': opt_result['avg_value_per_barrel'],
        'blended_api': props.get('blended_api', 0),
        'blended_sulfur_wt': props.get('blended_sulfur_wt', 0),
        'blended_quality_score': props.get('blended_quality_score', 0),
        'blended_processing_index': props.get('blended_processing_index', 0),
        'blended_refinery_margin': props.get('blended_refinery_margin', 0),
        'crudes_in_blend': len(composition_records)
    }
    
    summary_spark = spark.createDataFrame([summary_record])
    summary_spark.createOrReplaceTempView("optimized_blend_summary")
    
    print("✅ Created optimization result views:")
    print("   - optimized_blend_composition")
    print("   - optimized_blend_summary")
    
    print("\n📋 FINAL OPTIMIZATION SUMMARY")
    print("=" * 50)
    composition_spark.orderBy(F.desc("percentage")).show(20, truncate=False)
    
    print("\nBlend Properties:")
    summary_spark.show(truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## SQL Views for Dashboard Integration

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Optimized blend composition for dashboards
# MAGIC SELECT 
# MAGIC   crude_id,
# MAGIC   volume_bbl,
# MAGIC   percentage,
# MAGIC   value_per_barrel,
# MAGIC   api,
# MAGIC   sulfur_wt,
# MAGIC   quality_score,
# MAGIC   processing_index,
# MAGIC   total_contribution
# MAGIC FROM optimized_blend_composition
# MAGIC ORDER BY percentage DESC;

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Optimization summary metrics  
# MAGIC SELECT 
# MAGIC   optimization_type,
# MAGIC   total_value,
# MAGIC   avg_value_per_barrel,
# MAGIC   blended_api,
# MAGIC   blended_sulfur_wt,
# MAGIC   blended_quality_score,
# MAGIC   blended_processing_index,
# MAGIC   crudes_in_blend
# MAGIC FROM optimized_blend_summary;
