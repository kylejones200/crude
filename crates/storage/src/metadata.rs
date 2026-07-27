//! Run record metadata (solver, version, optional git commit).

use serde::{Deserialize, Serialize};

pub const SOLVER_NAME: &str = "microlp";

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RunMetadata {
    pub solver: String,
    pub crude_version: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub git_commit: Option<String>,
}

pub fn default_run_metadata() -> RunMetadata {
    RunMetadata {
        solver: SOLVER_NAME.to_string(),
        crude_version: env!("CARGO_PKG_VERSION").to_string(),
        git_commit: option_env!("CRUDE_GIT_COMMIT").map(|s| s.to_string()),
    }
}
