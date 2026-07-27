//! Geometric Brownian motion price simulation (ported from crude-assay `monte_carlo.py`).

use rand::rngs::StdRng;
use rand::SeedableRng;
use rand_distr::{Distribution, Normal};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PriceSeries {
    pub closes: Vec<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MonteCarloConfig {
    pub iterations: usize,
    pub forecast_days: usize,
    pub seed: Option<u64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MonteCarloResult {
    pub start_price: f64,
    pub end_values: Vec<f64>,
    pub mean_forecast: f64,
    pub median_forecast: f64,
    pub std_dev: f64,
    pub percentile_5: f64,
    pub percentile_95: f64,
    pub confidence_interval_lower: f64,
    pub confidence_interval_upper: f64,
    pub probability_increase_pct: f64,
}

/// Estimate GBM drift and volatility from log returns.
pub fn estimate_gbm_params(closes: &[f64]) -> Result<(f64, f64), String> {
    if closes.len() < 2 {
        return Err("need at least 2 prices".into());
    }
    let log_returns: Vec<f64> = closes.windows(2).map(|w| (w[1] / w[0]).ln()).collect();
    let n = log_returns.len() as f64;
    let mean = log_returns.iter().sum::<f64>() / n;
    let var = log_returns.iter().map(|r| (r - mean).powi(2)).sum::<f64>() / n;
    let drift = mean - 0.5 * var;
    let stdev = var.sqrt();
    Ok((drift, stdev))
}

/// Run Monte Carlo simulation using closed-form end-of-horizon lognormal (Python parity).
pub fn simulate_gbm(
    series: &PriceSeries,
    config: &MonteCarloConfig,
) -> Result<MonteCarloResult, String> {
    let (drift, stdev) = estimate_gbm_params(&series.closes)?;
    let s0 = *series.closes.last().ok_or("empty price series")?;
    let n_days = config.forecast_days;

    let mut rng = match config.seed {
        Some(s) => StdRng::seed_from_u64(s),
        None => StdRng::from_os_rng(),
    };
    let normal = Normal::new(0.0, 1.0).map_err(|e| e.to_string())?;

    let mut end_values = Vec::with_capacity(config.iterations);
    for _ in 0..config.iterations {
        let z: f64 = normal.sample(&mut rng);
        let end = s0 * (n_days as f64 * drift + stdev * (n_days as f64).sqrt() * z).exp();
        end_values.push(end);
    }

    end_values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = end_values.len();
    let mean = end_values.iter().sum::<f64>() / n as f64;
    let median = end_values[n / 2];
    let variance = end_values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n as f64;
    let std_dev = variance.sqrt();
    let p5 = percentile(&end_values, 5.0);
    let p95 = percentile(&end_values, 95.0);
    let ci_lo = percentile(&end_values, 2.5);
    let ci_hi = percentile(&end_values, 97.5);
    let prob_up = end_values.iter().filter(|&&v| v > s0).count() as f64 / n as f64 * 100.0;

    Ok(MonteCarloResult {
        start_price: s0,
        end_values,
        mean_forecast: mean,
        median_forecast: median,
        std_dev,
        percentile_5: p5,
        percentile_95: p95,
        confidence_interval_lower: ci_lo,
        confidence_interval_upper: ci_hi,
        probability_increase_pct: prob_up,
    })
}

fn percentile(sorted: &[f64], pct: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let rank = (pct / 100.0) * (sorted.len() - 1) as f64;
    let lo = rank.floor() as usize;
    let hi = rank.ceil() as usize;
    if lo == hi {
        sorted[lo]
    } else {
        let frac = rank - lo as f64;
        sorted[lo] * (1.0 - frac) + sorted[hi] * frac
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_closes() -> PriceSeries {
        // Deterministic rising-ish series
        PriceSeries {
            closes: (0..252)
                .map(|i| 70.0 + (i as f64 * 0.05).sin() * 2.0 + i as f64 * 0.01)
                .collect(),
        }
    }

    #[test]
    fn gbm_reproducible_with_seed() {
        let series = sample_closes();
        let config = MonteCarloConfig {
            iterations: 500,
            forecast_days: 60,
            seed: Some(42),
        };
        let r1 = simulate_gbm(&series, &config).unwrap();
        let r2 = simulate_gbm(&series, &config).unwrap();
        assert_eq!(r1.mean_forecast, r2.mean_forecast);
        assert_eq!(r1.end_values.len(), 500);
    }
}
