use crate::error::{AssayError, AssayResult};
use crate::report::import_assay_report;
use crude_domain::Crude;
use std::path::Path;

/// Import an assay file (JSON, YAML, Excel, PDF) and return a normalized [`Crude`].
pub fn import_assay(path: &Path) -> AssayResult<Crude> {
    import_assay_report(path).map(|r| r.crude)
}

/// Import assay bytes with an explicit file extension (e.g. `json`, `pdf`).
pub fn import_assay_bytes(bytes: &[u8], extension: &str) -> AssayResult<Crude> {
    crate::report::import_assay_report_bytes(bytes, extension).map(|r| r.crude)
}

pub fn parse_raw_assay_bytes(bytes: &[u8], extension: &str) -> AssayResult<RawAssay> {
    let ext = extension.to_lowercase();
    match ext.as_str() {
        "json" => parse_json(bytes),
        "xlsx" | "xls" => parse_excel(bytes),
        "yaml" | "yml" => parse_yaml(bytes),
        "pdf" => crate::pdf::parse_pdf(bytes),
        "txt" => Ok(crate::pdf::parse_assay_text(
            std::str::from_utf8(bytes).map_err(|e| AssayError::Parse(e.to_string()))?,
        )),
        other => Err(AssayError::UnsupportedFormat(other.to_string())),
    }
}

fn parse_json(bytes: &[u8]) -> AssayResult<RawAssay> {
    serde_json::from_slice(bytes).map_err(|e| AssayError::Parse(e.to_string()))
}

fn parse_yaml(bytes: &[u8]) -> AssayResult<RawAssay> {
    serde_yaml::from_slice(bytes).map_err(|e| AssayError::Parse(e.to_string()))
}

fn parse_excel(bytes: &[u8]) -> AssayResult<RawAssay> {
    use calamine::{open_workbook_auto_from_rs, Reader};
    use std::io::Cursor;

    let cursor = Cursor::new(bytes);
    let mut workbook =
        open_workbook_auto_from_rs(cursor).map_err(|e| AssayError::Parse(e.to_string()))?;

    let sheet_names = workbook.sheet_names().to_vec();
    let first = sheet_names
        .first()
        .ok_or_else(|| AssayError::Parse("excel workbook has no sheets".into()))?;

    let range = workbook
        .worksheet_range(first)
        .map_err(|e| AssayError::Parse(e.to_string()))?;

    let mut raw = RawAssay::default();
    for row in range.rows() {
        if row.len() < 2 {
            continue;
        }
        let key = cell_to_string(&row[0]).to_lowercase();
        let value = &row[1];
        map_field(&mut raw, &key, value);
    }

    Ok(raw)
}

fn cell_to_string(cell: &calamine::Data) -> String {
    use calamine::Data;
    match cell {
        Data::String(s) => s.clone(),
        Data::Float(f) => f.to_string(),
        Data::Int(i) => i.to_string(),
        Data::Bool(b) => b.to_string(),
        _ => String::new(),
    }
}

fn map_field(raw: &mut RawAssay, key: &str, value: &calamine::Data) {
    use calamine::Data;
    if key.contains("name") || key.contains("crude") || key.contains("grade") {
        if let Data::String(s) = value {
            raw.name = Some(s.clone());
        }
    } else if key.contains("api") {
        raw.api = data_to_f64(value);
    } else if key.contains("sulfur") {
        raw.sulfur = data_to_f64(value);
    } else if key.contains("acidity") || key.contains("tan") {
        raw.acidity = data_to_f64(value);
    } else if key.contains("source") || key.contains("origin") {
        if let Data::String(s) = value {
            raw.origin = Some(s.clone());
        }
    } else if key.contains("sbn") {
        raw.sbn = data_to_f64(value);
    } else if key.contains("in") || key.contains("insolubility") {
        raw.insolubility_number = data_to_f64(value);
    }
}

fn data_to_f64(value: &calamine::Data) -> Option<f64> {
    use calamine::Data;
    match value {
        Data::Float(f) => Some(*f),
        Data::Int(i) => Some(*i as f64),
        Data::String(s) => parse_numeric_token(s),
        _ => None,
    }
}

fn parse_numeric_token(token: &str) -> Option<f64> {
    token
        .trim()
        .trim_end_matches(|c: char| !c.is_ascii_digit() && c != '.')
        .parse()
        .ok()
}

/// Raw parsed assay before normalization (accepts legacy field aliases).
#[derive(Debug, Default, serde::Deserialize, serde::Serialize)]
pub struct RawAssay {
    #[serde(alias = "crude_id", alias = "id")]
    pub id: Option<String>,
    pub name: Option<String>,
    pub origin: Option<String>,
    #[serde(alias = "source")]
    pub source: Option<String>,
    #[serde(alias = "api_gravity")]
    pub api: Option<f64>,
    #[serde(alias = "sulfur_wt_pct", alias = "sulfur_content")]
    pub sulfur: Option<f64>,
    #[serde(alias = "total_acid_number")]
    pub acidity: Option<f64>,
    pub sbn: Option<f64>,
    pub insolubility_number: Option<f64>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn import_still_returns_crude() {
        let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../fixtures/assays/wti.json");
        let crude = import_assay(&path).unwrap();
        assert_eq!(crude.assay.api_gravity(), Some(39.6));
    }
}
