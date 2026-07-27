//! PDF and plain-text assay extraction (key-value lines and tabular rows).

use crate::error::{AssayError, AssayResult};
use crate::import::RawAssay;
use regex::Regex;

pub fn parse_pdf(bytes: &[u8]) -> AssayResult<RawAssay> {
    let text = pdf_extract::extract_text_from_mem(bytes)
        .map_err(|e| AssayError::Parse(format!("pdf extract: {e}")))?;
    Ok(parse_assay_text(&text))
}

/// Parse assay properties from extracted PDF text or plain-text assay reports.
pub fn parse_assay_text(text: &str) -> RawAssay {
    let mut raw = extract_key_values(text);
    merge_table_rows(text, &mut raw);
    raw
}

fn capture_first(text: &str, pattern: &str) -> Option<String> {
    Regex::new(pattern)
        .ok()?
        .captures(text)?
        .get(1)
        .map(|m| m.as_str().trim().to_string())
}

fn extract_key_values(text: &str) -> RawAssay {
    let mut raw = RawAssay::default();

    if let Some(v) = capture_first(text, r"(?i)API\s*(?:gravity)?\s*[:\-]?\s*([0-9.]+)") {
        raw.api = v.parse().ok();
    }
    if let Some(v) = capture_first(text, r"(?i)Sulfur\s*(?:content|wt%)?\s*[:\-]?\s*([0-9.]+)") {
        raw.sulfur = v.parse().ok();
    }
    if let Some(v) = capture_first(
        text,
        r"(?i)(?:Acidity|TAN|Total Acid Number)\s*[:\-]?\s*([0-9.]+)",
    ) {
        raw.acidity = v.parse().ok();
    }
    if let Some(v) = capture_first(text, r"(?i)Name\s*[:\-]?\s*([^\n]+)") {
        raw.name = Some(v);
    }
    if let Some(v) = capture_first(text, r"(?i)(?:Source|Origin)\s*[:\-]?\s*([^\n]+)") {
        raw.origin = Some(v);
    }
    if let Some(v) = capture_first(text, r"(?i)SBN\s*[:\-]?\s*([0-9.]+)") {
        raw.sbn = v.parse().ok();
    }
    if let Some(v) = capture_first(text, r"(?i)(?:IN|Insolubility Number)\s*[:\-]?\s*([0-9.]+)") {
        raw.insolubility_number = v.parse().ok();
    }

    raw
}

fn merge_table_rows(text: &str, raw: &mut RawAssay) {
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }

        let cols: Vec<&str> = if line.contains('\t') {
            line.split('\t')
                .map(str::trim)
                .filter(|c| !c.is_empty())
                .collect()
        } else if line.contains('|') {
            line.split('|')
                .map(str::trim)
                .filter(|c| !c.is_empty())
                .collect()
        } else {
            split_columns(line)
        };

        if cols.len() < 2 {
            continue;
        }

        let key = cols[0].to_lowercase();
        let value = cols[1];
        apply_table_field(raw, &key, value);
    }
}

fn split_columns(line: &str) -> Vec<&str> {
    line.split_whitespace().collect()
}

fn apply_table_field(raw: &mut RawAssay, key: &str, value: &str) {
    let numeric = parse_numeric(value);
    if key.contains("property") || key == "parameter" || key == "field" {
        return;
    }
    if key.contains("name") || key.contains("crude") || key.contains("grade") {
        if raw.name.is_none() {
            raw.name = Some(value.to_string());
        }
    } else if key.contains("api") {
        raw.api = raw.api.or(numeric);
    } else if key.contains("sulfur") {
        raw.sulfur = raw.sulfur.or(numeric);
    } else if key.contains("acidity") || key.contains("tan") {
        raw.acidity = raw.acidity.or(numeric);
    } else if key.contains("source") || key.contains("origin") {
        if raw.origin.is_none() {
            raw.origin = Some(value.to_string());
        }
    } else if key.contains("sbn") {
        raw.sbn = raw.sbn.or(numeric);
    } else if key == "in" || key.contains("insolubility") {
        raw.insolubility_number = raw.insolubility_number.or(numeric);
    }
}

fn parse_numeric(token: &str) -> Option<f64> {
    token
        .trim()
        .trim_end_matches(|c: char| !c.is_ascii_digit() && c != '.')
        .parse()
        .ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::report::import_assay_report_bytes;

    #[test]
    fn extracts_key_value_pairs_from_text() {
        let text = "Crude Assay Report\nName: West Texas Intermediate\nAPI: 39.6\nSulfur: 0.24\nAcidity: 0.05";
        let raw = parse_assay_text(text);
        assert_eq!(raw.name.as_deref(), Some("West Texas Intermediate"));
        assert!((raw.api.unwrap() - 39.6).abs() < 1e-9);
        assert!((raw.sulfur.unwrap() - 0.24).abs() < 1e-9);
    }

    #[test]
    fn parses_tabular_assay_rows() {
        let text = "Property\tValue\tUnit\nAPI Gravity\t39.6\tdeg API\nSulfur\t0.24\twt%\nTAN\t0.10\tmg KOH/g";
        let raw = parse_assay_text(text);
        assert!((raw.api.unwrap() - 39.6).abs() < 1e-9);
        assert!((raw.sulfur.unwrap() - 0.24).abs() < 1e-9);
        assert!((raw.acidity.unwrap() - 0.10).abs() < 1e-9);
    }

    #[test]
    fn table_fixture_imports_with_warnings() {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../fixtures/assays/wti-assay-table.txt");
        let bytes = std::fs::read(&path).unwrap();
        let report = import_assay_report_bytes(&bytes, "txt").unwrap();
        assert_eq!(report.crude.assay.api_gravity(), Some(39.6));
        assert!(report.warnings.iter().any(|w| w.code == "missing_sbn"));
    }
}
