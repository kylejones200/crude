//! Run result persistence (JSON).

mod error;
mod metadata;
mod run;
mod runs;

pub use error::{StorageError, StorageResult};
pub use metadata::{default_run_metadata, RunMetadata, SOLVER_NAME};
pub use run::{
    compare_runs, load_run, save_blend_schedule_run, save_inventory_run, save_run, RunBody,
    RunComparison, RunListEntry, RunRecord, RunSummary,
};
pub use runs::{get_run, list_runs};
