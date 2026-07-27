use serde::{Deserialize, Serialize};
use std::fmt;

/// Stable identifier for a crude stream.
#[derive(Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct CrudeId(pub String);

impl CrudeId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for CrudeId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl From<&str> for CrudeId {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}
