//! Constraint evaluation: product specifications and SBN/IN compatibility.

use crude_blending::BlendEvaluation;
use crude_domain::PropertyId;
use serde::{Deserialize, Serialize};

/// Default safety factor from crude-assay `compatibility_service.blend_compatibility`.
pub const DEFAULT_COMPATIBILITY_K: f64 = 1.2;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PropertyBound {
    pub min: Option<f64>,
    pub max: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ProductConstraints {
    pub api_gravity: Option<PropertyBound>,
    pub sulfur_wt_pct: Option<PropertyBound>,
    pub total_acid_number: Option<PropertyBound>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ConstraintViolation {
    pub property: String,
    pub actual: f64,
    pub bound: String,
    pub message: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ConstraintReport {
    pub satisfied: bool,
    pub violations: Vec<ConstraintViolation>,
}

pub fn evaluate_product_constraints(
    blend: &BlendEvaluation,
    constraints: &ProductConstraints,
) -> ConstraintReport {
    let mut violations = Vec::new();

    check_bound(
        &mut violations,
        "api_gravity",
        constraints.api_gravity.as_ref(),
        blend_property(blend, PropertyId::ApiGravity),
    );
    check_bound(
        &mut violations,
        "sulfur_wt_pct",
        constraints.sulfur_wt_pct.as_ref(),
        blend_property(blend, PropertyId::SulfurWtPct),
    );
    check_bound(
        &mut violations,
        "total_acid_number",
        constraints.total_acid_number.as_ref(),
        blend_property(blend, PropertyId::TotalAcidNumber),
    );

    ConstraintReport {
        satisfied: violations.is_empty(),
        violations,
    }
}

fn blend_property(blend: &BlendEvaluation, property: PropertyId) -> Option<f64> {
    blend
        .properties
        .properties
        .iter()
        .find(|p| p.property == property)
        .map(|p| p.value)
}

fn check_bound(
    violations: &mut Vec<ConstraintViolation>,
    name: &str,
    bound: Option<&PropertyBound>,
    actual: Option<f64>,
) {
    let Some(bound) = bound else { return };
    let Some(actual) = actual else {
        violations.push(ConstraintViolation {
            property: name.to_string(),
            actual: f64::NAN,
            bound: "required".into(),
            message: format!("property {name} not available in blend"),
        });
        return;
    };

    if let Some(min) = bound.min {
        if actual < min {
            violations.push(ConstraintViolation {
                property: name.to_string(),
                actual,
                bound: format!("min {min}"),
                message: format!("{name} {actual} below minimum {min}"),
            });
        }
    }
    if let Some(max) = bound.max {
        if actual > max {
            violations.push(ConstraintViolation {
                property: name.to_string(),
                actual,
                bound: format!("max {max}"),
                message: format!("{name} {actual} above maximum {max}"),
            });
        }
    }
}

/// SBN/IN solvency margin model from crude-assay compatibility_service.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct CompatibilityResult {
    pub sbn_blend: f64,
    pub in_max: f64,
    pub r: f64,
    pub compatible: bool,
    pub reserve: f64,
    pub band: String,
    pub band_label: String,
}

pub fn evaluate_compatibility(
    sbn_values: &[f64],
    in_values: &[f64],
    fractions: &[f64],
    k: f64,
) -> CompatibilityResult {
    if sbn_values.len() != fractions.len() || in_values.len() != fractions.len() {
        return CompatibilityResult {
            sbn_blend: 0.0,
            in_max: 0.0,
            r: 0.0,
            compatible: false,
            reserve: 0.0,
            band: "incompatible".into(),
            band_label: "Invalid input".into(),
        };
    }

    let sbn_blend: f64 = fractions
        .iter()
        .zip(sbn_values.iter())
        .map(|(f, s)| f * s)
        .sum();

    let in_max = fractions
        .iter()
        .zip(in_values.iter())
        .filter(|(f, _)| **f > 0.0)
        .map(|(_, in_)| *in_)
        .fold(0.0_f64, f64::max);

    let r = if in_max > 0.0 {
        sbn_blend / in_max
    } else {
        0.0
    };
    let reserve = sbn_blend - k * in_max;
    let compatible = sbn_blend >= k * in_max;
    let (band, band_label) = compatibility_band_from_r(r);

    CompatibilityResult {
        sbn_blend,
        in_max,
        r,
        compatible,
        reserve,
        band: band.to_string(),
        band_label: band_label.to_string(),
    }
}

pub fn compatibility_band_from_r(r: f64) -> (&'static str, &'static str) {
    if r >= 1.5 {
        ("compatible", "Compatible — Low risk")
    } else if r >= 1.2 {
        ("possibly_compatible", "Possibly compatible — Monitor")
    } else {
        ("incompatible", "Incompatible — High risk")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sbn_in_compatibility() {
        let result = evaluate_compatibility(&[50.0, 30.0], &[20.0, 40.0], &[0.6, 0.4], 1.2);
        assert!(result.sbn_blend > 0.0);
        assert_eq!(result.in_max, 40.0);
    }
}
