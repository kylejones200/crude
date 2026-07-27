use crate::units::Unit;
use serde::{Deserialize, Serialize};

/// Canonical property identifiers used across assay, blending, and constraints.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PropertyId {
    ApiGravity,
    SulfurWtPct,
    TotalAcidNumber,
    PourPoint,
    Sbn,
    InsolubilityNumber,
}

impl PropertyId {
    pub fn default_unit(&self) -> Unit {
        match self {
            Self::ApiGravity => Unit::DegApi,
            Self::SulfurWtPct => Unit::WtPct,
            Self::TotalAcidNumber => Unit::MgKohPerG,
            Self::PourPoint => Unit::DegApi,
            Self::Sbn | Self::InsolubilityNumber => Unit::Dimensionless,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::ApiGravity => "api_gravity",
            Self::SulfurWtPct => "sulfur_wt_pct",
            Self::TotalAcidNumber => "total_acid_number",
            Self::PourPoint => "pour_point",
            Self::Sbn => "sbn",
            Self::InsolubilityNumber => "insolubility_number",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PropertyMeasurement {
    pub property: PropertyId,
    pub value: f64,
    pub unit: Unit,
}

impl PropertyMeasurement {
    pub fn new(property: PropertyId, value: f64) -> Self {
        let unit = property.default_unit();
        Self {
            property,
            value,
            unit,
        }
    }
}

/// Typed property value after normalization (always in canonical units).
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub struct PropertyValue {
    pub property: PropertyId,
    pub value: f64,
}
