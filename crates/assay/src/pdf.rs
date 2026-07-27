//! PDF text extraction for assay reports (ported from crude-assay `assay_parser.py`).

use crate::error::{AssayError, AssayResult};
use crate::import::RawAssay;
use regex::Regex;

pub fn parse_pdf(bytes: &[u8]) -> AssayResult<RawAssay> {
    let text = pdf_extract::extract_text_from_mem(bytes)
        .map_err(|e| AssayError::Parse(format!("pdf extract: {e}")))?;
    Ok(extract_from_text(&text))
}

fn capture_first(text: &str, pattern: &str) -> Option<String> {
    Regex::new(pattern)
        .ok()?
        .captures(text)?
        .get(1)
        .map(|m| m.as_str().trim().to_string())
}

fn extract_from_text(text: &str) -> RawAssay {
    let mut raw = RawAssay::default();

    if let Some(v) = capture_first(text, r"API\s*[:\-]?\s*([0-9.]+)") {
        raw.api = v.parse().ok();
    }
    if let Some(v) = capture_first(text, r"Sulfur\s*[:\-]?\s*([0-9.]+)") {
        raw.sulfur = v.parse().ok();
    }
    if let Some(v) = capture_first(text, r"Acidity\s*[:\-]?\s*([0-9.]+)") {
        raw.acidity = v.parse().ok();
    }
    if let Some(v) = capture_first(text, r"Name\s*[:\-]?\s*([^\n]+)") {
        raw.name = Some(v);
    }
    if let Some(v) = capture_first(text, r"Source\s*[:\-]?\s*([^\n]+)") {
        raw.origin = Some(v);
    }

    raw
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_key_value_pairs_from_text() {
        let text = "Crude Assay Report\nName: West Texas Intermediate\nAPI: 39.6\nSulfur: 0.24\nAcidity: 0.05";
        let raw = extract_from_text(text);
        assert_eq!(raw.name.as_deref(), Some("West Texas Intermediate"));
        assert!((raw.api.unwrap() - 39.6).abs() < 1e-9);
        assert!((raw.sulfur.unwrap() - 0.24).abs() < 1e-9);
    }
}
