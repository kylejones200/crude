use crate::error::{ScenarioError, ScenarioResult};
use crude_domain::{LeadTimes, MonthlyPrices, SiteLimits};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendComponentSpec {
    pub assay_name: String,
    pub api_gravity: f64,
    pub sulfur_content: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendCandidateSpec {
    pub name: String,
    #[serde(default = "default_target_pct")]
    pub target_percentage: f64,
    pub components: Vec<BlendComponentSpec>,
    pub min_api_gravity: Option<f64>,
    pub max_sulfur_content: Option<f64>,
}

fn default_target_pct() -> f64 {
    100.0
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AssayStreamSpec {
    pub name: String,
    #[serde(default)]
    pub price_per_barrel: Option<f64>,
    #[serde(default = "default_domestic")]
    pub source: String,
}

fn default_domestic() -> String {
    "domestic".into()
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendScheduleScenario {
    pub name: String,
    pub start_year: u32,
    pub start_month: u32,
    pub months: usize,
    pub assays: Vec<AssayStreamSpec>,
    pub candidates: Vec<BlendCandidateSpec>,
    pub target_specs: HashMap<String, f64>,
    pub initial_inventory: HashMap<String, f64>,
    pub site_limits: SiteLimits,
    pub lead_times: LeadTimes,
    pub monthly_prices: Vec<MonthlyPrices>,
}

impl BlendScheduleScenario {
    pub fn from_yaml_file(path: &Path) -> ScenarioResult<Self> {
        let text = fs::read_to_string(path)?;
        Self::from_yaml_str(&text)
    }

    pub fn from_yaml_str(text: &str) -> ScenarioResult<Self> {
        let scenario: BlendScheduleScenario =
            serde_yaml::from_str(text).map_err(|e| ScenarioError::Parse(e.to_string()))?;
        scenario.validate()?;
        Ok(scenario)
    }

    pub fn validate(&self) -> ScenarioResult<()> {
        if self.months == 0 {
            return Err(ScenarioError::Validation("months must be positive".into()));
        }
        if self.assays.is_empty() {
            return Err(ScenarioError::Validation("assays required".into()));
        }
        if self.candidates.is_empty() {
            return Err(ScenarioError::Validation("candidates required".into()));
        }
        for key in ["api_gravity", "sulfur_content", "total_acid_number"] {
            if !self.target_specs.contains_key(key) {
                return Err(ScenarioError::Validation(format!(
                    "missing target spec: {key}"
                )));
            }
        }
        for assay in &self.assays {
            if !self.initial_inventory.contains_key(&assay.name) {
                return Err(ScenarioError::Validation(format!(
                    "missing initial inventory for {}",
                    assay.name
                )));
            }
        }
        if self.monthly_prices.len() < self.months {
            return Err(ScenarioError::Validation(format!(
                "need {} monthly price rows",
                self.months
            )));
        }
        Ok(())
    }

    pub fn days_in_month(&self, month_index: usize) -> u32 {
        crate::horizon::days_in_month(self.start_year, self.start_month, month_index)
    }
}
