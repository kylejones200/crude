//! Disk cache for Yahoo price fetches.

use crate::fetch::{fetch_live_wti_brent, fetch_price_history, LivePrices};
use crate::prices::{PriceError, PriceHistoryFile, PriceResult};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Duration;

const DEFAULT_CACHE_TTL_SECS: u64 = 86_400; // 24h
const HISTORY_CACHE_TTL_SECS: u64 = 86_400;

#[derive(Clone, Debug)]
pub struct PriceCacheConfig {
    pub cache_dir: PathBuf,
    pub live_ttl: Duration,
    pub history_ttl: Duration,
}

impl Default for PriceCacheConfig {
    fn default() -> Self {
        Self {
            cache_dir: default_cache_dir(),
            live_ttl: Duration::from_secs(DEFAULT_CACHE_TTL_SECS),
            history_ttl: Duration::from_secs(HISTORY_CACHE_TTL_SECS),
        }
    }
}

impl PriceCacheConfig {
    pub fn from_env() -> Self {
        let mut cfg = Self::default();
        if let Ok(dir) = std::env::var("CRUDE_CACHE_DIR") {
            cfg.cache_dir = PathBuf::from(dir);
        }
        cfg
    }
}

fn default_cache_dir() -> PathBuf {
    dirs_cache_home().join("crude")
}

fn dirs_cache_home() -> PathBuf {
    if let Ok(home) = std::env::var("HOME") {
        return PathBuf::from(home).join(".cache");
    }
    PathBuf::from(".cache")
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct CachedLive {
    fetched_at: DateTime<Utc>,
    prices: LivePrices,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct CachedHistory {
    fetched_at: DateTime<Utc>,
    range: String,
    history: PriceHistoryFile,
}

/// Fetch spot WTI/Brent, using a JSON cache when fresh.
pub fn fetch_live_cached(config: &PriceCacheConfig, force: bool) -> PriceResult<LivePrices> {
    let path = config.cache_dir.join("live-prices.json");
    if !force {
        if let Some(cached) = read_live_cache(&path, config.live_ttl) {
            return Ok(cached);
        }
    }
    let prices = fetch_live_wti_brent()?;
    write_live_cache(&path, &prices)?;
    Ok(prices)
}

/// Fetch daily price history for `range` (e.g. `2y`), with disk cache.
pub fn fetch_history_cached(
    config: &PriceCacheConfig,
    range: &str,
    force: bool,
) -> PriceResult<PriceHistoryFile> {
    let safe_range = sanitize_range(range);
    let path = config.cache_dir.join(format!("history-{safe_range}.json"));
    if !force {
        if let Some(cached) = read_history_cache(&path, config.history_ttl) {
            return Ok(cached);
        }
    }
    let history = fetch_price_history(range)?;
    write_history_cache(&path, range, &history)?;
    Ok(history)
}

fn sanitize_range(range: &str) -> String {
    range
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '_' })
        .collect()
}

fn read_live_cache(path: &Path, ttl: Duration) -> Option<LivePrices> {
    let text = fs::read_to_string(path).ok()?;
    let cached: CachedLive = serde_json::from_str(&text).ok()?;
    if cache_fresh(cached.fetched_at, ttl) {
        Some(cached.prices)
    } else {
        None
    }
}

fn write_live_cache(path: &Path, prices: &LivePrices) -> PriceResult<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let cached = CachedLive {
        fetched_at: Utc::now(),
        prices: prices.clone(),
    };
    let json =
        serde_json::to_string_pretty(&cached).map_err(|e| PriceError::Parse(e.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

fn read_history_cache(path: &Path, ttl: Duration) -> Option<PriceHistoryFile> {
    let text = fs::read_to_string(path).ok()?;
    let cached: CachedHistory = serde_json::from_str(&text).ok()?;
    if cache_fresh(cached.fetched_at, ttl) {
        Some(cached.history)
    } else {
        None
    }
}

fn write_history_cache(path: &Path, range: &str, history: &PriceHistoryFile) -> PriceResult<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let cached = CachedHistory {
        fetched_at: Utc::now(),
        range: range.to_string(),
        history: history.clone(),
    };
    let json =
        serde_json::to_string_pretty(&cached).map_err(|e| PriceError::Parse(e.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

fn cache_fresh(fetched_at: DateTime<Utc>, ttl: Duration) -> bool {
    let age = Utc::now()
        .signed_duration_since(fetched_at)
        .to_std()
        .unwrap_or(Duration::MAX);
    age < ttl
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_cache_dir() -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("crude-price-cache-{nanos}"))
    }

    #[test]
    fn live_cache_roundtrip() {
        let dir = temp_cache_dir();
        let cfg = PriceCacheConfig {
            cache_dir: dir.clone(),
            live_ttl: Duration::from_secs(3600),
            history_ttl: Duration::from_secs(3600),
        };
        let prices = LivePrices {
            wti: Some(71.0),
            brent: Some(75.0),
        };
        write_live_cache(&dir.join("live-prices.json"), &prices).unwrap();
        let cached = fetch_live_cached(&cfg, false).unwrap();
        assert_eq!(cached.wti, Some(71.0));
        let _ = fs::remove_dir_all(&dir);
    }
}
