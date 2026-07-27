use crate::error::{StorageError, StorageResult};
use crate::metadata::default_run_metadata;
use chrono::{DateTime, Utc};
use crude_optimization::{
    BlendScheduleOutput, InventoryOptimizationOutput, OptimizationOutput, SolverStatus,
};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RunRecord {
    pub run_id: String,
    pub created_at: DateTime<Utc>,
    pub scenario_name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub metadata: Option<crate::metadata::RunMetadata>,
    #[serde(flatten)]
    pub body: RunBody,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "run_type", content = "result")]
pub enum RunBody {
    #[serde(rename = "static_blend")]
    StaticBlend(OptimizationOutput),
    #[serde(rename = "blend_schedule")]
    BlendSchedule(BlendScheduleOutput),
    #[serde(rename = "inventory")]
    Inventory(InventoryOptimizationOutput),
}

/// Legacy on-disk format (pre-unified storage).
#[derive(Clone, Debug, Deserialize)]
struct LegacyRunRecord {
    run_id: String,
    created_at: DateTime<Utc>,
    scenario_name: String,
    result: OptimizationOutput,
}

pub fn save_run(path: &Path, result: &OptimizationOutput) -> StorageResult<PathBuf> {
    save_record(
        path,
        RunBody::StaticBlend(result.clone()),
        &result.scenario_name,
    )
}

pub fn save_blend_schedule_run(
    path: &Path,
    result: &BlendScheduleOutput,
) -> StorageResult<PathBuf> {
    save_record(
        path,
        RunBody::BlendSchedule(result.clone()),
        &result.scenario_name,
    )
}

pub fn save_inventory_run(
    path: &Path,
    result: &InventoryOptimizationOutput,
) -> StorageResult<PathBuf> {
    save_record(
        path,
        RunBody::Inventory(result.clone()),
        &result.scenario_name,
    )
}

fn save_record(path: &Path, body: RunBody, scenario_name: &str) -> StorageResult<PathBuf> {
    let record = RunRecord {
        run_id: format!("run-{}", Utc::now().timestamp_millis()),
        created_at: Utc::now(),
        scenario_name: scenario_name.to_string(),
        metadata: Some(default_run_metadata()),
        body,
    };

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    let out_path = if path.is_dir() {
        path.join(format!("{}.json", record.run_id))
    } else {
        path.to_path_buf()
    };

    let json =
        serde_json::to_string_pretty(&record).map_err(|e| StorageError::Parse(e.to_string()))?;
    fs::write(&out_path, json)?;
    Ok(out_path)
}

