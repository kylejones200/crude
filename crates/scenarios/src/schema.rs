use crate::error::{ScenarioError, ScenarioResult};
use crude_domain::{BlendComponent, BlendRecipe, Crude, CrudeId};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Canonical scenario contract (YAML).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Scenario {
    pub name: String,
    pub available_crudes: Vec<AvailableCrude>,
    pub products: Vec<ProductSpec>,
    pub objective: Objective,
    #[serde(default)]
    pub target_volume_bbl: Option<f64>,
    #[serde(default)]
    pub crudes: HashMap<String, CrudeAssayRef>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct CrudeAssayRef {
    pub api_gravity: f64,
    pub sulfur_wt_pct: f64,
    #[serde(default)]
    pub total_acid_number: Option<f64>,
    #[serde(default)]
    pub sbn: Option<f64>,
    #[serde(default)]
    pub insolubility_number: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AvailableCrude {
    pub crude: String,
    pub min_volume: f64,
    pub max_volume: f64,
    pub price_per_bbl: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ProductSpec {
    pub name: String,
    pub constraints: ProductConstraint,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct ProductConstraint {
    #[serde(default)]
    pub api_gravity: Option<PropertyConstraint>,
    #[serde(default)]
    pub sulfur_wt_pct: Option<PropertyConstraint>,
    #[serde(default)]
    pub total_acid_number: Option<PropertyConstraint>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PropertyConstraint {
    pub min: Option<f64>,
    pub max: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Objective {
    #[serde(rename = "type")]
    pub objective_type: ObjectiveType,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ObjectiveType {
    MinimizeFeedCost,
}

/// Blend recipe file for `crude blend evaluate`.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendScenarioFile {
    pub name: Option<String>,
    pub total_volume_bbl: Option<f64>,
    pub components: Vec<BlendComponentYaml>,
    #[serde(default)]
    pub crudes: HashMap<String, CrudeAssayRef>,
    #[serde(default)]
    pub prices_usd_per_bbl: HashMap<String, f64>,
    #[serde(default)]
    pub constraints: Option<ProductConstraint>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendComponentYaml {
    pub crude: String,
    pub fraction: f64,
}

impl Scenario {
    pub fn from_yaml_file(path: &Path) -> ScenarioResult<Self> {
        let text = fs::read_to_string(path)?;
        Self::from_yaml_str(&text)
    }

    pub fn from_yaml_str(text: &str) -> ScenarioResult<Self> {
        let scenario: Scenario =
            serde_yaml::from_str(text).map_err(|e| ScenarioError::Parse(e.to_string()))?;
        scenario.validate()?;
        Ok(scenario)
    }

    pub fn validate(&self) -> ScenarioResult<()> {
        if self.available_crudes.is_empty() {
            return Err(ScenarioError::Validation(
                "scenario must list at least one available crude".into(),
            ));
        }
        if self.products.is_empty() {
            return Err(ScenarioError::Validation(
                "scenario must define at least one product".into(),
            ));
        }
        for ac in &self.available_crudes {
            if ac.min_volume > ac.max_volume {
                return Err(ScenarioError::Validation(format!(
                    "crude {}: min_volume exceeds max_volume",
                    ac.crude
                )));
            }
            if ac.price_per_bbl < 0.0 {
                return Err(ScenarioError::Validation(format!(
                    "crude {}: negative price",
                    ac.crude
                )));
            }
            if !self.crudes.contains_key(&ac.crude) {
                return Err(ScenarioError::Validation(format!(
                    "crude {} listed in available_crudes but missing from crudes assay table",
                    ac.crude
                )));
            }
        }
        Ok(())
    }

    pub fn build_crude_library(&self) -> HashMap<CrudeId, Crude> {
        let mut library = HashMap::new();

        for ac in &self.available_crudes {
            let assay_ref = self
                .crudes
                .get(&ac.crude)
                .expect("validated in Scenario::validate");
            let api = assay_ref.api_gravity;
            let sulfur = assay_ref.sulfur_wt_pct;

            let id = CrudeId::new(&ac.crude);
            let mut bulk = vec![
                crude_domain::PropertyMeasurement::new(crude_domain::PropertyId::ApiGravity, api),
                crude_domain::PropertyMeasurement::new(
                    crude_domain::PropertyId::SulfurWtPct,
                    sulfur,
                ),
            ];
            if let Some(tan) = assay_ref.total_acid_number {
                bulk.push(crude_domain::PropertyMeasurement::new(
                    crude_domain::PropertyId::TotalAcidNumber,
                    tan,
                ));
            }
            if let Some(sbn) = assay_ref.sbn {
                bulk.push(crude_domain::PropertyMeasurement::new(
                    crude_domain::PropertyId::Sbn,
                    sbn,
                ));
            }
            if let Some(in_) = assay_ref.insolubility_number {
                bulk.push(crude_domain::PropertyMeasurement::new(
                    crude_domain::PropertyId::InsolubilityNumber,
                    in_,
                ));
            }

            library.insert(
                id.clone(),
                Crude {
                    id,
                    name: ac.crude.clone(),
                    origin: None,
                    assay: crude_domain::Assay {
                        bulk_properties: bulk,
                        cuts: vec![],
                    },
                },
            );
        }
        library
    }

    pub fn price_map(&self) -> HashMap<CrudeId, f64> {
        self.available_crudes
            .iter()
            .map(|ac| (CrudeId::new(&ac.crude), ac.price_per_bbl))
            .collect()
    }
}

impl BlendScenarioFile {
    pub fn from_yaml_file(path: &Path) -> ScenarioResult<Self> {
        let text = fs::read_to_string(path)?;
        Self::from_yaml_str(&text)
    }

    pub fn from_yaml_str(text: &str) -> ScenarioResult<Self> {
        serde_yaml::from_str(text).map_err(|e| ScenarioError::Parse(e.to_string()))
    }

    pub fn to_blend_recipe(&self) -> BlendRecipe {
        BlendRecipe {
            components: self
                .components
                .iter()
                .map(|c| BlendComponent {
                    crude_id: CrudeId::new(&c.crude),
                    fraction: c.fraction,
                })
                .collect(),
        }
    }

    pub fn build_crude_library(&self) -> HashMap<CrudeId, Crude> {
        let mut library = HashMap::new();
        for (name, assay_ref) in &self.crudes {
            let id = CrudeId::new(name);
            let mut bulk = vec![
                crude_domain::PropertyMeasurement::new(
                    crude_domain::PropertyId::ApiGravity,
                    assay_ref.api_gravity,
                ),
                crude_domain::PropertyMeasurement::new(
                    crude_domain::PropertyId::SulfurWtPct,
                    assay_ref.sulfur_wt_pct,
                ),
            ];
            if let Some(tan) = assay_ref.total_acid_number {
                bulk.push(crude_domain::PropertyMeasurement::new(
                    crude_domain::PropertyId::TotalAcidNumber,
                    tan,
                ));
            }
            library.insert(
                id.clone(),
                Crude {
                    id,
                    name: name.clone(),
                    origin: None,
                    assay: crude_domain::Assay {
                        bulk_properties: bulk,
                        cuts: vec![],
                    },
                },
            );
        }
        library
    }

    pub fn price_map(&self) -> HashMap<CrudeId, f64> {
        self.prices_usd_per_bbl
            .iter()
            .map(|(k, v)| (CrudeId::new(k), *v))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_requires_crude_assay_entries() {
        let scenario = Scenario {
            name: "bad".into(),
            available_crudes: vec![AvailableCrude {
                crude: "wti".into(),
                min_volume: 0.0,
                max_volume: 1000.0,
                price_per_bbl: 70.0,
            }],
            products: vec![ProductSpec {
                name: "blend".into(),
                constraints: ProductConstraint::default(),
            }],
            objective: Objective {
                objective_type: ObjectiveType::MinimizeFeedCost,
            },
            target_volume_bbl: Some(1000.0),
            crudes: HashMap::new(),
        };
        assert!(scenario.validate().is_err());
    }
}
