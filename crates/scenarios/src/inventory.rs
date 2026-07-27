use crate::error::{ScenarioError, ScenarioResult};
use crude_domain::{GradeSlate, LeadTimes, MonthlyPrices, SiteLimits};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct InventoryScenario {
    pub name: String,
    pub start_year: u32,
    pub start_month: u32,
    pub months: usize,
    pub site_limits: SiteLimits,
    pub lead_times: LeadTimes,
    pub initial_inventory: HashMap<String, f64>,
    pub slate: GradeSlate,
    pub monthly_prices: Vec<MonthlyPrices>,
}

impl InventoryScenario {
    pub fn from_yaml_file(path: &Path) -> ScenarioResult<Self> {
        let text = fs::read_to_string(path)?;
        Self::from_yaml_str(&text)
    }

    pub fn from_yaml_str(text: &str) -> ScenarioResult<Self> {
        let scenario: InventoryScenario =
            serde_yaml::from_str(text).map_err(|e| ScenarioError::Parse(e.to_string()))?;
        scenario.validate()?;
        Ok(scenario)
    }

    pub fn validate(&self) -> ScenarioResult<()> {
        self.slate.validate().map_err(ScenarioError::Validation)?;

        if self.months == 0 {
            return Err(ScenarioError::Validation("months must be positive".into()));
        }
        if self.monthly_prices.len() < self.months {
            return Err(ScenarioError::Validation(format!(
                "need at least {} monthly price rows (got {})",
                self.months,
                self.monthly_prices.len()
            )));
        }
        for grade in crude_domain::GRADES {
            if !self.initial_inventory.contains_key(grade) {
                return Err(ScenarioError::Validation(format!(
                    "missing initial inventory for grade: {grade}"
                )));
            }
        }
        Ok(())
    }

    pub fn days_in_month(&self, month_index: usize) -> u32 {
        crate::horizon::days_in_month(self.start_year, self.start_month, month_index)
    }
}