pub fn load_run(path: &Path) -> StorageResult<RunRecord> {
    let text = fs::read_to_string(path)?;

    if let Ok(record) = serde_json::from_str::<RunRecord>(&text) {
        return Ok(record);
    }

    let legacy: LegacyRunRecord =
        serde_json::from_str(&text).map_err(|e| StorageError::Parse(e.to_string()))?;
    Ok(RunRecord {
        run_id: legacy.run_id,
        created_at: legacy.created_at,
        scenario_name: legacy.scenario_name,
        metadata: None,
        body: RunBody::StaticBlend(legacy.result),
    })
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RunListEntry {
    pub run_id: String,
    pub created_at: DateTime<Utc>,
    pub summary: RunSummary,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RunComparison {
    pub runs: Vec<RunSummary>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RunSummary {
    pub path: String,
    pub run_type: String,
    pub scenario_name: String,
    pub objective_value_usd: f64,
    pub status: String,
    pub feed_cost_per_bbl: Option<f64>,
    pub blend_api_gravity: Option<f64>,
    pub blend_sulfur_wt_pct: Option<f64>,
    pub constraints_satisfied: Option<bool>,
    pub total_purchase_bbl: Option<f64>,
}

impl RunRecord {
    pub fn run_type(&self) -> &'static str {
        match &self.body {
            RunBody::StaticBlend(_) => "static_blend",
            RunBody::BlendSchedule(_) => "blend_schedule",
            RunBody::Inventory(_) => "inventory",
        }
    }

    pub fn objective_value_usd(&self) -> f64 {
        match &self.body {
            RunBody::StaticBlend(r) => r.objective_value_usd,
            RunBody::BlendSchedule(r) => r.objective_value_usd,
            RunBody::Inventory(r) => r.objective_value_usd,
        }
    }

    pub fn status(&self) -> &SolverStatus {
        match &self.body {
            RunBody::StaticBlend(r) => &r.status,
            RunBody::BlendSchedule(r) => &r.status,
            RunBody::Inventory(r) => &r.status,
        }
    }

    pub fn to_summary(&self, path: &Path) -> RunSummary {
        let mut summary = RunSummary {
            path: path.display().to_string(),
            run_type: self.run_type().to_string(),
            scenario_name: self.scenario_name.clone(),
            objective_value_usd: self.objective_value_usd(),
            status: format!("{:?}", self.status()),
            feed_cost_per_bbl: None,
            blend_api_gravity: None,
            blend_sulfur_wt_pct: None,
            constraints_satisfied: None,
            total_purchase_bbl: None,
        };

        match &self.body {
            RunBody::StaticBlend(r) => {
                summary.feed_cost_per_bbl = r.feed_cost_per_bbl;
                summary.blend_api_gravity = r.blend_api_gravity;
                summary.blend_sulfur_wt_pct = r.blend_sulfur_wt_pct;
                summary.constraints_satisfied = Some(r.constraints_satisfied);
            }
            RunBody::BlendSchedule(r) => {
                summary.total_purchase_bbl = Some(r.purchase_plan.iter().map(|p| p.barrels).sum());
            }
            RunBody::Inventory(r) => {
                summary.total_purchase_bbl = Some(r.purchase_plan.iter().map(|p| p.barrels).sum());
            }
        }

        summary
    }
}

pub fn compare_runs(paths: &[PathBuf]) -> StorageResult<RunComparison> {
    let runs = paths
        .iter()
        .map(|path| load_run(path).map(|record| record.to_summary(path)))
        .collect::<StorageResult<Vec<_>>>()?;
    Ok(RunComparison { runs })
}

#[cfg(test)]
mod compare_tests {
    use super::*;
    use crate::run::save_inventory_run;
    use crude_optimization::{InventoryOptimizationOutput, SolverStatus};
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_runs_dir() -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("crude-compare-test-{nanos}"))
    }

    #[test]
    fn compare_runs_loads_summaries() {
        let dir = temp_runs_dir();
        let result = InventoryOptimizationOutput {
            scenario_name: "cmp".into(),
            status: SolverStatus::Optimal,
            objective_value_usd: 100.0,
            purchase_plan: vec![],
            inventory_plan: vec![],
            shadow_prices: vec![],
            message: "ok".into(),
        };
        let path = save_inventory_run(&dir.join("cmp-inventory.json"), &result).unwrap();
        let comparison = compare_runs(&[path]).unwrap();
        assert_eq!(comparison.runs.len(), 1);
        assert_eq!(comparison.runs[0].scenario_name, "cmp");
        let _ = std::fs::remove_dir_all(&dir);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crude_optimization::SolverStatus;

    #[test]
    fn legacy_static_blend_record_loads() {
        let legacy = serde_json::json!({
            "run_id": "run-1",
            "created_at": "2025-01-01T00:00:00Z",
            "scenario_name": "test",
            "result": {
                "scenario_name": "test",
                "status": "optimal",
                "objective_value_usd": 100.0,
                "total_volume_bbl": 1000.0,
                "allocations": [],
                "blend_api_gravity": 35.0,
                "blend_sulfur_wt_pct": 0.5,
                "feed_cost_per_bbl": 70.0,
                "constraints_satisfied": true,
                "message": "ok"
            }
        });
        let record: RunRecord = load_run_from_str(&legacy.to_string()).unwrap();
        assert_eq!(record.run_type(), "static_blend");
        assert_eq!(record.objective_value_usd(), 100.0);
    }

    fn load_run_from_str(text: &str) -> StorageResult<RunRecord> {
        if let Ok(record) = serde_json::from_str::<RunRecord>(text) {
            return Ok(record);
        }
        let legacy: LegacyRunRecord =
            serde_json::from_str(text).map_err(|e| StorageError::Parse(e.to_string()))?;
        Ok(RunRecord {
            run_id: legacy.run_id,
            created_at: legacy.created_at,
            scenario_name: legacy.scenario_name,
            metadata: None,
            body: RunBody::StaticBlend(legacy.result),
        })
    }

    #[test]
    fn unified_inventory_record_roundtrip() {
        let body = RunBody::Inventory(InventoryOptimizationOutput {
            scenario_name: "inv".into(),
            status: SolverStatus::Optimal,
            objective_value_usd: 500.0,
            purchase_plan: vec![],
            inventory_plan: vec![],
            shadow_prices: vec![],
            message: "ok".into(),
        });
        let record = RunRecord {
            run_id: "run-2".into(),
            created_at: Utc::now(),
            scenario_name: "inv".into(),
            metadata: None,
            body,
        };
        let text = serde_json::to_string(&record).unwrap();
        let loaded: RunRecord = serde_json::from_str(&text).unwrap();
        assert_eq!(loaded.run_type(), "inventory");
    }

    #[test]
    fn saved_run_includes_metadata() {
        let dir =
            std::env::temp_dir().join(format!("crude-meta-test-{}", Utc::now().timestamp_millis()));
        let result = InventoryOptimizationOutput {
            scenario_name: "meta".into(),
            status: SolverStatus::Optimal,
            objective_value_usd: 1.0,
            purchase_plan: vec![],
            inventory_plan: vec![],
            shadow_prices: vec![],
            message: "ok".into(),
        };
        let path = save_inventory_run(&dir.join("meta.json"), &result).unwrap();
        let record = load_run(&path).unwrap();
        assert!(record.metadata.is_some());
        assert_eq!(record.metadata.as_ref().unwrap().solver, "microlp");
        let _ = fs::remove_dir_all(&dir);
    }
}
