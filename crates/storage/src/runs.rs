//! List and lookup persisted optimization runs.

use crate::error::{StorageError, StorageResult};
use crate::run::{load_run, RunListEntry, RunRecord};
use std::fs;
use std::path::{Path, PathBuf};

pub fn list_runs(dir: &Path) -> StorageResult<Vec<RunListEntry>> {
    if !dir.exists() {
        return Ok(Vec::new());
    }

    let mut entries = Vec::new();
    collect_runs(dir, dir, &mut entries)?;
    entries.sort_by_key(|b| std::cmp::Reverse(b.created_at));
    Ok(entries)
}

pub fn get_run(dir: &Path, run_id: &str) -> StorageResult<RunRecord> {
    if let Some(path) = find_run_path(dir, run_id)? {
        return load_run(&path);
    }
    Err(StorageError::NotFound(format!("run not found: {run_id}")))
}

fn collect_runs(_root: &Path, dir: &Path, out: &mut Vec<RunListEntry>) -> StorageResult<()> {
    let read_dir = fs::read_dir(dir).map_err(StorageError::Io)?;
    for entry in read_dir {
        let entry = entry.map_err(StorageError::Io)?;
        let path = entry.path();
        if path.is_dir() {
            collect_runs(_root, &path, out)?;
            continue;
        }
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        match load_run(&path) {
            Ok(record) => {
                let summary = record.to_summary(&path);
                out.push(RunListEntry {
                    run_id: record.run_id.clone(),
                    created_at: record.created_at,
                    summary,
                });
            }
            Err(_) => continue,
        }
    }
    Ok(())
}

fn find_run_path(dir: &Path, run_id: &str) -> StorageResult<Option<PathBuf>> {
    if !dir.exists() {
        return Ok(None);
    }
    find_run_path_inner(dir, run_id)
}

fn find_run_path_inner(dir: &Path, run_id: &str) -> StorageResult<Option<PathBuf>> {
    let read_dir = fs::read_dir(dir).map_err(StorageError::Io)?;
    for entry in read_dir {
        let entry = entry.map_err(StorageError::Io)?;
        let path = entry.path();
        if path.is_dir() {
            if let Some(found) = find_run_path_inner(&path, run_id)? {
                return Ok(Some(found));
            }
            continue;
        }
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        if let Ok(record) = load_run(&path) {
            if record.run_id == run_id {
                return Ok(Some(path));
            }
        }
    }
    Ok(None)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::run::save_inventory_run;
    use crude_optimization::{InventoryOptimizationOutput, SolverStatus};
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_runs_dir() -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("crude-runs-test-{nanos}"))
    }

    #[test]
    fn lists_and_finds_saved_run() {
        let dir = temp_runs_dir();
        let result = InventoryOptimizationOutput {
            scenario_name: "test-inv".into(),
            status: SolverStatus::Optimal,
            objective_value_usd: 42.0,
            purchase_plan: vec![],
            inventory_plan: vec![],
            shadow_prices: vec![],
            message: "ok".into(),
        };
        let path = save_inventory_run(&dir.join("test-inv-inventory.json"), &result).unwrap();
        let record = load_run(&path).unwrap();

        let listed = list_runs(&dir).unwrap();
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].run_id, record.run_id);

        let loaded = get_run(&dir, &record.run_id).unwrap();
        assert_eq!(loaded.scenario_name, "test-inv");

        let _ = fs::remove_dir_all(&dir);
    }
}
