-- Dashboard Views for Crude Assay Analytics with Regression Integration
-- These views provide pre-computed analytics for Databricks dashboards and reporting

-- View 1: Crude Portfolio Overview with Regression Analytics
CREATE OR REPLACE VIEW crude_portfolio_overview AS
SELECT 
  c.crude_id,
       c.name,
       c.api,
       c.sulfur_wt,
  v.netback_usd_bbl as traditional_netback,
  p.enhanced_gross_value,
  p.quality_score,
  p.processing_index,
  p.refinery_margin,
  p.crude_category,
  r.composite_score,
  r.crude_rank,
  -- Performance indicators
  CASE 
    WHEN p.quality_score >= 8 THEN 'Premium'
    WHEN p.quality_score >= 6 THEN 'Standard' 
    ELSE 'Discount'
  END as quality_tier,
  CASE
    WHEN p.processing_index >= 80 THEN 'High Complexity'
    WHEN p.processing_index >= 60 THEN 'Medium Complexity'
    ELSE 'Low Complexity'
  END as processing_complexity,
  -- Value metrics
  (p.enhanced_gross_value - v.netback_usd_bbl) as value_uplift,
  p.enhanced_gross_value / v.netback_usd_bbl as value_ratio
FROM gold_crude_catalog c
JOIN gold_crude_valuations v ON c.crude_id = v.crude_id
JOIN gold_crude_predictions p ON c.crude_id = p.crude_id  
JOIN gold_crude_rankings r ON c.crude_id = r.crude_id;

-- View 2: Quality Distribution Analysis
CREATE OR REPLACE VIEW quality_distribution_analysis AS
SELECT
  CASE 
    WHEN quality_score >= 9 THEN 'Excellent (9-10)'
    WHEN quality_score >= 8 THEN 'Premium (8-9)'
    WHEN quality_score >= 6 THEN 'Standard (6-8)'
    WHEN quality_score >= 4 THEN 'Below Standard (4-6)'
    ELSE 'Poor (0-4)'
  END as quality_category,
  COUNT(*) as crude_count,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(AVG(enhanced_gross_value), 2) as avg_enhanced_value,
  ROUND(AVG(netback_usd_bbl), 2) as avg_traditional_netback,
  ROUND(AVG(refinery_margin), 2) as avg_refinery_margin,
  ROUND(AVG(processing_index), 2) as avg_processing_index,
  ROUND(MIN(quality_score), 2) as min_quality_score,
  ROUND(MAX(quality_score), 2) as max_quality_score
FROM crude_portfolio_overview
GROUP BY 
  CASE 
    WHEN quality_score >= 9 THEN 'Excellent (9-10)'
    WHEN quality_score >= 8 THEN 'Premium (8-9)'
    WHEN quality_score >= 6 THEN 'Standard (6-8)'
    WHEN quality_score >= 4 THEN 'Below Standard (4-6)'
    ELSE 'Poor (0-4)'
  END
ORDER BY avg_quality_score DESC;

-- View 3: Processing Complexity Analysis
CREATE OR REPLACE VIEW processing_complexity_analysis AS
SELECT 
  processing_complexity,
  COUNT(*) as crude_count,
  ROUND(AVG(processing_index), 2) as avg_processing_index,
  ROUND(AVG(refinery_margin), 2) as avg_refinery_margin,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(AVG(api), 2) as avg_api,
  ROUND(AVG(sulfur_wt), 2) as avg_sulfur,
  ROUND(AVG(enhanced_gross_value), 2) as avg_enhanced_value
FROM crude_portfolio_overview  
GROUP BY processing_complexity
ORDER BY avg_processing_index;

-- View 4: Sweet vs Sour Crude Comparison
CREATE OR REPLACE VIEW sweet_sour_comparison AS
SELECT
  CASE 
    WHEN sulfur_wt < 0.5 THEN 'Sweet'
    WHEN sulfur_wt < 2.5 THEN 'Medium Sour'
    ELSE 'High Sour'
  END as sweetness_category,
  COUNT(*) as crude_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage_of_portfolio,
  ROUND(AVG(sulfur_wt), 3) as avg_sulfur_wt,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(AVG(enhanced_gross_value), 2) as avg_enhanced_value,
  ROUND(AVG(processing_index), 2) as avg_processing_index,
  ROUND(AVG(refinery_margin), 2) as avg_refinery_margin,
  ROUND(MIN(sulfur_wt), 3) as min_sulfur,
  ROUND(MAX(sulfur_wt), 3) as max_sulfur
