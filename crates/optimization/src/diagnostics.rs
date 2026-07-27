//! Pre-solve infeasibility hints for optimization scenarios.

use crude_scenarios::{BlendScheduleScenario, InventoryScenario};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct InfeasibilityHint {
    pub code: String,
    pub message: String,
}

pub fn preflight_blend_schedule(scenario: &BlendScheduleScenario) -> Vec<InfeasibilityHint> {
    bound_inversion_hints(&scenario.site_limits, scenario.months, |m| scenario.days_in_month(m))
}

pub fn diagnose_blend_schedule(scenario: &BlendScheduleScenario) -> Vec<InfeasibilityHint> {
    let mut hints = preflight_blend_schedule(scenario);
    let limits = &scenario.site_limits;

    for m in 0..scenario.months {
        let days = scenario.days_in_month(m) as f64;

        for candidate in &scenario.candidates {
            let pct = candidate.target_percentage / 100.0;
            let min_charge = limits.charge_min * days * pct;
            let max_charge = limits.charge_max * days * pct;
            if min_charge > max_charge + 1e-6 {
                hints.push(hint(
                    "monthly_charge",
                    format!(
                        "month {m} candidate {}: min charge {min_charge:.0} exceeds max {max_charge:.0}",
                        candidate.name
                    ),
                ));
            }
            let inv_ub = limits.tank_cap * 0.5;
            if min_charge > inv_ub + 1e-6 {
                hints.push(hint(
                    "charge_vs_tank",
                    format!(
                        "month {m} candidate {}: minimum charge {min_charge:.0} exceeds per-assay tank bound {inv_ub:.0}",
                        candidate.name
                    ),
                ));
            }
        }
    }

    hints
}

pub fn preflight_inventory(scenario: &InventoryScenario) -> Vec<InfeasibilityHint> {
    bound_inversion_hints(&scenario.site_limits, scenario.months, |m| scenario.days_in_month(m))
}

pub fn diagnose_inventory(scenario: &InventoryScenario) -> Vec<InfeasibilityHint> {
    preflight_inventory(scenario)
}

fn bound_inversion_hints(
    limits: &crude_domain::SiteLimits,
    months: usize,
    days_in_month: impl Fn(usize) -> u32,
) -> Vec<InfeasibilityHint> {
    let mut hints = Vec::new();

    if limits.receive_min > limits.receive_max {
        hints.push(hint(
            "receive_bounds",
            "receive_min exceeds receive_max",
        ));
    }
    if limits.charge_min > limits.charge_max {
        hints.push(hint(
            "charge_bounds",
            "charge_min exceeds charge_max",
        ));
    }
    if limits.tank_floor > limits.tank_cap {
        hints.push(hint(
            "tank_bounds",
            "tank_floor exceeds tank_cap",
        ));
    }

    for m in 0..months {
        let days = days_in_month(m) as f64;
        let min_recv = limits.receive_min * days;
        let max_recv = limits.receive_max * days;
        if min_recv > max_recv + 1e-6 {
            hints.push(hint(
                "monthly_receipt",
                format!("month {m}: min receipt {min_recv:.0} exceeds max {max_recv:.0}"),
            ));
        }
    }

    hints
}

pub fn solver_failure(
    solver_message: &str,
    hints: Vec<InfeasibilityHint>,
) -> crate::error::OptimizationError {
    use crate::error::OptimizationError;
    if hints.is_empty() {
        return OptimizationError::Solver(solver_message.to_string());
    }
    let detail: Vec<String> = hints
        .iter()
        .map(|h| format!("[{}] {}", h.code, h.message))
        .collect();
    OptimizationError::Infeasible(format!(
        "{solver_message}\nhints:\n{}",
        detail.join("\n")
    ))
}

fn hint(code: &str, message: impl Into<String>) -> InfeasibilityHint {
    InfeasibilityHint {
        code: code.to_string(),
        message: message.into(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crude_domain::{GradeSlate, LeadTimes, MonthlyPrices, SiteLimits};
    use std::collections::HashMap;

    #[test]
    fn detects_receive_min_gt_max() {
        let scenario = InventoryScenario {
            name: "bad".into(),
            start_year: 2025,
            start_month: 1,
            months: 1,
            site_limits: SiteLimits {
                receive_min: 200.0,
                receive_max: 100.0,
                charge_min: 10.0,
                charge_max: 100.0,
                tank_cap: 10_000.0,
                tank_floor: 100.0,
            },
            lead_times: LeadTimes {
                foreign_m: 2,
                canada_m: 1,
                domestic_m: 1,
            },
            initial_inventory: HashMap::from([
                ("light".into(), 1000.0),
                ("medium".into(), 1000.0),
                ("heavy".into(), 1000.0),
            ]),
            slate: GradeSlate {
                light: 40.0,
                medium: 35.0,
                heavy: 25.0,
            },
            monthly_prices: vec![MonthlyPrices {
                brent: 80.0,
                wti: 75.0,
            }],
        };
        let hints = diagnose_inventory(&scenario);
        assert!(hints.iter().any(|h| h.code == "receive_bounds"));
    }
}
