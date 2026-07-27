//! End-to-end vertical path: assay → blend → constraints → optimize

use crude_assay::import_assay;
use crude_blending::{evaluate_blend, get_blend_property};
use crude_constraints::{evaluate_product_constraints, ProductConstraints, PropertyBound};
use crude_domain::PropertyId;
use crude_optimization::optimize_scenario;
use crude_scenarios::{BlendScenarioFile, Scenario};
use std::path::PathBuf;

fn fixture_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../fixtures")
}

#[test]
fn assay_import_normalizes_wti() {
    let path = fixture_root().join("assays/wti.json");
    let crude = import_assay(&path).unwrap();
    assert_eq!(crude.assay.api_gravity(), Some(39.6));
    assert_eq!(crude.assay.sulfur_wt_pct(), Some(0.24));
}

#[test]
fn blend_evaluate_gulf_coast() {
    let path = fixture_root().join("blends/gulf-coast-blend.yaml");
    let file = BlendScenarioFile::from_yaml_file(&path).unwrap();
    let recipe = file.to_blend_recipe();
    let crudes = file.build_crude_library();
    let eval = evaluate_blend(&recipe, &crudes, None, file.total_volume_bbl).unwrap();

    let api = get_blend_property(&eval, PropertyId::ApiGravity).unwrap();
    let sulfur = get_blend_property(&eval, PropertyId::SulfurWtPct).unwrap();
    assert!((api - 34.11).abs() < 0.1);
    assert!((sulfur - 1.188).abs() < 0.01);
}

#[test]
fn optimize_gulf_coast_scenario() {
    let path = fixture_root().join("scenarios/gulf-coast-slate.yaml");
    let scenario = Scenario::from_yaml_file(&path).unwrap();
    let result = optimize_scenario(&scenario).unwrap();

    assert!(result.constraints_satisfied);
    assert!(result.blend_api_gravity.unwrap() >= 28.0);
    assert!(result.blend_sulfur_wt_pct.unwrap() <= 1.5);
    assert!(result.objective_value_usd > 0.0);
}

#[test]
fn blend_constraints_on_fixture() {
    let path = fixture_root().join("blends/gulf-coast-blend.yaml");
    let file = BlendScenarioFile::from_yaml_file(&path).unwrap();
    let recipe = file.to_blend_recipe();
    let crudes = file.build_crude_library();
    let eval = evaluate_blend(&recipe, &crudes, None, file.total_volume_bbl).unwrap();

    let c = file.constraints.unwrap();
    let report = evaluate_product_constraints(
        &eval,
        &ProductConstraints {
            api_gravity: c.api_gravity.map(|b| PropertyBound {
                min: b.min,
                max: b.max,
            }),
            sulfur_wt_pct: c.sulfur_wt_pct.map(|b| PropertyBound {
                min: b.min,
                max: b.max,
            }),
            total_acid_number: None,
        },
    );
    // 70/30 WTI/Maya yields sulfur 1.19 wt% — within the 1.5% cap
    assert!(report.satisfied);
    let sulfur = get_blend_property(&eval, PropertyId::SulfurWtPct).unwrap();
    assert!((sulfur - 1.188).abs() < 0.01);
}
