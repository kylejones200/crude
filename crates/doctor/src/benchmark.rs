//! LP solve timing for standard fixtures (microlp production solver).

use crude_optimization::{optimize_blend_schedule, optimize_inventory, optimize_scenario};
use crude_scenarios::{BlendScheduleScenario, InventoryScenario, Scenario};
use serde::Serialize;
use std::path::PathBuf;
use std::time::Instant;

pub const SOLVER_NAME: &str = "microlp";

#[derive(Clone, Debug, Serialize)]
pub struct LpBenchmarkResult {
    pub scenario: String,
    pub solver: String,
    pub elapsed_ms: f64,
    pub objective_value_usd: f64,
    pub status: String,
}

pub fn run_lp_benchmarks(fixtures_root: Option<PathBuf>) -> Vec<LpBenchmarkResult> {
    let root = resolve_fixtures_root(fixtures_root);
    let mut results = Vec::new();

    if let Ok(scenario) =
        InventoryScenario::from_yaml_file(&root.join("scenarios/refinery-inventory.yaml"))
    {
        results.push(bench("refinery-inventory", || {
            optimize_inventory(&scenario)
                .map(|r| (r.objective_value_usd, format!("{:?}", r.status)))
        }));
    }

    if let Ok(scenario) =
        BlendScheduleScenario::from_yaml_file(&root.join("scenarios/blend-schedule-tiny.yaml"))
    {
        results.push(bench("blend-schedule-tiny", || {
            optimize_blend_schedule(&scenario)
                .map(|r| (r.objective_value_usd, format!("{:?}", r.status)))
        }));
    }

    if let Ok(scenario) =
        BlendScheduleScenario::from_yaml_file(&root.join("scenarios/blend-schedule-12month.yaml"))
    {
        results.push(bench("blend-schedule-12month", || {
            optimize_blend_schedule(&scenario)
                .map(|r| (r.objective_value_usd, format!("{:?}", r.status)))
        }));
    }

    if let Ok(scenario) = Scenario::from_yaml_file(&root.join("scenarios/gulf-coast-slate.yaml")) {
        results.push(bench("gulf-coast-static", || {
            optimize_scenario(&scenario).map(|r| (r.objective_value_usd, format!("{:?}", r.status)))
        }));
    }

    results
}

fn bench(
    scenario: &str,
    solve: impl FnOnce() -> Result<(f64, String), crude_optimization::OptimizationError>,
) -> LpBenchmarkResult {
    let start = Instant::now();
    match solve() {
        Ok((objective_value_usd, status)) => LpBenchmarkResult {
            scenario: scenario.to_string(),
            solver: SOLVER_NAME.to_string(),
            elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
            objective_value_usd,
            status,
        },
        Err(e) => LpBenchmarkResult {
            scenario: scenario.to_string(),
            solver: SOLVER_NAME.to_string(),
            elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
            objective_value_usd: f64::NAN,
            status: format!("error: {e}"),
        },
    }
}

fn resolve_fixtures_root(explicit: Option<PathBuf>) -> PathBuf {
    if let Some(path) = explicit {
        return path;
    }
    for candidate in [PathBuf::from("fixtures"), PathBuf::from("crude/fixtures")] {
        if candidate.join("assays/wti.json").is_file() {
            return candidate;
        }
    }
    PathBuf::from("fixtures")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn benchmarks_all_fixture_scenarios() {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../fixtures");
        let results = run_lp_benchmarks(Some(root));
        assert_eq!(results.len(), 4);
        assert!(results.iter().all(|r| r.status.contains("Optimal")));
    }
}
