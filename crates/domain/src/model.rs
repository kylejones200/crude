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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ids::CrudeId;

    #[test]
    fn blend_recipe_validates_fraction_sum() {
        let recipe = BlendRecipe {
            components: vec![
                BlendComponent {
                    crude_id: CrudeId::new("wti"),
                    fraction: 0.5,
                },
                BlendComponent {
                    crude_id: CrudeId::new("maya"),
                    fraction: 0.5,
                },
            ],
        };
        recipe.validate().unwrap();
    }

    #[test]
    fn blend_recipe_rejects_bad_fraction_sum() {
        let recipe = BlendRecipe {
            components: vec![BlendComponent {
                crude_id: CrudeId::new("wti"),
                fraction: 0.9,
            }],
        };
        assert!(recipe.validate().is_err());
    }

    #[test]
    fn blend_recipe_rejects_empty() {
        let recipe = BlendRecipe {
            components: vec![],
        };
        assert!(recipe.validate().is_err());
    }

    #[test]
    fn assay_reads_api_and_sulfur() {
        let assay = Assay {
            bulk_properties: vec![
                PropertyMeasurement::new(PropertyId::ApiGravity, 39.6),
                PropertyMeasurement::new(PropertyId::SulfurWtPct, 0.24),
            ],
            cuts: vec![],
        };
        assert_eq!(assay.api_gravity(), Some(39.6));
        assert_eq!(assay.sulfur_wt_pct(), Some(0.24));
    }
}
