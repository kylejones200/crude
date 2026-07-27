//! Multi-month inventory procurement LP (ported from crude-assay `inventory_optimization.py`).

#![allow(clippy::needless_range_loop)]

use crate::diagnostics::{diagnose_inventory, preflight_inventory, solver_failure};
use crate::error::{OptimizationError, OptimizationResult};
use crate::shadow::{estimate_inventory_shadow_prices, ShadowPrice};
use crate::solver::SolverStatus;
use crude_domain::{GRADES, SOURCES, UNMET_DEMAND_PENALTY_USD_PER_BBL};
use crude_scenarios::InventoryScenario;
use good_lp::{
    constraint, microlp, variable, variables, Expression, Solution, SolverModel, Variable,
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PurchaseRow {
    pub source: String,
    pub grade: String,
    pub month: usize,
    pub barrels: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct InventoryRow {
    pub grade: String,
    pub month: usize,
    pub inventory: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct InventoryOptimizationOutput {
    pub scenario_name: String,
    pub status: SolverStatus,
    pub objective_value_usd: f64,
    pub purchase_plan: Vec<PurchaseRow>,
    pub inventory_plan: Vec<InventoryRow>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub shadow_prices: Vec<ShadowPrice>,
    pub message: String,
}

struct InventoryLpSolution {
    objective_value_usd: f64,
    purchase_plan: Vec<PurchaseRow>,
    inventory_plan: Vec<InventoryRow>,
}

struct VarIndex {
    purchase: Vec<Vec<Vec<Variable>>>,
    demand: Vec<Vec<Variable>>,
    unmet: Vec<Vec<Variable>>,
    inventory: Vec<Vec<Variable>>,
}

pub fn optimize_inventory(
    scenario: &InventoryScenario,
) -> OptimizationResult<InventoryOptimizationOutput> {
    let solved = solve_inventory_lp(scenario)?;
    let shadow_prices =
        estimate_inventory_shadow_prices(scenario, solved.objective_value_usd, |s| {
            solve_inventory_lp(s).map(|r| r.objective_value_usd)
        });

    Ok(InventoryOptimizationOutput {
        scenario_name: scenario.name.clone(),
        status: SolverStatus::Optimal,
        objective_value_usd: solved.objective_value_usd,
        purchase_plan: solved.purchase_plan,
        inventory_plan: solved.inventory_plan,
        shadow_prices,
        message: "optimal solution found".into(),
    })
}

fn solve_inventory_lp(scenario: &InventoryScenario) -> OptimizationResult<InventoryLpSolution> {
    let preflight = preflight_inventory(scenario);
    if !preflight.is_empty() {
        return Err(solver_failure("preflight validation failed", preflight));
    }

    let months = scenario.months;
    let limits = &scenario.site_limits;
    let lead_times = &scenario.lead_times;
    let slate = &scenario.slate;

    let mut vars = variables!();
    let mut vi = VarIndex {
        purchase: Vec::new(),
        demand: Vec::new(),
        unmet: Vec::new(),
        inventory: Vec::new(),
    };

    for _source in SOURCES {
        let mut by_grade = Vec::new();
        for _grade in GRADES {
            let mut by_month = Vec::new();
            for _m in 0..months {
                by_month.push(vars.add(variable()));
            }
            by_grade.push(by_month);
        }
        vi.purchase.push(by_grade);
    }

    for grade_i in 0..GRADES.len() {
        let grade = GRADES[grade_i];
        let frac = slate.fraction(grade);
        let mut d_row = Vec::new();
        let mut u_row = Vec::new();
        for _m in 0..months {
            d_row.push(vars.add(variable().min(0.0)));
            u_row.push(vars.add(variable().min(0.0)));
        }
        vi.demand.push(d_row);
        vi.unmet.push(u_row);
        let _ = (frac, grade); // bounds added as constraints below
    }

    for _grade_i in 0..GRADES.len() {
        let mut inv_row = Vec::new();
        for _m in 0..=months {
            inv_row.push(vars.add(variable()));
        }
        vi.inventory.push(inv_row);
    }

    let objective = build_inventory_objective(&vi, scenario);
    let mut model = vars.minimise(objective).using(microlp);

    // Initial inventory
    for (grade_i, grade) in GRADES.iter().enumerate() {
        let init = scenario
            .initial_inventory
            .get(*grade)
            .copied()
            .unwrap_or(0.0);
        model = model.with(constraint!(vi.inventory[grade_i][0] == init));
    }

    // Demand / unmet / inventory bounds
    for grade_i in 0..GRADES.len() {
        let frac = slate.fraction(GRADES[grade_i]);
        let low = limits.tank_floor * frac;
        let high = limits.tank_cap * frac;
        for m in 0..months {
            let days = scenario.days_in_month(m) as f64;
            let min_d = limits.charge_min * days * frac;
            let max_d = limits.charge_max * days * frac;
            model = model.with(constraint!(vi.demand[grade_i][m] >= min_d));
            model = model.with(constraint!(vi.demand[grade_i][m] <= max_d));
            model = model.with(constraint!(vi.unmet[grade_i][m] <= max_d));
        }
        for m in 0..=months {
            model = model.with(constraint!(vi.inventory[grade_i][m] >= low));
            model = model.with(constraint!(vi.inventory[grade_i][m] <= high));
        }
    }

    // Non-negative purchases
    for source_i in 0..SOURCES.len() {
        for grade_i in 0..GRADES.len() {
            for m in 0..months {
                model = model.with(constraint!(vi.purchase[source_i][grade_i][m] >= 0.0));
            }
        }
    }

    // Inventory balance with lead times
    for m in 1..=months {
        for grade_i in 0..GRADES.len() {
            let prev = vi.inventory[grade_i][m - 1];
            let demand = vi.demand[grade_i][m - 1];
            let unmet = vi.unmet[grade_i][m - 1];
            let inv = vi.inventory[grade_i][m];

            let mut balance = Expression::from_other_affine(prev) - demand + unmet;
            for (source_i, source) in SOURCES.iter().enumerate() {
                let lt = lead_times.for_source(source) as i32;
                let order_month = m as i32 - 1 - lt;
                if order_month >= 0 && (order_month as usize) < months {
                    balance += vi.purchase[source_i][grade_i][order_month as usize];
                }
            }
            model = model.with(constraint!(balance == inv));
        }
    }

    // Receipt capacity
    for m in 0..months {
        let days = scenario.days_in_month(m) as f64;
        let mut total = Expression::from_other_affine(vi.purchase[0][0][m]);
        for source_i in 0..SOURCES.len() {
            for grade_i in 0..GRADES.len() {
                if source_i == 0 && grade_i == 0 {
                    continue;
                }
                total += vi.purchase[source_i][grade_i][m];
            }
        }
        model = model.with(constraint!(total.clone() <= limits.receive_max * days));
        model = model.with(constraint!(total >= limits.receive_min * days));
    }

    let solution = model
        .solve()
        .map_err(|e| solver_failure(&e.to_string(), diagnose_inventory(scenario)))?;

    validate_inventory_solution(scenario, &vi, &solution)?;

    let mut purchase_plan = Vec::new();
    for (source_i, source) in SOURCES.iter().enumerate() {
        for (grade_i, grade) in GRADES.iter().enumerate() {
            for m in 0..months {
                let barrels = solution.value(vi.purchase[source_i][grade_i][m]);
                if barrels > 1e-6 {
                    purchase_plan.push(PurchaseRow {
                        source: source.to_string(),
                        grade: grade.to_string(),
                        month: m,
                        barrels,
                    });
                }
            }
        }
    }

    let mut inventory_plan = Vec::new();
    for (grade_i, grade) in GRADES.iter().enumerate() {
        for m in 0..=months {
            inventory_plan.push(InventoryRow {
                grade: grade.to_string(),
                month: m,
                inventory: solution.value(vi.inventory[grade_i][m]),
            });
        }
    }

    let objective_value = compute_objective_value(&vi, scenario, &solution);

    Ok(InventoryLpSolution {
        objective_value_usd: objective_value,
        purchase_plan,
        inventory_plan,
    })
}

fn validate_inventory_solution(
    scenario: &InventoryScenario,
    vi: &VarIndex,
    solution: &impl Solution,
) -> OptimizationResult<()> {
    let limits = &scenario.site_limits;
    let slate = &scenario.slate;
    let months = scenario.months;

    for m in 0..months {
        let days = scenario.days_in_month(m) as f64;
        let mut recv = 0.0;
        for source_i in 0..SOURCES.len() {
            for grade_i in 0..GRADES.len() {
                recv += solution.value(vi.purchase[source_i][grade_i][m]);
            }
        }
        let min_r = limits.receive_min * days;
        let max_r = limits.receive_max * days;
        if recv < min_r - 1e-3 {
            return Err(OptimizationError::Validation(format!(
                "month {m}: receipts {recv:.1} below minimum {min_r:.1}"
            )));
        }
        if recv > max_r + 1e-3 {
            return Err(OptimizationError::Validation(format!(
                "month {m}: receipts {recv:.1} above maximum {max_r:.1}"
            )));
        }
    }

    for grade_i in 0..GRADES.len() {
        let frac = slate.fraction(GRADES[grade_i]);
        for m in 0..months {
            let days = scenario.days_in_month(m) as f64;
            let d = solution.value(vi.demand[grade_i][m]);
            let min_d = limits.charge_min * days * frac;
            let max_d = limits.charge_max * days * frac;
            if d < min_d - 1e-3 || d > max_d + 1e-3 {
                return Err(OptimizationError::Validation(format!(
                    "month {m} grade {}: demand {d:.1} outside [{min_d:.1}, {max_d:.1}]",
                    GRADES[grade_i]
                )));
            }
        }
    }

    Ok(())
}

fn compute_objective_value(
    vi: &VarIndex,
    scenario: &InventoryScenario,
    solution: &impl Solution,
) -> f64 {
    let months = scenario.months;
    let mut total = 0.0;
    for (source_i, source) in SOURCES.iter().enumerate() {
        for grade_i in 0..GRADES.len() {
            for m in 0..months {
                let vol = solution.value(vi.purchase[source_i][grade_i][m]);
                let price = scenario.monthly_prices[m].price_for_source(source);
                total += vol * price;
            }
        }
    }
    for grade_i in 0..GRADES.len() {
        for m in 0..months {
            total += UNMET_DEMAND_PENALTY_USD_PER_BBL * solution.value(vi.unmet[grade_i][m]);
        }
    }
    total
}

fn build_inventory_objective(vi: &VarIndex, scenario: &InventoryScenario) -> Expression {
    let months = scenario.months;
    let mut terms: Vec<Expression> = Vec::new();

    for (source_i, source) in SOURCES.iter().enumerate() {
        for grade_i in 0..GRADES.len() {
            for m in 0..months {
                let price = scenario.monthly_prices[m].price_for_source(source);
                terms.push(price * vi.purchase[source_i][grade_i][m]);
            }
        }
    }

    for grade_i in 0..GRADES.len() {
        for m in 0..months {
            terms.push(UNMET_DEMAND_PENALTY_USD_PER_BBL * vi.unmet[grade_i][m]);
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
    use crude_domain::{GradeSlate, LeadTimes, MonthlyPrices, SiteLimits};
    use std::collections::HashMap;

    fn tiny_inventory_scenario() -> InventoryScenario {
        InventoryScenario {
            name: "tiny".into(),
            start_year: 2025,
            start_month: 1,
            months: 2,
            site_limits: SiteLimits {
                receive_min: 0.0,
                receive_max: 100_000.0,
                charge_min: 1000.0,
                charge_max: 5000.0,
                tank_cap: 100_000.0,
                tank_floor: 1000.0,
            },
            lead_times: LeadTimes {
                foreign_m: 2,
                canada_m: 1,
                domestic_m: 1,
            },
            initial_inventory: HashMap::from([
                ("light".into(), 20_000.0),
                ("medium".into(), 20_000.0),
                ("heavy".into(), 20_000.0),
            ]),
            slate: GradeSlate {
                light: 40.0,
                medium: 35.0,
                heavy: 25.0,
            },
            monthly_prices: vec![
                MonthlyPrices {
                    brent: 80.0,
                    wti: 75.0,
                },
                MonthlyPrices {
                    brent: 82.0,
                    wti: 77.0,
                },
            ],
        }
    }

    #[test]
    fn inventory_lp_solves() {
        let result = optimize_inventory(&tiny_inventory_scenario()).unwrap();
        assert_eq!(result.status, SolverStatus::Optimal);
        assert!(result.objective_value_usd >= 0.0);
        assert!(!result.inventory_plan.is_empty());
    }
}
