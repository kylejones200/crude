use serde::{Deserialize, Serialize};

pub const GRADES: [&str; 3] = ["light", "medium", "heavy"];
pub const SOURCES: [&str; 3] = ["foreign", "canada", "domestic"];

/// Unmet demand penalty ($/bbl) from crude-assay `inventory_optimization.py`.
pub const UNMET_DEMAND_PENALTY_USD_PER_BBL: f64 = 1000.0;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SiteLimits {
    pub receive_min: f64,
    pub receive_max: f64,
    pub charge_min: f64,
    pub charge_max: f64,
    pub tank_cap: f64,
    pub tank_floor: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LeadTimes {
    pub foreign_m: u32,
    pub canada_m: u32,
    pub domestic_m: u32,
}

impl LeadTimes {
    pub fn for_source(&self, source: &str) -> u32 {
        match source {
            "foreign" => self.foreign_m,
            "canada" => self.canada_m,
            "domestic" => self.domestic_m,
            _ => 0,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct GradeSlate {
    pub light: f64,
    pub medium: f64,
    pub heavy: f64,
}

impl GradeSlate {
    pub fn fraction(&self, grade: &str) -> f64 {
        match grade {
            "light" => self.light / 100.0,
            "medium" => self.medium / 100.0,
            "heavy" => self.heavy / 100.0,
            _ => 0.0,
        }
    }

    pub fn validate(&self) -> Result<(), String> {
        let sum = self.light + self.medium + self.heavy;
        if (sum - 100.0).abs() > 1e-6 {
            return Err(format!("slate must sum to 100% (got {sum}%)"));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MonthlyPrices {
    pub brent: f64,
    pub wti: f64,
}

impl MonthlyPrices {
    pub fn price_for_source(&self, source: &str) -> f64 {
        match source {
            "foreign" => self.brent,
            "canada" | "domestic" => self.wti,
            _ => self.wti,
        }
    }
}
