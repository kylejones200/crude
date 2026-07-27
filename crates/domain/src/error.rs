use thiserror::Error;

pub type DomainResult<T> = Result<T, DomainError>;

#[derive(Debug, Error, PartialEq)]
pub enum DomainError {
    #[error("invalid fraction: components must sum to 1.0 (got {0})")]
    InvalidFractionSum(f64),

    #[error("unknown crude: {0}")]
    UnknownCrude(String),

    #[error("missing property: {0}")]
    MissingProperty(String),

    #[error("validation failed: {0}")]
    Validation(String),

    #[error("invalid value for {property}: {message}")]
    InvalidValue { property: String, message: String },
}
