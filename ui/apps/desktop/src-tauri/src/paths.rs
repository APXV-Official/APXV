use std::path::{Path, PathBuf};

/// Operator data root per V1.3-PRODUCT-SPEC §3.1.
pub fn default_local_appdata_root() -> String {
    #[cfg(windows)]
    {
        if let Ok(local) = std::env::var("LOCALAPPDATA") {
            let trimmed = local.trim();
            if !trimmed.is_empty() {
                return PathBuf::from(trimmed)
                    .join("APXV")
                    .to_string_lossy()
                    .to_string();
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        if let Ok(home) = std::env::var("HOME") {
            let trimmed = home.trim();
            if !trimmed.is_empty() {
                return PathBuf::from(trimmed)
                    .join("Library")
                    .join("Application Support")
                    .join("APXV")
                    .to_string_lossy()
                    .to_string();
            }
        }
    }

    #[cfg(not(any(windows, target_os = "macos")))]
    {
        if let Ok(xdg) = std::env::var("XDG_DATA_HOME") {
            let trimmed = xdg.trim();
            if !trimmed.is_empty() {
                return PathBuf::from(trimmed)
                    .join("APXV")
                    .to_string_lossy()
                    .to_string();
            }
        }
        if let Ok(home) = std::env::var("HOME") {
            let trimmed = home.trim();
            if !trimmed.is_empty() {
                return PathBuf::from(trimmed)
                    .join(".local")
                    .join("share")
                    .join("APXV")
                    .to_string_lossy()
                    .to_string();
            }
        }
    }

    if let Ok(home) = std::env::var("USERPROFILE").or_else(|_| std::env::var("HOME")) {
        let trimmed = home.trim();
        if !trimmed.is_empty() {
            return PathBuf::from(trimmed)
                .join(".local")
                .join("share")
                .join("APXV")
                .to_string_lossy()
                .to_string();
        }
    }

    PathBuf::from(".")
        .join("APXV")
        .to_string_lossy()
        .to_string()
}

#[cfg(debug_assertions)]
fn dev_runtime_candidate() -> Option<String> {
    let exe = std::env::current_exe().ok()?;
    let mut dir = exe.parent()?;
    for _ in 0..10 {
        let candidate = dir.join("runtime");
        if candidate.join("scripts").join("apxv_serve.py").is_file() {
            return Some(candidate.to_string_lossy().to_string());
        }
        let remaster = dir.join("apxv-v1.3-remaster").join("runtime");
        if remaster.join("scripts").join("apxv_serve.py").is_file() {
            return Some(remaster.to_string_lossy().to_string());
        }
        dir = dir.parent()?;
    }
    None
}

/// Expand `%VAR%` / `$VAR` placeholders in a UI-supplied root path.
pub fn expand_apxv_root(path: &str) -> String {
    let trimmed = path.trim();
    if trimmed.is_empty() {
        return resolve_apxv_root();
    }

    let mut expanded = trimmed.to_string();
    for (name, value) in std::env::vars() {
        let win_token = format!("%{name}%");
        if expanded.contains(&win_token) {
            expanded = expanded.replace(&win_token, &value);
        }
        let unix_token = format!("${name}");
        if expanded.contains(&unix_token) {
            expanded = expanded.replace(&unix_token, &value);
        }
    }

    expanded
}

/// Resolve APXV instance root (managed/, keys/, runtime payload).
pub fn resolve_apxv_root() -> String {
    if let Ok(root) = std::env::var("APXV_ROOT") {
        let trimmed = root.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }

    if let Ok(dev) = std::env::var("APXV_DEV_ROOT") {
        let trimmed = dev.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }

    #[cfg(debug_assertions)]
    if let Some(candidate) = dev_runtime_candidate() {
        return candidate;
    }

    default_local_appdata_root()
}

pub fn install_json_path(apxv_root: &str) -> PathBuf {
    PathBuf::from(apxv_root)
        .join("managed")
        .join("config")
        .join("install.json")
}

pub fn is_sovereign_bootstrap_complete(apxv_root: &str) -> bool {
    let path = install_json_path(apxv_root);
    let Ok(content) = std::fs::read_to_string(path) else {
        return false;
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(&content) else {
        return false;
    };
    value
        .get("sovereign_setup")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
}

pub fn runtime_ready(apxv_root: &str) -> bool {
    Path::new(apxv_root)
        .join("scripts")
        .join("apxv_serve.py")
        .is_file()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn expand_apxv_root_replaces_localappdata_placeholder() {
        let local = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| "C:\\Users\\test\\AppData\\Local".into());
        let expanded = expand_apxv_root("%LOCALAPPDATA%\\APXV");
        assert!(expanded.contains("APXV"));
        assert!(!expanded.contains('%'));
        assert!(expanded.starts_with(&local) || expanded.contains("APXV"));
    }

    #[test]
    fn default_root_ends_with_apxv() {
        let root = default_local_appdata_root();
        assert!(
            root.ends_with("APXV") || root.ends_with("APXV/") || root.ends_with("APXV\\"),
            "expected APXV suffix, got {root}"
        );
    }

    #[cfg(windows)]
    #[test]
    fn windows_root_uses_localappdata_when_set() {
        let local = std::env::var("LOCALAPPDATA").expect("LOCALAPPDATA");
        let root = default_local_appdata_root();
        assert!(root.contains("APXV"));
        assert!(root.starts_with(&local) || root.contains("APXV"));
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn macos_root_uses_application_support_when_home_set() {
        let home = std::env::var("HOME").expect("HOME");
        let root = default_local_appdata_root();
        assert!(root.contains("Library"));
        assert!(root.contains("Application Support"));
        assert!(root.contains("APXV"));
        assert!(root.starts_with(&home));
    }

    #[cfg(all(unix, not(target_os = "macos")))]
    #[test]
    fn linux_root_uses_xdg_or_local_share() {
        let root = default_local_appdata_root();
        assert!(root.contains("APXV"));
        if std::env::var("XDG_DATA_HOME")
            .map(|v| !v.trim().is_empty())
            .unwrap_or(false)
        {
            assert!(root.contains("APXV"));
        } else if let Ok(home) = std::env::var("HOME") {
            assert!(root.starts_with(&home));
            assert!(root.contains(".local"));
        }
    }
}