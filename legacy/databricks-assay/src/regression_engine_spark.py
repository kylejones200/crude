"""
Spark-compatible regression engine for crude assay predictions.

This module provides PySpark UDFs and functions for regression predictions
that can be used in Delta Live Tables and Databricks notebooks.
"""

from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql import DataFrame
import math


def create_regression_udfs():
    """
    Create PySpark UDFs for regression predictions.
    Returns a dictionary of UDF functions.
    """
    
    @F.udf(returnType=T.DoubleType())
    def predict_quality_score(api_gravity, sulfur_content):
        """
        Predict crude quality score based on API gravity and sulfur content.
        Score ranges from 0-10 with higher being better quality.
        """
        if api_gravity is None or sulfur_content is None:
            return None
        
        # API component (higher API = higher quality)
        api_score = min(10.0, float(api_gravity) / 4.0)
        
        # Sulfur component (lower sulfur = higher quality) 
        sulfur_score = max(0.0, 10.0 - float(sulfur_content) * 2.5)
        
        # Combined score
        return (api_score + sulfur_score) / 2.0
    
    @F.udf(returnType=T.DoubleType())
    def predict_processing_index(api_gravity, sulfur_content, light_cuts, middle_cuts, heavy_cuts):
        """
        Predict processing complexity index (0-100).
        Higher values indicate more complex/expensive processing.
        """
        if any(x is None for x in [api_gravity, sulfur_content, light_cuts, middle_cuts, heavy_cuts]):
            return None
        
        api = float(api_gravity)
        sulfur = float(sulfur_content)
        light = float(light_cuts)
        middle = float(middle_cuts)
        heavy = float(heavy_cuts)
        
        # API factor (higher API = easier processing)
        api_factor = api * 1.2
        
        # Sulfur penalty (higher sulfur = more complex processing)
        sulfur_penalty = sulfur * 10.0
        
        # Cut yield bonuses/penalties
        light_bonus = light * 60.0  # Light cuts are valuable
        middle_bonus = middle * 45.0  # Middle distillates are good
        heavy_penalty = heavy * 25.0  # Heavy cuts require more processing
        
        index = api_factor - sulfur_penalty + light_bonus + middle_bonus - heavy_penalty
        
        # Constrain to 0-100 range
        return max(0.0, min(100.0, index))
    
    @F.udf(returnType=T.DoubleType())
    def predict_refinery_margin(api_gravity, sulfur_content, light_cuts, middle_cuts, heavy_cuts):
        """
        Predict refinery margin potential in $/bbl.
        """
        if any(x is None for x in [api_gravity, sulfur_content, light_cuts, middle_cuts, heavy_cuts]):
            return None
            
        api = float(api_gravity)
        sulfur = float(sulfur_content)
        light = float(light_cuts)
        middle = float(middle_cuts)
        heavy = float(heavy_cuts)
        
        # Base margin from crude characteristics
        base_margin = 5.0  # Base refinery margin
        
        # API bonus (light crudes have higher margins)
        api_bonus = (api - 30.0) * 0.3
        
        # Sulfur penalty (sour crudes reduce margins)
        sulfur_penalty = sulfur * 1.5
        
        # Yield adjustments
        light_bonus = light * 15.0  # High gasoline yield increases margin
        middle_bonus = middle * 12.0  # Diesel yield bonus
        heavy_penalty = heavy * 8.0   # Heavy products reduce margin
        
        margin = base_margin + api_bonus - sulfur_penalty + light_bonus + middle_bonus - heavy_penalty
        
        return max(-5.0, min(25.0, margin))  # Constrain to realistic range
    
    @F.udf(returnType=T.StringType())
    def predict_crude_category(api_gravity, sulfur_content):
        """
        Categorize crude oil based on API gravity and sulfur content.
        """
        if api_gravity is None or sulfur_content is None:
            return "Unknown"
        
        api = float(api_gravity)
        sulfur = float(sulfur_content)
        
        # API categories
        if api > 31.1:
            gravity_cat = "Light"
        elif api > 22.3:
            gravity_cat = "Medium"
        else:
            gravity_cat = "Heavy"
        
        # Sulfur categories
        if sulfur < 0.5:
            sulfur_cat = "Sweet"
        else:
            sulfur_cat = "Sour"
        
        return f"{gravity_cat} {sulfur_cat}"
    
    @F.udf(returnType=T.DoubleType())
    def predict_transportation_cost(api_gravity, origin_region):
        """
        Predict transportation cost based on crude type and origin.
        """
        if api_gravity is None:
            return 2.0  # Default transportation cost
        
        api = float(api_gravity)
        
        # Base cost by origin region
        region_costs = {
            "ME": 2.5,    # Middle East
            "WAF": 1.8,   # West Africa
            "USG": 0.5,   # US Gulf
            "USWC": 1.2,  # US West Coast
            "NSea": 1.5,  # North Sea
        }
        
        base_cost = region_costs.get(origin_region, 2.0)
        
        # Light crudes may have premium transportation
        if api > 35:
            base_cost *= 1.1  # 10% premium for very light crudes
        elif api < 25:
            base_cost *= 0.9  # 10% discount for heavy crudes (less demand)
        
        return base_cost
    
    return {
        'predict_quality_score': predict_quality_score,
        'predict_processing_index': predict_processing_index,
        'predict_refinery_margin': predict_refinery_margin,
        'predict_crude_category': predict_crude_category,
        'predict_transportation_cost': predict_transportation_cost
    }


