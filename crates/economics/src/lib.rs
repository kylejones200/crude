//! Economic calculations for crude blending.

mod cache;
mod fetch;
mod prices;

pub use cache::{fetch_history_cached, fetch_live_cached, PriceCacheConfig};
pub use fetch::{fetch_live_wti_brent, fetch_price_history, LivePrices};
pub use prices::{
    aggregate_daily_to_monthly, DailyPriceRow, PriceError, PriceHistoryFile, PriceResult,
};

use crude_domain::CrudeId;
use std::collections::HashMap;

/// Heuristic crude value from crude-blending `blend_solver._calculate_value`.
pub fn heuristic_crude_value_usd_per_bbl(api_gravity: f64, sulfur_wt_pct: f64) -> f64 {
    80.0 + (api_gravity - 30.0) * 0.5 - sulfur_wt_pct * 2.0
}

/// Feed cost for a volume allocation (USD).
pub fn feed_cost(
    volumes_bbl: &HashMap<CrudeId, f64>,
    prices_usd_per_bbl: &HashMap<CrudeId, f64>,
) -> f64 {
    volumes_bbl
        .iter()
        .filter_map(|(id, vol)| prices_usd_per_bbl.get(id).map(|p| vol * p))
        .sum()
}

/// Average feed cost per barrel.
pub fn feed_cost_per_bbl(
    volumes_bbl: &HashMap<CrudeId, f64>,
    prices_usd_per_bbl: &HashMap<CrudeId, f64>,
) -> Option<f64> {
    let total_vol: f64 = volumes_bbl.values().sum();
    if total_vol <= 0.0 {
        return None;
    }
    Some(feed_cost(volumes_bbl, prices_usd_per_bbl) / total_vol)
}
