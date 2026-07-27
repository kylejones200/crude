//! Assay file import and normalization to canonical domain types.

mod error;
mod import;
mod normalize;
mod pdf;
mod report;
mod validation;

pub use error::{AssayError, AssayResult};
pub use import::{import_assay, import_assay_bytes, parse_raw_assay_bytes, RawAssay};
pub use normalize::{build_crude_from_raw, normalize_raw_assay};
pub use pdf::{parse_assay_text, parse_pdf};
pub use report::{import_assay_report, import_assay_report_bytes};
pub use validation::{validate_raw_assay, AssayImportReport, AssayIssue, AssayIssueSeverity};
