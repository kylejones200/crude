//! Shared API request parsing: path on disk or inline YAML.

use std::path::{Component, Path, PathBuf};

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

/// Data roots for scenario/assay file reads (`CRUDE_DATA_ROOT` or discovered `fixtures/`).
pub fn resolve_data_roots() -> Vec<PathBuf> {
    if let Ok(raw) = std::env::var("CRUDE_DATA_ROOT") {
        return raw
            .split(',')
            .map(|s| PathBuf::from(s.trim()))
            .filter(|p| !p.as_os_str().is_empty())
            .collect();
    }
    for candidate in [PathBuf::from("fixtures"), PathBuf::from("crude/fixtures")] {
        if candidate.join("assays/wti.json").is_file() {
            return vec![candidate];
        }
    }
    vec![PathBuf::from("fixtures")]
}

pub fn resolve_runs_dir() -> PathBuf {
    std::env::var("CRUDE_RUNS_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("runs"))
}

/// Resolve `user_path` under one of `roots` (rejects `..`, requires normalized path under root).
pub fn allowed_path(roots: &[PathBuf], user_path: &str) -> Result<PathBuf, String> {
    if user_path.is_empty() {
        return Err("path is empty".into());
    }
    let user = PathBuf::from(user_path);
    if user
        .components()
        .any(|c| matches!(c, Component::ParentDir))
    {
        return Err("path must not contain ..".into());
    }

    for root in roots {
        let root_abs = absolute_root(root)?;
        let candidate = if user.is_absolute() {
            user.clone()
        } else {
            root_abs.join(&user)
        };
        let normalized = normalize_path(&candidate);
        if normalized.starts_with(&root_abs) {
            return Ok(candidate);
        }
    }
    Err(format!("path not allowed under configured roots: {user_path}"))
}

pub fn absolute_root(root: &Path) -> Result<PathBuf, String> {
    if root.exists() {
        root.canonicalize().map_err(|e| format!("invalid root {}: {e}", root.display()))
    } else {
        std::env::current_dir()
            .map(|cwd| normalize_path(&cwd.join(root)))
            .map_err(|e| e.to_string())
    }
}

fn normalize_path(path: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for component in path.components() {
        match component {
            Component::Prefix(p) => out.push(p.as_os_str()),
            Component::RootDir => out.push(component.as_os_str()),
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            Component::Normal(c) => out.push(c),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn rejects_parent_dir_traversal() {
        let roots = vec![PathBuf::from("fixtures")];
        assert!(allowed_path(&roots, "../etc/passwd").is_err());
    }

    #[test]
    fn allows_path_under_root() {
        let dir = std::env::temp_dir().join(format!(
            "crude-api-path-test-{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&dir).unwrap();
        let file = dir.join("sample.json");
        fs::write(&file, "{}").unwrap();
        let allowed = allowed_path(std::slice::from_ref(&dir), "sample.json").unwrap();
        assert_eq!(allowed, file.canonicalize().unwrap());
        let _ = fs::remove_dir_all(&dir);
    }
}
