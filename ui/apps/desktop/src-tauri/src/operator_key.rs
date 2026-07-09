use serde::Serialize;
use std::path::{Path, PathBuf};

use crate::paths::resolve_apxv_root;

#[derive(Serialize)]
pub struct OperatorKeyInfo {
    pub key: String,
    pub file_path: String,
    pub file_content: String,
    pub key_id: Option<String>,
}

fn config_dir(apxv_root: &str) -> PathBuf {
    PathBuf::from(apxv_root)
        .join("managed")
        .join("config")
}

fn operator_key_paths(config_dir: &Path) -> Result<Vec<PathBuf>, String> {
    let entries = std::fs::read_dir(config_dir)
        .map_err(|e| format!("Cannot read {}: {e}", config_dir.display()))?;

    let mut paths: Vec<PathBuf> = entries
        .filter_map(|entry| entry.ok())
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .map(|name| name.starts_with("OPERATOR-KEY-") && name.ends_with(".txt"))
                .unwrap_or(false)
        })
        .collect();

    paths.sort();
    Ok(paths)
}

fn parse_operator_key(content: &str) -> Option<String> {
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("API Key:") {
            let key = trimmed.splitn(2, ':').nth(1)?.trim();
            if !key.is_empty() {
                return Some(key.to_string());
            }
        }
    }
    None
}

fn key_id_from_path(path: &Path) -> Option<String> {
    let stem = path.file_stem()?.to_str()?;
    stem.strip_prefix("OPERATOR-KEY-").map(str::to_string)
}

pub fn load_operator_key(apxv_root: &str) -> Result<OperatorKeyInfo, String> {
    let dir = config_dir(apxv_root);
    let paths = operator_key_paths(&dir)?;

    for path in paths {
        let file_content = std::fs::read_to_string(&path)
            .map_err(|e| format!("Cannot read {}: {e}", path.display()))?;
        if let Some(key) = parse_operator_key(&file_content) {
            return Ok(OperatorKeyInfo {
                key,
                file_path: path.display().to_string(),
                file_content,
                key_id: key_id_from_path(&path),
            });
        }
    }

    Err(format!(
        "No OPERATOR-KEY-*.txt found under {}. Run setup first.",
        dir.display()
    ))
}

fn downloads_dir() -> PathBuf {
    if let Ok(userprofile) = std::env::var("USERPROFILE") {
        return PathBuf::from(userprofile).join("Downloads");
    }
    if let Ok(home) = std::env::var("HOME") {
        return PathBuf::from(home).join("Downloads");
    }
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

#[tauri::command]
pub fn read_operator_key(apxv_root: Option<String>) -> Result<OperatorKeyInfo, String> {
    let root = apxv_root.unwrap_or_else(resolve_apxv_root);
    load_operator_key(&root)
}

#[tauri::command]
pub fn save_operator_key_file(apxv_root: Option<String>) -> Result<String, String> {
    let root = apxv_root.unwrap_or_else(resolve_apxv_root);
    let info = load_operator_key(&root)?;
    let downloads = downloads_dir();
    std::fs::create_dir_all(&downloads)
        .map_err(|e| format!("Cannot create Downloads folder: {e}"))?;

    let filename = info
        .key_id
        .map(|id| format!("OPERATOR-KEY-{id}.txt"))
        .unwrap_or_else(|| "OPERATOR-KEY-export.txt".to_string());
    let target = downloads.join(filename);
    std::fs::write(&target, &info.file_content)
        .map_err(|e| format!("Cannot write {}: {e}", target.display()))?;
    Ok(target.display().to_string())
}