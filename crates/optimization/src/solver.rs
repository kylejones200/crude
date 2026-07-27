use crate::error::{OptimizationError, OptimizationResult};
use crude_blending::{evaluate_blend, get_blend_property};
use crude_constraints::{evaluate_product_constraints, ProductConstraints, PropertyBound};
use crude_domain::{BlendComponent, BlendRecipe, CrudeId, PropertyId};
use crude_economics::feed_cost_per_bbl;
use crude_scenarios::{ProductConstraint, Scenario};
use good_lp::{
    constraint, microlp, variable, variables, Expression, Solution, SolverModel, Variable,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SolverStatus {
    Optimal,
    Infeasible,
    Error,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct VolumeAllocation {
    pub crude_id: String,
    pub volume_bbl: f64,
    pub fraction: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct OptimizationOutput {
    pub scenario_name: String,
    pub status: SolverStatus,
    pub objective_value_usd: f64,
    pub total_volume_bbl: f64,
    pub allocations: Vec<VolumeAllocation>,
    pub blend_api_gravity: Option<f64>,
    pub blend_sulfur_wt_pct: Option<f64>,
    pub feed_cost_per_bbl: Option<f64>,
    pub constraints_satisfied: bool,
    pub message: String,
}

/// Solve a scenario using a static blend LP (minimize feed cost subject to quality bounds).
pub fn optimize_scenario(scenario: &Scenario) -> OptimizationResult<OptimizationOutput> {
    let product = scenario
        .products
        .first()
        .ok_or_else(|| OptimizationError::Validation("no product defined".into()))?;

    let total_volume = scenario.target_volume_bbl.unwrap_or_else(|| {
        scenario
            .available_crudes
            .iter()
            .map(|c| c.max_volume)
            .sum::<f64>()
            .min(100_000.0)
    });

    if total_volume <= 0.0 {
        return Err(OptimizationError::Validation(
            "target volume must be positive".into(),
        ));
    }

    let crudes = scenario.build_crude_library();
    let n = scenario.available_crudes.len();

    let mut vars = variables!();
    let vol_vars: Vec<Variable> = (0..n).map(|_| vars.add(variable())).collect();

    let objective = build_objective(&vol_vars, scenario);

    let mut model = vars.minimise(objective).using(microlp);
    model = model.with(constraint!(sum_variables(&vol_vars) == total_volume));

    for (i, ac) in scenario.available_crudes.iter().enumerate() {
        model = model.with(constraint!(vol_vars[i] >= ac.min_volume));
        model = model.with(constraint!(vol_vars[i] <= ac.max_volume));
    }

    if let Some(api_c) = &product.constraints.api_gravity {
        if let Some(min_api) = api_c.min {
            let api_terms = weighted_property_terms(&vol_vars, scenario, &crudes, |c| {
                c.assay.api_gravity().unwrap_or(0.0)
            });
            model = model.with(constraint!(api_terms >= min_api * total_volume));
        }
        if let Some(max_api) = api_c.max {
            let api_terms = weighted_property_terms(&vol_vars, scenario, &crudes, |c| {
                c.assay.api_gravity().unwrap_or(0.0)
            });
            model = model.with(constraint!(api_terms <= max_api * total_volume));
        }
    }

    if let Some(s_c) = &product.constraints.sulfur_wt_pct {
        if let Some(max_s) = s_c.max {
            let sulfur_terms = weighted_property_terms(&vol_vars, scenario, &crudes, |c| {
                c.assay.sulfur_wt_pct().unwrap_or(0.0)
            });
            model = model.with(constraint!(sulfur_terms <= max_s * total_volume));
        }
        if let Some(min_s) = s_c.min {
            let sulfur_terms = weighted_property_terms(&vol_vars, scenario, &crudes, |c| {
                c.assay.sulfur_wt_pct().unwrap_or(0.0)
            });
            model = model.with(constraint!(sulfur_terms >= min_s * total_volume));
        }
    }

    let solution = model
        .solve()
        .map_err(|e| OptimizationError::Solver(e.to_string()))?;

    let mut volumes = HashMap::new();
    let mut allocations = Vec::new();
    let mut objective_value = 0.0;

    for (i, ac) in scenario.available_crudes.iter().enumerate() {
        let vol = solution.value(vol_vars[i]);
        if vol < -1e-6 {
            return Err(OptimizationError::Infeasible(
                "negative volume in solution".into(),
            ));
        }
        let vol = vol.max(0.0);
        let id = CrudeId::new(&ac.crude);
        volumes.insert(id.clone(), vol);
        objective_value += vol * ac.price_per_bbl;
        allocations.push(VolumeAllocation {
            crude_id: ac.crude.clone(),
            volume_bbl: vol,
            fraction: if total_volume > 0.0 {
                vol / total_volume
            } else {
                0.0
            },
        });
    }

    let recipe = BlendRecipe {
        components: allocations
            .iter()
            .filter(|a| a.fraction > 1e-9)
            .map(|a| BlendComponent {
                crude_id: CrudeId::new(&a.crude_id),
                fraction: a.fraction,
            })
            .collect(),
    };

    let prices = scenario.price_map();
    let blend_eval = evaluate_blend(&recipe, &crudes, Some(&prices), Some(total_volume))?;

    let constraint_report = evaluate_product_constraints(
        &blend_eval,
        &product_constraints_to_domain(&product.constraints),
    );

    Ok(OptimizationOutput {
        scenario_name: scenario.name.clone(),
        status: SolverStatus::Optimal,
        objective_value_usd: objective_value,
        total_volume_bbl: total_volume,
        blend_api_gravity: get_blend_property(&blend_eval, PropertyId::ApiGravity),
        blend_sulfur_wt_pct: get_blend_property(&blend_eval, PropertyId::SulfurWtPct),
        feed_cost_per_bbl: feed_cost_per_bbl(&volumes, &prices),
        constraints_satisfied: constraint_report.satisfied,
        allocations,
        message: if constraint_report.satisfied {
            "optimization completed successfully".into()
        } else {
            format!(
                "optimal cost solution but {} constraint violations",
                constraint_report.violations.len()
            )
        },
    })
}

fn build_objective(vol_vars: &[Variable], scenario: &Scenario) -> Expression {
    vol_vars
        .iter()
        .copied()
        .enumerate()
        .map(|(i, v)| scenario.available_crudes[i].price_per_bbl * v)
        .reduce(|a, b| a + b)
        .expect("at least one crude variable")
}

fn sum_variables(vars: &[Variable]) -> Expression {
    let mut iter = vars.iter().copied();
    let first = iter.next().expect("at least one variable");
    iter.fold(Expression::from_other_affine(first), |acc, v| acc + v)
}

fn weighted_property_terms(
    vol_vars: &[Variable],
    scenario: &Scenario,
    crudes: &HashMap<CrudeId, crude_domain::Crude>,
    property: impl Fn(&crude_domain::Crude) -> f64,
) -> Expression {
    vol_vars
        .iter()
        .copied()
        .enumerate()
        .map(|(i, v)| {
            let coeff = crudes
                .get(&CrudeId::new(&scenario.available_crudes[i].crude))
                .map(&property)
                .unwrap_or(0.0);
            coeff * v
        })
        .reduce(|a, b| a + b)
        .expect("at least one crude variable")
}

fn product_constraints_to_domain(c: &ProductConstraint) -> ProductConstraints {
    ProductConstraints {
        api_gravity: c.api_gravity.as_ref().map(|b| PropertyBound {
            min: b.min,
            max: b.max,
        }),
        sulfur_wt_pct: c.sulfur_wt_pct.as_ref().map(|b| PropertyBound {
            min: b.min,
            max: b.max,
        }),
        total_acid_number: c.total_acid_number.as_ref().map(|b| PropertyBound {
            min: b.min,
            max: b.max,
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crude_scenarios::{AvailableCrude, Objective, ObjectiveType, ProductSpec};

    fn gulf_coast_fixture() -> Scenario {
        Scenario {
            name: "gulf-coast-slate".into(),
            available_crudes: vec![
                AvailableCrude {
                    crude: "wti".into(),
                    min_volume: 0.0,
                    max_volume: 80_000.0,
                    price_per_bbl: 74.50,
                },
                AvailableCrude {
                    crude: "maya".into(),
                    min_volume: 10_000.0,
                    max_volume: 50_000.0,
                    price_per_bbl: 66.20,
                },
            ],
            products: vec![ProductSpec {
                name: "crude_blend".into(),
                constraints: ProductConstraint {
                    api_gravity: Some(crude_scenarios::PropertyConstraint {
                        min: Some(28.0),
                        max: None,
                    }),
                    sulfur_wt_pct: Some(crude_scenarios::PropertyConstraint {
                        min: None,
                        max: Some(1.5),
                    }),
                    total_acid_number: None,
                },
            }],
            objective: Objective {
                objective_type: ObjectiveType::MinimizeFeedCost,
            },
            target_volume_bbl: Some(80_000.0),
            crudes: [
                (
                    "wti".into(),
                    crude_scenarios::CrudeAssayRef {
                        api_gravity: 39.6,
                        sulfur_wt_pct: 0.24,
                        total_acid_number: None,
                        sbn: None,
                        insolubility_number: None,
                    },
                ),
                (
                    "maya".into(),
                    crude_scenarios::CrudeAssayRef {
                        api_gravity: 21.3,
                        sulfur_wt_pct: 3.4,
                        total_acid_number: None,
                        sbn: None,
                        insolubility_number: None,
                    },
                ),
            ]
            .into_iter()
            .collect(),
        }
    }

    #[test]
    fn optimizes_gulf_coast_scenario() {
        let result = optimize_scenario(&gulf_coast_fixture()).unwrap();
        assert_eq!(result.status, SolverStatus::Optimal);
        assert!(result.objective_value_usd > 0.0);
        assert!(result.constraints_satisfied);
        let api = result.blend_api_gravity.unwrap();
        let sulfur = result.blend_sulfur_wt_pct.unwrap();
        assert!(api >= 28.0);
        assert!(sulfur <= 1.5);
    }
}
