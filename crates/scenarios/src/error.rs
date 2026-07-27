use thiserror::Error;

pub type ScenarioResult<T> = Result<T, ScenarioError>;

#[derive(Debug, Error)]
pub enum ScenarioError {
    #[error("parse error: {0}")]
    Parse(String),

    #[error("validation failed: {0}")]
    Validation(String),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
}
