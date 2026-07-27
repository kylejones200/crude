use crate::error::{AssayError, AssayResult};
use crate::import::RawAssay;
use crude_domain::{Crude, CrudeId, PropertyId, PropertyMeasurement};

/// Validation bounds ported from crude-assay `assay_parser._validate_assay_data`.
const API_MIN: f64 = 10.0;
const API_MAX: f64 = 50.0;
const SULFUR_MIN: f64 = 0.0;
const SULFUR_MAX: f64 = 10.0;

pub fn normalize_raw_assay(raw: RawAssay) -> AssayResult<Crude> {
    let name = raw
        .name
        .clone()
        .or(raw.id.clone())
        .ok_or_else(|| AssayError::Validation("missing assay name".into()))?;

    let id = CrudeId::new(raw.id.clone().unwrap_or_else(|| slugify(&name)));

    let api = raw
        .api
        .ok_or_else(|| AssayError::Validation("required field missing: api gravity".into()))?;
    validate_api(api)?;

    let sulfur = raw
        .sulfur
        .ok_or_else(|| AssayError::Validation("required field missing: sulfur".into()))?;
    validate_sulfur(sulfur)?;

    if let Some(acidity) = raw.acidity {
        if acidity < 0.0 {
            return Err(AssayError::Validation(
                "acidity must be non-negative".into(),
            ));
        }
    }

    let mut bulk_properties = vec![
        PropertyMeasurement::new(PropertyId::ApiGravity, api),
        PropertyMeasurement::new(PropertyId::SulfurWtPct, sulfur),
    ];

    if let Some(acidity) = raw.acidity {
        bulk_properties.push(PropertyMeasurement::new(
            PropertyId::TotalAcidNumber,
            acidity,
        ));
    }
    if let Some(sbn) = raw.sbn {
        bulk_properties.push(PropertyMeasurement::new(PropertyId::Sbn, sbn));
    }
    if let Some(in_) = raw.insolubility_number {
        bulk_properties.push(PropertyMeasurement::new(
            PropertyId::InsolubilityNumber,
            in_,
        ));
    }

    let origin = raw.origin.or(raw.source);

    Ok(Crude {
        id,
        name,
        origin,
        assay: crude_domain::Assay {
            bulk_properties,
            cuts: vec![],
        },
    })
}

fn validate_api(api: f64) -> AssayResult<()> {
    if !(API_MIN..=API_MAX).contains(&api) {
        return Err(AssayError::Validation(format!(
            "API gravity must be between {API_MIN} and {API_MAX} degrees"
        )));
    }
    Ok(())
}

fn validate_sulfur(sulfur: f64) -> AssayResult<()> {
    if !(SULFUR_MIN..=SULFUR_MAX).contains(&sulfur) {
        return Err(AssayError::Validation(format!(
            "sulfur content must be between {SULFUR_MIN} and {SULFUR_MAX}%"
        )));
    }
    Ok(())
}

fn slugify(name: &str) -> String {
    name.to_lowercase()
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '_' })
        .collect::<String>()
        .split('_')
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("_")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_legacy_aliases() {
        let raw = RawAssay {
            name: Some("West Texas Intermediate".into()),
            api: Some(39.6),
            sulfur: Some(0.24),
            acidity: Some(0.1),
            ..Default::default()
        };
        let crude = normalize_raw_assay(raw).unwrap();
        assert_eq!(crude.assay.api_gravity(), Some(39.6));
        assert_eq!(crude.assay.sulfur_wt_pct(), Some(0.24));
    }
}
