//! Multi-month assay blend LP (ported from crude-assay `blend_optimizer.py`).

use crate::diagnostics::{diagnose_blend_schedule, preflight_blend_schedule, solver_failure};
use crate::error::OptimizationResult;
use crate::shadow::{estimate_blend_schedule_shadow_prices, ShadowPrice};
use crate::solver::SolverStatus;
use crude_scenarios::{lead_time_for_source, BlendScheduleScenario};
use good_lp::{
    constraint, microlp, variable, variables, Expression, Solution, SolverModel, Variable,
};
use serde::{Deserialize, Serialize};

const UNMET_PENALTY: f64 = 1000.0;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AssayPurchaseRow {
    pub assay_name: String,
    pub month: usize,
    pub barrels: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AssayInventoryRow {
    pub assay_name: String,
    pub month: usize,
    pub inventory: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendScheduleOutput {
    pub scenario_name: String,
    pub status: SolverStatus,
    pub objective_value_usd: f64,
    pub purchase_plan: Vec<AssayPurchaseRow>,
    pub inventory_plan: Vec<AssayInventoryRow>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub shadow_prices: Vec<ShadowPrice>,
    pub message: String,
}

struct BlendLpSolution {
    objective_value_usd: f64,
    purchase_plan: Vec<AssayPurchaseRow>,
    inventory_plan: Vec<AssayInventoryRow>,
}

struct BlendVars {
    purchase: Vec<Vec<Variable>>,
    demand: Vec<Vec<Variable>>,
    unmet: Vec<Vec<Variable>>,
    inventory: Vec<Vec<Variable>>,
}

pub fn optimize_blend_schedule(
    scenario: &BlendScheduleScenario,
) -> OptimizationResult<BlendScheduleOutput> {
    let solved = solve_blend_schedule_lp(scenario)?;
    let shadow_prices = estimate_blend_schedule_shadow_prices(
        scenario,
        solved.objective_value_usd,
        |s| solve_blend_schedule_lp(s).map(|r| r.objective_value_usd),
    );

    Ok(BlendScheduleOutput {
        scenario_name: scenario.name.clone(),
        status: SolverStatus::Optimal,
        objective_value_usd: solved.objective_value_usd,
        purchase_plan: solved.purchase_plan,
        inventory_plan: solved.inventory_plan,
        shadow_prices,
        message: "optimal solution found".into(),
    })
}

fn solve_blend_schedule_lp(
    scenario: &BlendScheduleScenario,
) -> OptimizationResult<BlendLpSolution> {
    let preflight = preflight_blend_schedule(scenario);
    if !preflight.is_empty() {
        return Err(solver_failure("preflight validation failed", preflight));
    }

    let months = scenario.months;
    let limits = &scenario.site_limits;
    let lt = &scenario.lead_times;
    let n_assays = scenario.assays.len();
    let n_candidates = scenario.candidates.len();

    let inv_lb = limits.tank_floor * 0.1;
    let inv_ub = limits.tank_cap * 0.5;

    let mut vars = variables!();
    let bv = BlendVars {
        purchase: (0..n_assays)
            .map(|_| (0..months).map(|_| vars.add(variable().min(0.0))).collect())
            .collect(),
        demand: (0..n_candidates)
            .map(|_| (0..months).map(|_| vars.add(variable().min(0.0))).collect())
            .collect(),
        unmet: (0..n_candidates)
            .map(|_| (0..months).map(|_| vars.add(variable().min(0.0))).collect())
            .collect(),
        inventory: (0..n_assays)
            .map(|_| (0..=months).map(|_| vars.add(variable())).collect())
            .collect(),
    };

    let objective = build_blend_objective(scenario, &bv);
    let mut model = vars.minimise(objective).using(microlp);

    for (ai, assay) in scenario.assays.iter().enumerate() {
        let init = scenario
            .initial_inventory
            .get(&assay.name)
            .copied()
            .unwrap_or(0.0);
        model = model.with(constraint!(bv.inventory[ai][0] == init));
        for m in 0..=months {
            model = model.with(constraint!(bv.inventory[ai][m] >= inv_lb));
            model = model.with(constraint!(bv.inventory[ai][m] <= inv_ub));
        }
    }

    for ci in 0..n_candidates {
        let pct = scenario.candidates[ci].target_percentage / 100.0;
        for m in 0..months {
            let days = scenario.days_in_month(m) as f64;
            let min_d = limits.charge_min * days * pct;
            let max_d = limits.charge_max * days * pct;
            model = model.with(constraint!(bv.demand[ci][m] >= min_d));
            model = model.with(constraint!(bv.demand[ci][m] <= max_d));
            model = model.with(constraint!(bv.unmet[ci][m] <= max_d));
        }
    }

    for m in 1..=months {
        for (ai, assay) in scenario.assays.iter().enumerate() {
            let source_lt =
                lead_time_for_source(&assay.source, lt.foreign_m, lt.canada_m, lt.domestic_m);
            let order_month = m as i32 - 1 - source_lt as i32;

            let mut arrivals = Expression::from_other_affine(0.0);
            if order_month >= 0 && (order_month as usize) < months {
                arrivals += bv.purchase[ai][order_month as usize];
            }

            let prev_inv = bv.inventory[ai][m - 1];
            let mut total_demand = Expression::from_other_affine(0.0);
            let mut total_unmet = Expression::from_other_affine(0.0);

            for (ci, candidate) in scenario.candidates.iter().enumerate() {
                let has_assay = candidate
                    .components
                    .iter()
                    .any(|c| c.assay_name == assay.name);
                if has_assay {
                    total_demand += bv.demand[ci][m - 1];
                    total_unmet += bv.unmet[ci][m - 1];
                }
            }

            model = model.with(constraint!(
                prev_inv + arrivals - total_demand + total_unmet == bv.inventory[ai][m]
            ));
        }
    }

    for m in 0..months {
        let days = scenario.days_in_month(m) as f64;
        let mut total = Expression::from_other_affine(bv.purchase[0][m]);
        for ai in 1..n_assays {
            total += bv.purchase[ai][m];
        }
        model = model.with(constraint!(total.clone() <= limits.receive_max * days));
        model = model.with(constraint!(total >= limits.receive_min * days));
    }

    for (ci, candidate) in scenario.candidates.iter().enumerate() {
        let min_api = candidate.min_api_gravity;
        let max_sulfur = candidate.max_sulfur_content;
        for m in 0..months {
            let d_var = bv.demand[ci][m];
            if let Some(min_api) = min_api {
                let mut api_terms = Expression::from_other_affine(0.0);
                let mut has_terms = false;
                for comp in &candidate.components {
                    if let Some(ai) = scenario
                        .assays
                        .iter()
                        .position(|a| a.name == comp.assay_name)
                    {
                        api_terms += bv.purchase[ai][m] * comp.api_gravity;
                        has_terms = true;
                    }
                }
                if has_terms {
                    model = model.with(constraint!(api_terms >= min_api * d_var));
                }
            }
            if let Some(max_sulfur) = max_sulfur {
                let mut sulfur_terms = Expression::from_other_affine(0.0);
                let mut has_terms = false;
                for comp in &candidate.components {
                    if let Some(ai) = scenario
                        .assays
                        .iter()
                        .position(|a| a.name == comp.assay_name)
                    {
                        sulfur_terms += bv.purchase[ai][m] * comp.sulfur_content;
                        has_terms = true;
                    }
                }
                if has_terms {
                    model = model.with(constraint!(sulfur_terms <= max_sulfur * d_var));
                }
            }
        }
    }

    let solution = model.solve().map_err(|e| {
        solver_failure(&e.to_string(), diagnose_blend_schedule(scenario))
    })?;

    let objective_value = compute_blend_objective(scenario, &bv, &solution);

    let mut purchase_plan = Vec::new();
    for (ai, assay) in scenario.assays.iter().enumerate() {
        for m in 0..months {
            let barrels = solution.value(bv.purchase[ai][m]);
            if barrels > 1e-6 {
                purchase_plan.push(AssayPurchaseRow {
                    assay_name: assay.name.clone(),
                    month: m,
                    barrels,
                });
            }
        }
    }

    let mut inventory_plan = Vec::new();
    for (ai, assay) in scenario.assays.iter().enumerate() {
        for m in 0..=months {
            inventory_plan.push(AssayInventoryRow {
                assay_name: assay.name.clone(),
                month: m,
                inventory: solution.value(bv.inventory[ai][m]),
            });
        }
    }

    Ok(BlendLpSolution {
        objective_value_usd: objective_value,
        purchase_plan,
        inventory_plan,
    })
}

fn compute_blend_objective(
    scenario: &BlendScheduleScenario,
    bv: &BlendVars,
    solution: &impl Solution,
) -> f64 {
    let mut total = 0.0;
    for (ai, assay) in scenario.assays.iter().enumerate() {
        for m in 0..scenario.months {
            let vol = solution.value(bv.purchase[ai][m]);
            let price = assay
                .price_per_barrel
                .unwrap_or_else(|| scenario.monthly_prices[m].brent);
            total += vol * price;
        }
    }
    for ci in 0..scenario.candidates.len() {
        for m in 0..scenario.months {
            total += UNMET_PENALTY * solution.value(bv.unmet[ci][m]);
        }
    }
    total
}

fn build_blend_objective(scenario: &BlendScheduleScenario, bv: &BlendVars) -> Expression {
    let mut terms: Vec<Expression> = Vec::new();
    for (ai, assay) in scenario.assays.iter().enumerate() {
        for m in 0..scenario.months {
            let price = assay
                .price_per_barrel
                .unwrap_or_else(|| scenario.monthly_prices[m].brent);
            terms.push(price * bv.purchase[ai][m]);
        }
    }
    for ci in 0..scenario.candidates.len() {
        for m in 0..scenario.months {
            terms.push(UNMET_PENALTY * bv.unmet[ci][m]);
        }
    }
    terms
        .into_iter()
        .reduce(|a, b| a + b)
        .expect("objective terms")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crude_domain::{LeadTimes, MonthlyPrices, SiteLimits};
    use crude_scenarios::{
        AssayStreamSpec, BlendCandidateSpec, BlendComponentSpec, BlendScheduleScenario,
    };
    use std::collections::HashMap;

    fn tiny_blend_scenario() -> BlendScheduleScenario {
        BlendScheduleScenario {
            name: "tiny".into(),
            start_year: 2025,
            start_month: 1,
            months: 1,
            assays: vec![AssayStreamSpec {
                name: "Light".into(),
                price_per_barrel: Some(70.0),
                source: "domestic".into(),
            }],
            candidates: vec![BlendCandidateSpec {
                name: "BlendA".into(),
                target_percentage: 100.0,
                components: vec![BlendComponentSpec {
                    assay_name: "Light".into(),
                    api_gravity: 38.0,
                    sulfur_content: 0.5,
                }],
                min_api_gravity: Some(35.0),
                max_sulfur_content: Some(1.0),
            }],
            target_specs: HashMap::from([
                ("api_gravity".into(), 37.0),
                ("sulfur_content".into(), 0.6),
                ("total_acid_number".into(), 0.5),
            ]),
            initial_inventory: HashMap::from([("Light".into(), 50_000.0)]),
            site_limits: SiteLimits {
                receive_min: 10_000.0,
                receive_max: 100_000.0,
                charge_min: 10_000.0,
                charge_max: 80_000.0,
                tank_cap: 500_000.0,
                tank_floor: 10_000.0,
            },
            lead_times: LeadTimes {
                foreign_m: 2,
                canada_m: 1,
                domestic_m: 1,
            },
            monthly_prices: vec![MonthlyPrices {
                brent: 72.0,
                wti: 68.0,
            }],
        }
    }

    #[test]
    fn tiny_blend_matches_python_objective() {
        let result = optimize_blend_schedule(&tiny_blend_scenario()).unwrap();
        assert_eq!(result.status, SolverStatus::Optimal);
        assert!((result.objective_value_usd - 282_700_000.0).abs() < 1.0);
        let total_purchase: f64 = result.purchase_plan.iter().map(|r| r.barrels).sum();
        assert!((total_purchase - 310_000.0).abs() < 1.0);
        let end_inv = result
            .inventory_plan
            .iter()
            .find(|r| r.month == 1)
            .map(|r| r.inventory)
            .unwrap();
        assert!((end_inv - 1_000.0).abs() < 1.0);
    }
}
