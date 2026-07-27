//! Live WTI/Brent price fetch via Yahoo Finance chart API.

use crate::prices::{
    aggregate_daily_to_monthly, DailyPriceRow, PriceError, PriceHistoryFile, PriceResult,
};
use serde::Deserialize;
use std::collections::BTreeMap;

const BRENT_TICKERS: &[&str] = &["BZ=F", "BNO"];
const WTI_TICKERS: &[&str] = &["CL=F", "USO"];

#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct LivePrices {
    pub wti: Option<f64>,
    pub brent: Option<f64>,
}

#[derive(Debug, Deserialize)]
struct YahooChartResponse {
    chart: YahooChart,
}

#[derive(Debug, Deserialize)]
struct YahooChart {
    result: Option<Vec<YahooHistoryResult>>,
}

#[derive(Debug, Deserialize)]
struct YahooHistoryResult {
    timestamp: Option<Vec<i64>>,
    meta: Option<YahooMeta>,
    indicators: Option<YahooIndicators>,
}

#[derive(Debug, Deserialize)]
struct YahooIndicators {
    quote: Option<Vec<YahooQuote>>,
}

#[derive(Debug, Deserialize)]
struct YahooQuote {
    close: Option<Vec<Option<f64>>>,
}

#[derive(Debug, Deserialize)]
struct YahooMeta {
    #[serde(rename = "regularMarketPrice")]
    regular_market_price: Option<f64>,
}

/// Fetch current WTI and Brent spot prices (USD/bbl). Returns partial results on ticker failure.
pub fn fetch_live_wti_brent() -> PriceResult<LivePrices> {
    let brent = fetch_first_ticker(BRENT_TICKERS, "1d");
    let wti = fetch_first_ticker(WTI_TICKERS, "1d");
    if brent.is_none() && wti.is_none() {
        return Err(PriceError::Validation(
            "could not fetch WTI or Brent from Yahoo Finance".into(),
        ));
    }
    Ok(LivePrices { wti, brent })
}

/// Fetch merged daily WTI/Brent history for a Yahoo `range` (e.g. `1y`, `2y`, `5y`).
pub fn fetch_price_history(range: &str) -> PriceResult<PriceHistoryFile> {
    let wti = fetch_ticker_series(WTI_TICKERS[0], range)?;
    let brent = fetch_ticker_series(BRENT_TICKERS[0], range)?;

    let mut by_date: BTreeMap<String, DailyPriceRow> = BTreeMap::new();
    for (date, close) in wti {
        by_date
            .entry(date)
            .or_insert_with(|| DailyPriceRow {
                date: String::new(),
                brent: None,
                wti: None,
            })
            .wti = Some(close);
    }
    for (date, close) in brent {
        let row = by_date
            .entry(date.clone())
            .or_insert_with(|| DailyPriceRow {
                date: date.clone(),
                brent: None,
                wti: None,
            });
        row.date = date;
        row.brent = Some(close);
    }

    let mut daily: Vec<DailyPriceRow> = by_date.into_values().collect();
    for row in &mut daily {
        if row.date.is_empty() {
            continue;
        }
        if row.brent.is_none() {
            row.brent = row.wti;
        }
        if row.wti.is_none() {
            row.wti = row.brent;
        }
    }
    daily.retain(|r| r.wti.is_some() || r.brent.is_some());
    daily.sort_by(|a, b| a.date.cmp(&b.date));

    let closes: Vec<f64> = daily.iter().filter_map(|r| r.wti.or(r.brent)).collect();
    let monthly = if daily.is_empty() {
        vec![]
    } else {
        aggregate_daily_to_monthly(&daily)?
    };

    if daily.is_empty() {
        return Err(PriceError::Validation(format!(
            "no daily prices returned for range {range}"
        )));
    }

    Ok(PriceHistoryFile {
        daily,
        closes,
        monthly,
    })
}

fn fetch_first_ticker(tickers: &[&str], range: &str) -> Option<f64> {
    for ticker in tickers {
        if let Ok(price) = fetch_ticker_close(ticker, range) {
            if price > 0.0 {
                return Some(price);
            }
        }
    }
    None
}

fn fetch_ticker_close(ticker: &str, range: &str) -> PriceResult<f64> {
    if range == "1d" {
        let url = format!(
            "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        );
        let body: YahooChartResponse = yahoo_get(&url)?;
        return body
            .chart
            .result
            .and_then(|r| r.into_iter().next())
            .and_then(|r| r.meta)
            .and_then(|m| m.regular_market_price)
            .filter(|p| *p > 0.0)
            .ok_or_else(|| PriceError::Parse(format!("no spot price for {ticker}")));
    }

    let series = fetch_ticker_series(ticker, range)?;
    series
        .last()
        .map(|(_, close)| *close)
        .ok_or_else(|| PriceError::Parse(format!("no history for {ticker}")))
}

fn fetch_ticker_series(ticker: &str, range: &str) -> PriceResult<Vec<(String, f64)>> {
    let url = format!(
        "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={range}"
    );
    let body: YahooChartResponse = yahoo_get(&url)?;
    let result = body
        .chart
        .result
        .and_then(|mut r| r.pop())
        .ok_or_else(|| PriceError::Parse(format!("empty chart for {ticker}")))?;

    let timestamps = result
        .timestamp
        .ok_or_else(|| PriceError::Parse(format!("no timestamps for {ticker}")))?;
    let closes = result
        .indicators
        .and_then(|i| i.quote)
        .and_then(|mut q| q.pop())
        .and_then(|q| q.close)
        .ok_or_else(|| PriceError::Parse(format!("no closes for {ticker}")))?;

    let mut out = Vec::new();
    for (ts, close) in timestamps.iter().zip(closes.iter()) {
        let Some(close) = close else { continue };
        if *close <= 0.0 {
            continue;
        }
        let date = chrono::DateTime::from_timestamp(*ts, 0)
            .map(|dt| dt.format("%Y-%m-%d").to_string())
            .unwrap_or_else(|| ts.to_string());
        out.push((date, *close));
    }
    Ok(out)
}

fn yahoo_get(url: &str) -> PriceResult<YahooChartResponse> {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| PriceError::Parse(e.to_string()))?;
    let resp = client
        .get(url)
        .header("User-Agent", "crude-cli/0.1")
        .send()
        .map_err(|e| PriceError::Parse(e.to_string()))?;
    if !resp.status().is_success() {
        return Err(PriceError::Parse(format!("yahoo http {}", resp.status())));
    }
    resp.json().map_err(|e| PriceError::Parse(e.to_string()))
}
