//! Price series loading and monthly aggregation.

use crude_domain::MonthlyPrices;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, thiserror::Error)]
pub enum PriceError {
    #[error("parse error: {0}")]
    Parse(String),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("validation failed: {0}")]
    Validation(String),
}

pub type PriceResult<T> = Result<T, PriceError>;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct DailyPriceRow {
    pub date: String,
    pub brent: Option<f64>,
    pub wti: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PriceHistoryFile {
    #[serde(default)]
    pub daily: Vec<DailyPriceRow>,
    /// Simple close series for Monte Carlo (WTI or generic).
    #[serde(default)]
    pub closes: Vec<f64>,
    #[serde(default)]
    pub monthly: Vec<MonthlyPrices>,
}

impl PriceHistoryFile {
    pub fn from_json_file(path: &Path) -> PriceResult<Self> {
        let text = fs::read_to_string(path)?;
        serde_json::from_str(&text).map_err(|e| PriceError::Parse(e.to_string()))
    }

    pub fn monthly_prices(&self) -> PriceResult<Vec<MonthlyPrices>> {
        if !self.monthly.is_empty() {
            return Ok(self.monthly.clone());
        }
        if !self.daily.is_empty() {
            return aggregate_daily_to_monthly(&self.daily);
        }
        Err(PriceError::Validation(
            "price file must contain monthly or daily rows".into(),
        ))
    }
}

pub fn aggregate_daily_to_monthly(daily: &[DailyPriceRow]) -> PriceResult<Vec<MonthlyPrices>> {
    use std::collections::BTreeMap;

    let mut buckets: BTreeMap<String, Vec<(f64, f64)>> = BTreeMap::new();
    for row in daily {
        let month_key = if row.date.len() >= 7 {
            row.date[..7].to_string()
        } else {
            continue;
        };
        let brent = row.brent.unwrap_or(row.wti.unwrap_or(0.0));
        let wti = row.wti.unwrap_or(brent);
        buckets.entry(month_key).or_default().push((brent, wti));
    }

    Ok(buckets
        .into_values()
        .map(|vals| {
            let n = vals.len() as f64;
            let brent = vals.iter().map(|(b, _)| b).sum::<f64>() / n;
            let wti = vals.iter().map(|(_, w)| w).sum::<f64>() / n;
            MonthlyPrices { brent, wti }
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn aggregates_daily_to_monthly() {
        let daily = vec![
            DailyPriceRow {
                date: "2025-01-05".into(),
                brent: Some(80.0),
                wti: Some(75.0),
            },
            DailyPriceRow {
                date: "2025-01-20".into(),
                brent: Some(82.0),
                wti: Some(77.0),
            },
        ];
        let monthly = aggregate_daily_to_monthly(&daily).unwrap();
        assert_eq!(monthly.len(), 1);
        assert!((monthly[0].brent - 81.0).abs() < 1e-9);
    }
}
