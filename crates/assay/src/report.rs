//! Assay import with structured validation report.

use crate::error::{AssayError, AssayResult};
use crate::import::{parse_raw_assay_bytes, RawAssay};
use crate::normalize::build_crude_from_raw;
use crate::validation::{has_errors, validate_raw_assay, AssayImportReport, AssayIssue};
use std::fs;
use std::path::Path;

pub fn import_assay_report(path: &Path) -> AssayResult<AssayImportReport> {
    let bytes = fs::read(path)?;
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase();
    import_assay_report_bytes(&bytes, &ext)
}

pub fn import_assay_report_bytes(bytes: &[u8], extension: &str) -> AssayResult<AssayImportReport> {
    let raw = parse_raw_assay_bytes(bytes, extension)?;
    build_report(raw)
}

fn build_report(raw: RawAssay) -> AssayResult<AssayImportReport> {
    let issues = validate_raw_assay(&raw);
    if has_errors(&issues) {
        return Err(AssayError::Validation(format_issues(&issues)));
    }
    let crude = build_crude_from_raw(raw)?;
    let warnings: Vec<AssayIssue> = issues
        .into_iter()
        .filter(|i| i.severity == crate::validation::AssayIssueSeverity::Warning)
        .collect();
    Ok(AssayImportReport { crude, warnings })
}

fn format_issues(issues: &[AssayIssue]) -> String {
    issues
        .iter()
        .filter(|i| i.severity == crate::validation::AssayIssueSeverity::Error)
        .map(|i| format!("[{}] {}", i.code, i.message))
        .collect::<Vec<_>>()
        .join("; ")
}
