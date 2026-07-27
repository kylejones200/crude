use thiserror::Error;

pub type AssayResult<T> = Result<T, AssayError>;

#[derive(Debug, Error)]
pub enum AssayError {
    #[error("unsupported format: {0}")]
    UnsupportedFormat(String),

    #[error("parse error: {0}")]
    Parse(String),

    #[error("validation failed: {0}")]
    Validation(String),

    #[error(transparent)]
    Domain(#[from] crude_domain::DomainError),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
}
