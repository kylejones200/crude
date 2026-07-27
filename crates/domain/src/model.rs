use crate::ids::CrudeId;
use crate::property::{PropertyId, PropertyMeasurement};
use crate::{DomainError, DomainResult};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Crude {
    pub id: CrudeId,
    pub name: String,
    pub origin: Option<String>,
    pub assay: Assay,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct Assay {
    pub bulk_properties: Vec<PropertyMeasurement>,
    pub cuts: Vec<AssayCut>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AssayCut {
    pub name: String,
    pub ibp_c: Option<f64>,
    pub fbp_c: Option<f64>,
    pub yield_wt_pct: Option<f64>,
    pub properties: Vec<PropertyMeasurement>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendRecipe {
    pub components: Vec<BlendComponent>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendComponent {
    pub crude_id: CrudeId,
    pub fraction: f64,
}

impl Assay {
    pub fn get(&self, property: PropertyId) -> Option<f64> {
        self.bulk_properties
            .iter()
            .find(|m| m.property == property)
            .map(|m| m.value)
    }

    pub fn api_gravity(&self) -> Option<f64> {
        self.get(PropertyId::ApiGravity)
    }

    pub fn sulfur_wt_pct(&self) -> Option<f64> {
        self.get(PropertyId::SulfurWtPct)
    }
}

impl BlendRecipe {
    pub fn validate(&self) -> DomainResult<()> {
        if self.components.is_empty() {
            return Err(DomainError::Validation(
                "blend must have at least one component".into(),
            ));
        }
        let sum: f64 = self.components.iter().map(|c| c.fraction).sum();
        if (sum - 1.0).abs() > 1e-6 {
            return Err(DomainError::InvalidFractionSum(sum));
        }
        Ok(())
    }
}