FROM crude_portfolio_overview
GROUP BY 
  CASE 
    WHEN sulfur_wt < 0.5 THEN 'Sweet'
    WHEN sulfur_wt < 2.5 THEN 'Medium Sour'
    ELSE 'High Sour'
  END
ORDER BY avg_quality_score DESC;

-- View 5: Light vs Heavy Crude Analysis
CREATE OR REPLACE VIEW light_heavy_analysis AS
SELECT
  CASE 
    WHEN api > 31.1 THEN 'Light'
    WHEN api > 22.3 THEN 'Medium'  
    ELSE 'Heavy'
  END as gravity_category,
  COUNT(*) as crude_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage_of_portfolio,
  ROUND(AVG(api), 2) as avg_api,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(AVG(enhanced_gross_value), 2) as avg_enhanced_value,
  ROUND(AVG(processing_index), 2) as avg_processing_index,
  ROUND(AVG(refinery_margin), 2) as avg_refinery_margin,
  ROUND(MIN(api), 1) as min_api,
  ROUND(MAX(api), 1) as max_api
FROM crude_portfolio_overview
GROUP BY 
  CASE 
    WHEN api > 31.1 THEN 'Light'
    WHEN api > 22.3 THEN 'Medium'  
    ELSE 'Heavy'
  END
ORDER BY avg_api DESC;

-- View 6: Top Performers Dashboard
CREATE OR REPLACE VIEW top_performers_dashboard AS
SELECT 
  'Top 10 by Composite Score' as metric_category,
  crude_id,
  name,
  crude_rank,
  ROUND(composite_score, 2) as metric_value,
  ROUND(quality_score, 2) as quality_score,
  ROUND(enhanced_gross_value, 2) as enhanced_value,
  crude_category
FROM crude_portfolio_overview
WHERE crude_rank <= 10

UNION ALL

SELECT 
  'Top 10 by Enhanced Value' as metric_category,
  crude_id,
  name,
  ROW_NUMBER() OVER (ORDER BY enhanced_gross_value DESC) as crude_rank,
  ROUND(enhanced_gross_value, 2) as metric_value,
  ROUND(quality_score, 2) as quality_score,
  ROUND(enhanced_gross_value, 2) as enhanced_value,
  crude_category
FROM crude_portfolio_overview
ORDER BY metric_category, metric_value DESC
LIMIT 20;

-- View 7: Value Enhancement Analysis  
CREATE OR REPLACE VIEW value_enhancement_analysis AS
SELECT 
  crude_id,
  name,
  ROUND(traditional_netback, 2) as traditional_netback,
  ROUND(enhanced_gross_value, 2) as enhanced_gross_value,
  ROUND(value_uplift, 2) as value_uplift,
  ROUND(value_ratio, 3) as value_ratio,
  CASE 
    WHEN value_uplift > 5 THEN 'High Enhancement'
    WHEN value_uplift > 2 THEN 'Medium Enhancement'  
    WHEN value_uplift > -2 THEN 'Neutral'
    ELSE 'Value Reduction'
  END as enhancement_category,
  ROUND(quality_score, 2) as quality_score,
  crude_category
FROM crude_portfolio_overview
ORDER BY value_uplift DESC;

-- View 8: Regression Model Performance Summary
CREATE OR REPLACE VIEW regression_model_summary AS
SELECT 
  'Quality Score' as prediction_metric,
  ROUND(AVG(quality_score), 2) as avg_prediction,
  ROUND(STDDEV(quality_score), 2) as stddev_prediction,
  ROUND(MIN(quality_score), 2) as min_prediction,
  ROUND(MAX(quality_score), 2) as max_prediction,
  COUNT(*) as sample_count

UNION ALL

SELECT 
  'Processing Index' as prediction_metric,
  ROUND(AVG(processing_index), 2) as avg_prediction,
  ROUND(STDDEV(processing_index), 2) as stddev_prediction,
  ROUND(MIN(processing_index), 2) as min_prediction,
  ROUND(MAX(processing_index), 2) as max_prediction,
  COUNT(*) as sample_count

UNION ALL

SELECT 
  'Refinery Margin' as prediction_metric,
  ROUND(AVG(refinery_margin), 2) as avg_prediction,
  ROUND(STDDEV(refinery_margin), 2) as stddev_prediction,
  ROUND(MIN(refinery_margin), 2) as min_prediction,
  ROUND(MAX(refinery_margin), 2) as max_prediction,
  COUNT(*) as sample_count

UNION ALL

