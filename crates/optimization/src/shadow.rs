//! Marginal cost estimates for binding site-limit constraints (finite-difference sensitivity).

use crate::error::OptimizationResult;
use crude_scenarios::{BlendScheduleScenario, InventoryScenario};
use serde::{Deserialize, Serialize};

/// Marginal change in objective ($) per unit relaxation of a named constraint.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ShadowPrice {
    pub name: String,
    /// USD saved per additional bbl of monthly receipt/charge capacity (or tank volume).
    pub usd_per_bbl: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub month: Option<usize>,
}

const BUMP_DAILY_BBL: f64 = 10.0;
const BUMP_TANK_BBL: f64 = 100.0;

pub fn estimate_inventory_shadow_prices(
    scenario: &InventoryScenario,
    base_objective_usd: f64,
    solve: impl Fn(&InventoryScenario) -> OptimizationResult<f64>,
) -> Vec<ShadowPrice> {
    let mut shadows = Vec::new();
    let days = scenario.days_in_month(0) as f64;
    let bump_monthly = BUMP_DAILY_BBL * days;

    if let Ok(obj) = relaxed_receive_max(scenario, &solve) {
        if let Some(sp) = shadow_from_relaxation(
            "receive_max",
            Some(0),
            base_objective_usd,
            obj,
            bump_monthly,
        ) {
            shadows.push(sp);
        }
    }

    if let Ok(obj) = relaxed_receive_min(scenario, &solve) {
        if let Some(sp) = shadow_from_relaxation(
            "receive_min",
            Some(0),
            base_objective_usd,
            obj,
            bump_monthly,
        ) {
            shadows.push(sp);
        }
    }

    if let Ok(obj) = relaxed_charge_max(scenario, &solve) {
        if let Some(sp) =
            shadow_from_relaxation("charge_max", Some(0), base_objective_usd, obj, bump_monthly)
        {
            shadows.push(sp);
        }
    }

    if let Ok(obj) = relaxed_tank_cap(scenario, &solve) {
        if let Some(sp) =
            shadow_from_relaxation("tank_cap", None, base_objective_usd, obj, BUMP_TANK_BBL)
        {
            shadows.push(sp);
        }
    }

    shadows
}

pub fn estimate_blend_schedule_shadow_prices(
    scenario: &BlendScheduleScenario,
    base_objective_usd: f64,
    solve: impl Fn(&BlendScheduleScenario) -> OptimizationResult<f64>,
) -> Vec<ShadowPrice> {
    let mut shadows = Vec::new();
    let days = scenario.days_in_month(0) as f64;
    let bump_monthly = BUMP_DAILY_BBL * days;

    if let Ok(obj) = relaxed_blend_receive_max(scenario, &solve) {
        if let Some(sp) = shadow_from_relaxation(
            "receive_max",
            Some(0),
            base_objective_usd,
            obj,
            bump_monthly,
        ) {
            shadows.push(sp);
        }
    }

    if let Ok(obj) = relaxed_blend_receive_min(scenario, &solve) {
        if let Some(sp) = shadow_from_relaxation(
            "receive_min",
            Some(0),
            base_objective_usd,
            obj,
            bump_monthly,
        ) {
            shadows.push(sp);
        }
    }

    if let Ok(obj) = relaxed_blend_charge_max(scenario, &solve) {
        if let Some(sp) =
            shadow_from_relaxation("charge_max", Some(0), base_objective_usd, obj, bump_monthly)
        {
            shadows.push(sp);
        }
    }

    shadows
}

fn shadow_from_relaxation(
    name: &str,
    month: Option<usize>,
    base_objective_usd: f64,
    relaxed_objective_usd: f64,
    bump_units: f64,
) -> Option<ShadowPrice> {
    if bump_units <= 0.0 {
        return None;
    }
    let delta = base_objective_usd - relaxed_objective_usd;
    if delta.abs() < 0.01 {
        return None;
    }
    Some(ShadowPrice {
        name: name.to_string(),
        usd_per_bbl: delta / bump_units,
        month,
    })
}

fn relaxed_receive_max(
    scenario: &InventoryScenario,
    solve: &impl Fn(&InventoryScenario) -> OptimizationResult<f64>,
) -> OptimizationResult<f64> {
    let mut bumped = scenario.clone();
    bumped.site_limits.receive_max += BUMP_DAILY_BBL;
    solve(&bumped)
}

fn relaxed_receive_min(
    scenario: &InventoryScenario,
    solve: &impl Fn(&InventoryScenario) -> OptimizationResult<f64>,
) -> OptimizationResult<f64> {
    let mut bumped = scenario.clone();
    bumped.site_limits.receive_min = (bumped.site_limits.receive_min - BUMP_DAILY_BBL).max(0.0);
    solve(&bumped)
}

fn relaxed_charge_max(
    scenario: &InventoryScenario,
    solve: &impl Fn(&InventoryScenario) -> OptimizationResult<f64>,
) -> OptimizationResult<f64> {
    let mut bumped = scenario.clone();
    bumped.site_limits.charge_max += BUMP_DAILY_BBL;
    solve(&bumped)
}

fn relaxed_tank_cap(
    scenario: &InventoryScenario,
    solve: &impl Fn(&InventoryScenario) -> OptimizationResult<f64>,
) -> OptimizationResult<f64> {
    let mut bumped = scenario.clone();
    bumped.site_limits.tank_cap += BUMP_TANK_BBL;
    solve(&bumped)
}

fn relaxed_blend_receive_max(
    scenario: &BlendScheduleScenario,
    solve: &impl Fn(&BlendScheduleScenario) -> OptimizationResult<f64>,
) -> OptimizationResult<f64> {
    let mut bumped = scenario.clone();
    bumped.site_limits.receive_max += BUMP_DAILY_BBL;
    solve(&bumped)
}

fn relaxed_blend_receive_min(
    scenario: &BlendScheduleScenario,
    solve: &impl Fn(&BlendScheduleScenario) -> OptimizationResult<f64>,
) -> OptimizationResult<f64> {
    let mut bumped = scenario.clone();
    bumped.site_limits.receive_min = (bumped.site_limits.receive_min - BUMP_DAILY_BBL).max(0.0);
    solve(&bumped)
}

fn relaxed_blend_charge_max(
    scenario: &BlendScheduleScenario,
    solve: &impl Fn(&BlendScheduleScenario) -> OptimizationResult<f64>,
) -> OptimizationResult<f64> {
    let mut bumped = scenario.clone();
    bumped.site_limits.charge_max += BUMP_DAILY_BBL;
    solve(&bumped)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ignores_negligible_sensitivity() {
        assert!(shadow_from_relaxation("receive_max", Some(0), 100.0, 100.0, 100.0).is_none());
    }

    #[test]
    fn computes_positive_shadow_when_relaxation_lowers_cost() {
        let sp = shadow_from_relaxation("tank_cap", None, 1000.0, 900.0, 100.0).unwrap();
        assert_eq!(sp.name, "tank_cap");
        assert!((sp.usd_per_bbl - 1.0).abs() < 1e-6);
    }
}
