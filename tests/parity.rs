//! Parity checks against recorded reference outputs from legacy Python optimizers.

use crude_optimization::{optimize_blend_schedule, optimize_inventory};
use crude_scenarios::{BlendScheduleScenario, InventoryScenario};
use serde::Deserialize;
use std::path::PathBuf;

fn fixture_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../fixtures")
}

#[derive(Debug, Deserialize)]
struct InventoryParityExpectation {
    scenario: String,
    tolerance_objective_pct: f64,
    objective_value_usd: f64,
    status: String,
    min_purchase_rows: usize,
}

#[test]
fn inventory_refinery_slate_solves_and_matches_shape() {
    let scenario_path = fixture_root().join("scenarios/refinery-inventory.yaml");
    let scenario = InventoryScenario::from_yaml_file(&scenario_path).unwrap();
    let result = optimize_inventory(&scenario).unwrap();

    assert_eq!(format!("{:?}", result.status).to_lowercase(), "optimal");
    assert!(result.objective_value_usd > 0.0);
    assert!(!result.purchase_plan.is_empty());
    assert_eq!(result.inventory_plan.len(), 7 * 3); // (months+1) * grades

    // Update fixtures/parity/inventory-refinery.json objective_value_usd after first green run
    let parity_path = fixture_root().join("parity/inventory-refinery.json");
    let expected: InventoryParityExpectation =
        serde_json::from_str(&std::fs::read_to_string(&parity_path).unwrap()).unwrap();

    if expected.objective_value_usd > 0.0 {
        let rel_err = (result.objective_value_usd - expected.objective_value_usd).abs()
            / expected.objective_value_usd;
        assert!(
            rel_err <= expected.tolerance_objective_pct,
            "objective mismatch: got {} expected {} (rel err {rel_err})",
            result.objective_value_usd,
            expected.objective_value_usd
        );
    }

    let total_bbl: f64 = result.purchase_plan.iter().map(|p| p.barrels).sum();
    assert!(result.purchase_plan.len() >= expected.min_purchase_rows);
    assert_eq!(expected.scenario, scenario.name);
    assert_eq!(expected.status.to_lowercase(), "optimal");

    // Locked parity: Python domain_pkg @ refinery-inventory fixture
    assert!(
        (total_bbl - 9050.0).abs() < 1.0,
        "total purchase bbl {total_bbl}"
    );
}

#[test]
fn blend_schedule_tiny_matches_python_golden() {
    let scenario_path = fixture_root().join("scenarios/blend-schedule-tiny.yaml");
    let scenario = BlendScheduleScenario::from_yaml_file(&scenario_path).unwrap();
    let result = optimize_blend_schedule(&scenario).unwrap();

    assert_eq!(format!("{:?}", result.status).to_lowercase(), "optimal");

    let parity_path = fixture_root().join("parity/blend-schedule-tiny.json");
    #[derive(Debug, Deserialize)]
    struct BlendParityExpectation {
        objective_value_usd: f64,
        total_purchase_bbl: f64,
        ending_inventory_bbl: f64,
    }
    let expected: BlendParityExpectation =
        serde_json::from_str(&std::fs::read_to_string(&parity_path).unwrap()).unwrap();

    assert!((result.objective_value_usd - expected.objective_value_usd).abs() < 1.0);
    let total_purchase: f64 = result.purchase_plan.iter().map(|p| p.barrels).sum();
    assert!((total_purchase - expected.total_purchase_bbl).abs() < 1.0);
    let end_inv = result
        .inventory_plan
        .iter()
        .find(|r| r.month == 1)
        .map(|r| r.inventory)
        .unwrap();
    assert!((end_inv - expected.ending_inventory_bbl).abs() < 1.0);
    assert!(result
        .shadow_prices
        .iter()
        .all(|sp| sp.usd_per_bbl.is_finite()));
}

#[test]
fn blend_schedule_12month_regression() {
    let scenario_path = fixture_root().join("scenarios/blend-schedule-12month.yaml");
    let scenario = BlendScheduleScenario::from_yaml_file(&scenario_path).unwrap();
    let result = optimize_blend_schedule(&scenario).unwrap();

    assert_eq!(format!("{:?}", result.status).to_lowercase(), "optimal");
    assert_eq!(scenario.months, 12);

    #[derive(Debug, Deserialize)]
    struct Blend12Parity {
        objective_value_usd: f64,
        total_purchase_bbl: f64,
        purchase_months: usize,
        tolerance_objective_pct: f64,
    }

    let parity_path = fixture_root().join("parity/blend-schedule-12month.json");
    let expected: Blend12Parity =
        serde_json::from_str(&std::fs::read_to_string(&parity_path).unwrap()).unwrap();

    let rel_err = (result.objective_value_usd - expected.objective_value_usd).abs()
        / expected.objective_value_usd;
    assert!(
        rel_err <= expected.tolerance_objective_pct,
        "objective mismatch: got {} expected {} (rel err {rel_err})",
        result.objective_value_usd,
        expected.objective_value_usd
    );

    let total_purchase: f64 = result.purchase_plan.iter().map(|p| p.barrels).sum();
    assert!((total_purchase - expected.total_purchase_bbl).abs() < 1.0);
    assert_eq!(
        result
            .purchase_plan
            .iter()
            .map(|p| p.month)
            .collect::<std::collections::HashSet<_>>()
            .len(),
        expected.purchase_months
    );
}

#[test]
fn inventory_refinery_includes_shadow_prices() {
    let scenario_path = fixture_root().join("scenarios/refinery-inventory.yaml");
    let scenario = InventoryScenario::from_yaml_file(&scenario_path).unwrap();
    let result = optimize_inventory(&scenario).unwrap();
    assert!(!result.shadow_prices.is_empty());
    assert!(result
        .shadow_prices
        .iter()
        .all(|sp| sp.usd_per_bbl.is_finite()));
}

#[test]
fn legacy_streamlit_purchase_plan_totals_parse() {
    let csv_path = fixture_root().join("parity/legacy-streamlit/purchase_plan_20250808_142702.csv");
    let text = std::fs::read_to_string(&csv_path).unwrap();
    let mut total_bbl = 0.0;
    for (i, line) in text.lines().enumerate() {
        if i == 0 {
            continue;
        }
        let cols: Vec<&str> = line.split(',').collect();
        total_bbl += cols[3].parse::<f64>().unwrap();
    }
    assert!((total_bbl - 6100.0).abs() < 1.0);

    let summary_path = fixture_root().join("parity/legacy-streamlit/summary_20250808_142702.json");
    #[derive(Debug, Deserialize)]
    struct LegacySummary {
        objective_value: f64,
        status: String,
    }
    let summary: LegacySummary =
        serde_json::from_str(&std::fs::read_to_string(&summary_path).unwrap()).unwrap();
    assert_eq!(summary.status, "optimal");
    assert!(summary.objective_value > 400_000.0);
}

#[test]
fn monte_carlo_fixture_statistics_stable() {
    use crude_scenarios::{simulate_gbm, MonteCarloConfig, PriceSeries};

    let closes: Vec<f64> = (0..252)
        .map(|i| 72.0 + (i as f64 * 0.02).sin() * 1.5)
        .collect();
    let series = PriceSeries { closes };
    let config = MonteCarloConfig {
        iterations: 1000,
        forecast_days: 63,
        seed: Some(3363),
    };
    let result = simulate_gbm(&series, &config).unwrap();
    assert!((result.mean_forecast - 72.0).abs() < 15.0);
    assert!(result.confidence_interval_lower < result.confidence_interval_upper);
}