SELECT 
  'Enhanced Gross Value' as prediction_metric,
  ROUND(AVG(enhanced_gross_value), 2) as avg_prediction,
  ROUND(STDDEV(enhanced_gross_value), 2) as stddev_prediction,
  ROUND(MIN(enhanced_gross_value), 2) as min_prediction,
  ROUND(MAX(enhanced_gross_value), 2) as max_prediction,
  COUNT(*) as sample_count

FROM crude_portfolio_overview
ORDER BY prediction_metric;

-- View 9: Correlation Insights
CREATE OR REPLACE VIEW correlation_insights AS
WITH correlation_data AS (
  SELECT 
    api,
    sulfur_wt,
    quality_score,
    processing_index, 
    refinery_margin,
    enhanced_gross_value,
    traditional_netback,
    composite_score
  FROM crude_portfolio_overview
)
SELECT 
  'API vs Quality Score' as correlation_pair,
  ROUND(CORR(api, quality_score), 3) as correlation_coefficient,
  COUNT(*) as sample_size
FROM correlation_data

UNION ALL

SELECT 
  'Sulfur vs Quality Score' as correlation_pair,
  ROUND(CORR(sulfur_wt, quality_score), 3) as correlation_coefficient,
  COUNT(*) as sample_size
FROM correlation_data

UNION ALL

SELECT 
  'Processing Index vs Refinery Margin' as correlation_pair,
  ROUND(CORR(processing_index, refinery_margin), 3) as correlation_coefficient,
  COUNT(*) as sample_size
FROM correlation_data

UNION ALL

SELECT 
  'Enhanced vs Traditional Value' as correlation_pair,
  ROUND(CORR(enhanced_gross_value, traditional_netback), 3) as correlation_coefficient,
  COUNT(*) as sample_size
FROM correlation_data

UNION ALL

SELECT 
  'Quality Score vs Composite Score' as correlation_pair,
  ROUND(CORR(quality_score, composite_score), 3) as correlation_coefficient,
  COUNT(*) as sample_size
FROM correlation_data

ORDER BY ABS(correlation_coefficient) DESC;

-- View 10: Monthly Trend Analysis (Placeholder - would use real time-series data)
CREATE OR REPLACE VIEW monthly_trend_placeholder AS
SELECT 
  CURRENT_DATE() as analysis_date,
  'Static Analysis' as period_type,
  COUNT(*) as total_crudes,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(AVG(enhanced_gross_value), 2) as avg_enhanced_value,
  ROUND(AVG(processing_index), 2) as avg_processing_index,
  COUNT(CASE WHEN quality_tier = 'Premium' THEN 1 END) as premium_crude_count,
  COUNT(CASE WHEN crude_category LIKE '%Sweet%' THEN 1 END) as sweet_crude_count
FROM crude_portfolio_overview;

-- View 11: Optimization Readiness Assessment
CREATE OR REPLACE VIEW optimization_readiness AS
SELECT 
  crude_id,
  name,
  -- Basic optimization readiness score
  CASE 
    WHEN quality_score >= 7 AND processing_index <= 70 AND enhanced_gross_value >= 80 THEN 'Excellent'
    WHEN quality_score >= 5 AND processing_index <= 80 AND enhanced_gross_value >= 75 THEN 'Good'
    WHEN quality_score >= 3 AND processing_index <= 90 THEN 'Fair'
    ELSE 'Poor'
  END as optimization_readiness,
  
  -- Individual component scores
  CASE WHEN quality_score >= 7 THEN 'High' WHEN quality_score >= 5 THEN 'Medium' ELSE 'Low' END as quality_rating,
  CASE WHEN processing_index <= 70 THEN 'Low' WHEN processing_index <= 80 THEN 'Medium' ELSE 'High' END as processing_complexity_rating,
  CASE WHEN enhanced_gross_value >= 85 THEN 'High' WHEN enhanced_gross_value >= 80 THEN 'Medium' ELSE 'Low' END as value_rating,
  CASE WHEN refinery_margin >= 15 THEN 'High' WHEN refinery_margin >= 10 THEN 'Medium' ELSE 'Low' END as margin_rating,
  
  -- Key metrics
  ROUND(quality_score, 2) as quality_score,
  ROUND(processing_index, 2) as processing_index,  
  ROUND(enhanced_gross_value, 2) as enhanced_gross_value,
  ROUND(refinery_margin, 2) as refinery_margin,
  crude_category
  
FROM crude_portfolio_overview
ORDER BY 
  CASE optimization_readiness
    WHEN 'Excellent' THEN 1
    WHEN 'Good' THEN 2  
    WHEN 'Fair' THEN 3
    ELSE 4
  END,
  quality_score DESC;