//! Assay validation issues (warnings vs blocking errors).

use crate::import::RawAssay;
use serde::{Deserialize, Serialize};

pub const API_MIN: f64 = 10.0;
pub const API_MAX: f64 = 50.0;
pub const SULFUR_MIN: f64 = 0.0;
pub const SULFUR_MAX: f64 = 10.0;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AssayIssueSeverity {
    Warning,
    Error,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AssayIssue {
    pub code: String,
    pub message: String,
    pub severity: AssayIssueSeverity,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AssayImportReport {
    pub crude: crude_domain::Crude,
    pub warnings: Vec<AssayIssue>,
}

pub fn validate_raw_assay(raw: &RawAssay) -> Vec<AssayIssue> {
    let mut issues = Vec::new();

    if raw.name.is_none() && raw.id.is_none() {
        issues.push(error(
            "missing_name",
            "assay name or id is required; a slug will be generated from name if present",
        ));
    }

    match raw.api {
        None => issues.push(error("missing_api", "required field missing: api gravity")),
        Some(api) => {
            if !(API_MIN..=API_MAX).contains(&api) {
                issues.push(error(
                    "api_out_of_range",
                    format!("API gravity must be between {API_MIN} and {API_MAX} degrees"),
                ));
            } else if !(15.0..=45.0).contains(&api) {
                issues.push(warning(
                    "api_unusual",
                    format!("API gravity {api:.1} is outside typical crude range (15–45)"),
                ));
            }
        }
    }

    match raw.sulfur {
        None => issues.push(error(
            "missing_sulfur",
            "required field missing: sulfur (wt%)",
        )),
        Some(sulfur) => {
            if !(SULFUR_MIN..=SULFUR_MAX).contains(&sulfur) {
                issues.push(error(
                    "sulfur_out_of_range",
                    format!("sulfur content must be between {SULFUR_MIN} and {SULFUR_MAX}%"),
                ));
            } else if sulfur > 5.0 {
                issues.push(warning(
                    "sulfur_high",
                    format!("sulfur {sulfur:.2} wt% indicates very sour crude"),
                ));
            }
        }
    }

    if let Some(acidity) = raw.acidity {
        if acidity < 0.0 {
            issues.push(error("acidity_negative", "acidity must be non-negative"));
        }
    } else {
        issues.push(warning(
            "missing_acidity",
            "total acid number (TAN) not provided",
        ));
    }

    if raw.sbn.is_none() {
        issues.push(warning(
            "missing_sbn",
            "SBN not provided; compatibility checks will be incomplete",
        ));
    }
    if raw.insolubility_number.is_none() {
        issues.push(warning(
            "missing_in",
            "insolubility number (IN) not provided; compatibility checks will be incomplete",
        ));
    }
    if raw.origin.is_none() && raw.source.is_none() {
        issues.push(warning("missing_origin", "origin/source not provided"));
    }

    issues
}

pub fn has_errors(issues: &[AssayIssue]) -> bool {
    issues
        .iter()
        .any(|i| i.severity == AssayIssueSeverity::Error)
}

fn warning(code: &str, message: impl Into<String>) -> AssayIssue {
    AssayIssue {
        code: code.to_string(),
        message: message.into(),
        severity: AssayIssueSeverity::Warning,
    }
}

fn error(code: &str, message: impl Into<String>) -> AssayIssue {
    AssayIssue {
        code: code.to_string(),
        message: message.into(),
        severity: AssayIssueSeverity::Error,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::import::RawAssay;

    #[test]
    fn missing_api_is_error() {
        let raw = RawAssay {
            name: Some("X".into()),
            sulfur: Some(1.0),
            ..Default::default()
        };
        let issues = validate_raw_assay(&raw);
        assert!(issues.iter().any(|i| i.code == "missing_api"));
        assert!(has_errors(&issues));
    }

    #[test]
    fn missing_tan_is_warning_only() {
        let raw = RawAssay {
            name: Some("X".into()),
            api: Some(35.0),
            sulfur: Some(0.5),
            ..Default::default()
        };
        let issues = validate_raw_assay(&raw);
        assert!(!has_errors(&issues));
        assert!(issues.iter().any(|i| i.code == "missing_acidity"));
    }
}
