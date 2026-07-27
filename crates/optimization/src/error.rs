use thiserror::Error;

pub type OptimizationResult<T> = Result<T, OptimizationError>;

#[derive(Debug, Error)]
pub enum OptimizationError {
    #[error("solver error: {0}")]
    Solver(String),

    #[error("infeasible: {0}")]
    Infeasible(String),

    #[error("validation failed: {0}")]
    Validation(String),

    #[error(transparent)]
    Domain(#[from] crude_domain::DomainError),
}
