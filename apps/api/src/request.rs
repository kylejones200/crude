//! Shared API request parsing: path on disk or inline YAML.

use std::path::PathBuf;

pub fn require_path_or_yaml(path: Option<&str>, yaml: Option<&str>) -> Result<PathOrYaml, String> {
    match (path, yaml) {
        (Some(p), None) => Ok(PathOrYaml::Path(p.to_string())),
        (None, Some(y)) => Ok(PathOrYaml::Yaml(y.to_string())),
        (Some(_), Some(_)) => Err("provide either path or yaml, not both".into()),
        (None, None) => Err("provide path or yaml".into()),
    }
}

pub enum PathOrYaml {
    Path(String),
    Yaml(String),
}

impl PathOrYaml {
    #[allow(dead_code)]
    pub fn as_path(&self) -> Option<&str> {
        match self {
            PathOrYaml::Path(p) => Some(p),
            PathOrYaml::Yaml(_) => None,
        }
    }
}

pub fn path_buf(path: &str) -> PathBuf {
    PathBuf::from(path)
}