def add_regression_predictions(df: DataFrame, product_prices: dict = None) -> DataFrame:
    """
    Add regression prediction columns to a crude assay DataFrame.
    
    Args:
        df: Input DataFrame with crude assay data
        product_prices: Dictionary of product prices (optional)
        
    Returns:
        DataFrame with additional regression prediction columns
    """
    
    # Default product prices
    if product_prices is None:
        product_prices = {
            'lights': 88.0,
            'middles': 82.0,
            'heavies': 75.0
        }
    
    # Create UDFs
    udfs = create_regression_udfs()
    
    # Add predictions
    result_df = df.withColumn(
        "quality_score",
        udfs['predict_quality_score'](F.col("api"), F.col("sulfur_wt"))
    ).withColumn(
        "processing_index", 
        udfs['predict_processing_index'](
            F.col("api"), F.col("sulfur_wt"), 
            F.col("cut_light_pct"), F.col("cut_middle_pct"), F.col("cut_heavy_pct")
        )
    ).withColumn(
        "refinery_margin",
        udfs['predict_refinery_margin'](
            F.col("api"), F.col("sulfur_wt"),
            F.col("cut_light_pct"), F.col("cut_middle_pct"), F.col("cut_heavy_pct")
        )
    ).withColumn(
        "crude_category",
        udfs['predict_crude_category'](F.col("api"), F.col("sulfur_wt"))
    )
    
    # Add enhanced gross value prediction incorporating API gravity
    enhanced_gross_value = (
        F.col("cut_light_pct") * F.lit(product_prices['lights']) +
        F.col("cut_middle_pct") * F.lit(product_prices['middles']) +
        F.col("cut_heavy_pct") * F.lit(product_prices['heavies']) +
        (F.col("api") - F.lit(30.0)) * F.lit(0.8)  # API gravity adjustment
    )
    
    result_df = result_df.withColumn("enhanced_gross_value", enhanced_gross_value)
    
    return result_df


def create_regression_summary_stats(df: DataFrame) -> DataFrame:
    """
    Create summary statistics for regression predictions.
    
    Args:
        df: DataFrame with regression predictions
        
    Returns:
        DataFrame with summary statistics
    """
    
    summary_stats = df.agg(
        F.avg("quality_score").alias("avg_quality_score"),
        F.min("quality_score").alias("min_quality_score"),
        F.max("quality_score").alias("max_quality_score"),
        F.stddev("quality_score").alias("stddev_quality_score"),
        
        F.avg("processing_index").alias("avg_processing_index"),
        F.min("processing_index").alias("min_processing_index"),
        F.max("processing_index").alias("max_processing_index"),
        F.stddev("processing_index").alias("stddev_processing_index"),
        
        F.avg("refinery_margin").alias("avg_refinery_margin"),
        F.min("refinery_margin").alias("min_refinery_margin"),
        F.max("refinery_margin").alias("max_refinery_margin"),
        F.stddev("refinery_margin").alias("stddev_refinery_margin"),
        
        F.avg("enhanced_gross_value").alias("avg_enhanced_gross_value"),
        F.min("enhanced_gross_value").alias("min_enhanced_gross_value"),
        F.max("enhanced_gross_value").alias("max_enhanced_gross_value"),
        F.stddev("enhanced_gross_value").alias("stddev_enhanced_gross_value"),
        
        F.count("crude_id").alias("total_crudes")
    )
    
    return summary_stats


def create_crude_ranking(df: DataFrame, ranking_weights: dict = None) -> DataFrame:
    """
    Create a composite ranking of crudes based on multiple regression predictions.
    
    Args:
        df: DataFrame with regression predictions
        ranking_weights: Dictionary of weights for different metrics
        
    Returns:
        DataFrame with composite ranking scores
    """
    
    # Default weights for composite score
    if ranking_weights is None:
        ranking_weights = {
            'quality_score': 0.3,
            'enhanced_gross_value': 0.4,
            'refinery_margin': 0.2,
            'processing_index': -0.1  # Negative because lower processing complexity is better
        }
    
    # Normalize scores to 0-100 scale for composite ranking
    quality_normalized = (F.col("quality_score") / F.lit(10.0)) * F.lit(100.0)
    
    # Normalize enhanced gross value (assume range of $70-$95)
    value_normalized = ((F.col("enhanced_gross_value") - F.lit(70.0)) / F.lit(25.0)) * F.lit(100.0)
    
    # Normalize refinery margin (assume range of -5 to 25)
    margin_normalized = ((F.col("refinery_margin") - F.lit(-5.0)) / F.lit(30.0)) * F.lit(100.0)
    
    # Normalize processing index (already 0-100)
    processing_normalized = F.col("processing_index")
    
    # Calculate composite score
    composite_score = (
        quality_normalized * F.lit(ranking_weights['quality_score']) +
        value_normalized * F.lit(ranking_weights['enhanced_gross_value']) + 
        margin_normalized * F.lit(ranking_weights['refinery_margin']) +
        processing_normalized * F.lit(ranking_weights['processing_index'])
    )
    
    # Add ranking
    ranked_df = df.withColumn("composite_score", composite_score).withColumn(
        "crude_rank", 
        F.row_number().over(
            F.Window.orderBy(F.desc("composite_score"))
        )
    )
    
    return ranked_df
