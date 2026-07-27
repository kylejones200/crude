//! Environment and dependency checks for the crude toolchain.

use crude_assay::import_assay;
use crude_optimization::{optimize_blend_schedule, optimize_inventory, SolverStatus};
use crude_scenarios::{BlendScheduleScenario, InventoryScenario};
use serde::Serialize;
use std::path::{Path, PathBuf};

const REQUIRED_FIXTURES: &[&str] = &[
    "assays/wti.json",
    "blends/gulf-coast-blend.yaml",
    "scenarios/gulf-coast-slate.yaml",
    "scenarios/refinery-inventory.yaml",
    "scenarios/blend-schedule-tiny.yaml",
    "scenarios/blend-schedule-12month.yaml",
    "parity/inventory-refinery.json",
    "parity/blend-schedule-tiny.json",
    "parity/blend-schedule-12month.json",
];

#[derive(Clone, Debug, Serialize)]
pub struct DoctorReport {
    pub healthy: bool,
    pub fixtures_root: String,
    pub checks: Vec<DoctorCheck>,
}

#[derive(Clone, Debug, Serialize)]
pub struct DoctorCheck {
    pub name: String,
    pub ok: bool,
    pub detail: String,
}

pub fn run_doctor(fixtures_root: Option<PathBuf>, check_prices: bool) -> DoctorReport {
    let root = resolve_fixtures_root(fixtures_root);
    let mut checks = Vec::new();

    for rel in REQUIRED_FIXTURES {
        let path = root.join(rel);
        checks.push(DoctorCheck {
            name: format!("fixture:{rel}"),
            ok: path.is_file(),
            detail: if path.is_file() {
                "present".into()
            } else {
                format!("missing: {}", path.display())
            },
        });
    }

    checks.push(check_assay_import(&root));
    checks.push(check_inventory_lp(&root));
    checks.push(check_blend_schedule_lp(&root));

    if check_prices {
        checks.push(check_live_prices());
    }

    let healthy = checks.iter().all(|c| c.ok);
    DoctorReport {
        healthy,
        fixtures_root: root.display().to_string(),
        checks,
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

fn check_assay_import(root: &Path) -> DoctorCheck {
    let path = root.join("assays/wti.json");
    match import_assay(&path) {
        Ok(crude) => DoctorCheck {
            name: "assay:import".into(),
            ok: !crude.id.as_str().is_empty(),
            detail: format!("imported {}", crude.id),
        },
        Err(e) => DoctorCheck {
            name: "assay:import".into(),
            ok: false,
            detail: e.to_string(),
        },
    }
}

fn check_inventory_lp(root: &Path) -> DoctorCheck {
    let path = root.join("scenarios/refinery-inventory.yaml");
    let scenario = match InventoryScenario::from_yaml_file(&path) {
        Ok(s) => s,
        Err(e) => {
            return DoctorCheck {
                name: "solver:inventory_lp".into(),
                ok: false,
                detail: e.to_string(),
            };
        }
    };
    match optimize_inventory(&scenario) {
        Ok(result) => DoctorCheck {
            name: "solver:inventory_lp".into(),
            ok: matches!(result.status, SolverStatus::Optimal),
            detail: format!("objective ${:.0}", result.objective_value_usd),
        },
        Err(e) => DoctorCheck {
            name: "solver:inventory_lp".into(),
            ok: false,
            detail: e.to_string(),
        },
    }
}

fn check_blend_schedule_lp(root: &Path) -> DoctorCheck {
    let path = root.join("scenarios/blend-schedule-tiny.yaml");
    let scenario = match BlendScheduleScenario::from_yaml_file(&path) {
        Ok(s) => s,
        Err(e) => {
            return DoctorCheck {
                name: "solver:blend_schedule_lp".into(),
                ok: false,
                detail: e.to_string(),
            };
        }
    };
    match optimize_blend_schedule(&scenario) {
        Ok(result) => DoctorCheck {
            name: "solver:blend_schedule_lp".into(),
            ok: matches!(result.status, SolverStatus::Optimal),
            detail: format!("objective ${:.0}", result.objective_value_usd),
        },
        Err(e) => DoctorCheck {
            name: "solver:blend_schedule_lp".into(),
            ok: false,
            detail: e.to_string(),
        },
    }
}

fn check_live_prices() -> DoctorCheck {
    match crude_economics::fetch_live_wti_brent() {
        Ok(prices) => {
            let ok = prices.wti.is_some() || prices.brent.is_some();
            DoctorCheck {
                name: "network:yahoo_prices".into(),
                ok,
                detail: format!("wti={:?} brent={:?}", prices.wti, prices.brent),
            }
        }
        Err(e) => DoctorCheck {
            name: "network:yahoo_prices".into(),
            ok: false,
            detail: e.to_string(),
        },
    }
}
