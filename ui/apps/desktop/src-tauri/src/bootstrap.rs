use serde::Serialize;
use tauri::Manager;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::Child;
use std::sync::{Arc, Mutex};
use std::thread;

use crate::paths::{
    install_json_path, is_sovereign_bootstrap_complete, resolve_apxv_root, runtime_ready,
};
use crate::python_cmd::spawn_python_module;

#[derive(Serialize, Clone)]
pub struct BootstrapStatus {
    pub apxv_root: String,
    pub source_root: String,
    pub runtime_ready: bool,
    pub running: bool,
    pub sovereign_setup: bool,
    pub bootstrap_complete: bool,
    pub partial: bool,
    pub install_json: Option<serde_json::Value>,
    pub exit_code: Option<i32>,
    pub last_lines: Vec<String>,
    pub error: Option<String>,
}

struct BootstrapState {
    child: Option<Child>,
    last_lines: Vec<String>,
    exit_code: Option<i32>,
    error: Option<String>,
}

static BOOTSTRAP: Mutex<BootstrapState> = Mutex::new(BootstrapState {
    child: None,
    last_lines: Vec::new(),
    exit_code: None,
    error: None,
});

fn read_install_json(apxv_root: &str) -> Option<serde_json::Value> {
    let path = install_json_path(apxv_root);
    let content = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&content).ok()
}

pub fn resolve_source_root(app: &tauri::AppHandle) -> Result<String, String> {
    if let Ok(src) = std::env::var("APXV_SOURCE_ROOT") {
        let trimmed = src.trim();
        if !trimmed.is_empty() {
            return Ok(trimmed.to_string());
        }
    }

    if let Ok(resource) = app.path().resource_dir() {
        let bundled = resource.join("runtime");
        if bundled.join("scripts").join("apxv_bootstrap.py").is_file() {
            return Ok(bundled.to_string_lossy().to_string());
        }
    }

    let apxv_root = resolve_apxv_root();
    if Path::new(&apxv_root)
        .join("scripts")
        .join("apxv_bootstrap.py")
        .is_file()
    {
        return Ok(apxv_root);
    }

    Err(
        "Runtime source tree not found (bundle runtime/ or set APXV_SOURCE_ROOT)".to_string(),
    )
}

fn copy_dir_recursive(src: &Path, dst: &Path) -> Result<(), String> {
    if !src.is_dir() {
        return Err(format!("Source is not a directory: {}", src.display()));
    }
    std::fs::create_dir_all(dst).map_err(|e| format!("mkdir {}: {e}", dst.display()))?;

    for entry in std::fs::read_dir(src).map_err(|e| format!("read_dir {}: {e}", src.display()))? {
        let entry = entry.map_err(|e| e.to_string())?;
        let file_type = entry.file_type().map_err(|e| e.to_string())?;
        let name = entry.file_name();
        let from = entry.path();
        let to = dst.join(&name);
        if file_type.is_dir() {
            copy_dir_recursive(&from, &to)?;
        } else if file_type.is_file() {
            if let Some(parent) = to.parent() {
                std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
            }
            std::fs::copy(&from, &to).map_err(|e| format!("copy {}: {e}", from.display()))?;
        }
    }
    Ok(())
}

pub fn ensure_runtime_payload(app: &tauri::AppHandle) -> Result<String, String> {
    let apxv_root = resolve_apxv_root();
    if runtime_ready(&apxv_root) {
        return Ok(apxv_root);
    }

    let resource = app
        .path()
        .resource_dir()
        .map_err(|e| format!("resource_dir: {e}"))?;
    let bundled = resource.join("runtime");
    if !bundled.join("scripts").join("apxv_serve.py").is_file() {
        return Err(
            "Bundled runtime payload missing. Reinstall APXV or set APXV_DEV_ROOT.".to_string(),
        );
    }

    let target = PathBuf::from(&apxv_root);
    std::fs::create_dir_all(&target)
        .map_err(|e| format!("Cannot create {}: {e}", target.display()))?;
    copy_dir_recursive(&bundled, &target)?;
    Ok(apxv_root)
}

fn attach_output_reader(child: &mut Child, lines: Arc<Mutex<Vec<String>>>) {
    if let Some(stdout) = child.stdout.take() {
        let stdout_lines = Arc::clone(&lines);
        thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines().map_while(Result::ok) {
                let mut guard = stdout_lines.lock().unwrap_or_else(|e| e.into_inner());
                guard.push(line);
                if guard.len() > 80 {
                    let drop = guard.len() - 80;
                    guard.drain(0..drop);
                }
            }
        });
    }
    if let Some(stderr) = child.stderr.take() {
        let lines = Arc::clone(&lines);
        thread::spawn(move || {
            let reader = BufReader::new(stderr);
            for line in reader.lines().map_while(Result::ok) {
                let mut guard = lines.lock().unwrap_or_else(|e| e.into_inner());
                guard.push(format!("[stderr] {line}"));
                if guard.len() > 80 {
                    let drop = guard.len() - 80;
                    guard.drain(0..drop);
                }
            }
        });
    }
}

#[tauri::command]
pub fn get_bootstrap_status(app: tauri::AppHandle) -> Result<BootstrapStatus, String> {
    let apxv_root = resolve_apxv_root();
    let source_root = resolve_source_root(&app).unwrap_or_else(|_| apxv_root.clone());
    let install_json = read_install_json(&apxv_root);
    let sovereign_setup = install_json
        .as_ref()
        .and_then(|j| j.get("sovereign_setup"))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    let mut guard = BOOTSTRAP.lock().map_err(|e| e.to_string())?;
    let running = if let Some(child) = guard.child.as_mut() {
        match child.try_wait() {
            Ok(None) => true,
            Ok(Some(status)) => {
                guard.exit_code = status.code();
                guard.child = None;
                false
            }
            Err(e) => return Err(format!("Bootstrap process check failed: {e}")),
        }
    } else {
        false
    };

    let partial = guard.exit_code == Some(2)
        || install_json
            .as_ref()
            .map(|j| {
                let ollama = j
                    .get("ollama")
                    .and_then(|v| v.get("verified"))
                    .and_then(|v| v.as_bool());
                let voice = j
                    .get("voice")
                    .and_then(|v| v.get("enabled"))
                    .and_then(|v| v.as_bool());
                ollama == Some(false) || voice == Some(false)
            })
            .unwrap_or(false);

    Ok(BootstrapStatus {
        apxv_root,
        source_root,
        runtime_ready: runtime_ready(&resolve_apxv_root()),
        running,
        sovereign_setup,
        bootstrap_complete: sovereign_setup && !running,
        partial,
        install_json,
        exit_code: guard.exit_code,
        last_lines: guard.last_lines.clone(),
        error: guard.error.clone(),
    })
}

#[tauri::command]
pub fn run_bootstrap(
    app: tauri::AppHandle,
    skip_ollama: Option<bool>,
    skip_voice: Option<bool>,
) -> Result<String, String> {
    let apxv_root = ensure_runtime_payload(&app)?;
    let source_root = resolve_source_root(&app)?;

    let mut guard = BOOTSTRAP.lock().map_err(|e| e.to_string())?;
    if let Some(child) = guard.child.as_mut() {
        match child.try_wait() {
            Ok(None) => return Ok("already_running".into()),
            Ok(Some(status)) => {
                guard.exit_code = status.code();
                guard.child = None;
            }
            Err(e) => return Err(format!("Bootstrap process check failed: {e}")),
        }
    }

    let mut args = vec![
        "--base-path",
        &apxv_root,
        "--source-root",
        &source_root,
        "--profile",
        "production",
        "--json-report",
        "--skip-prover-build",
    ];
    let skip_ollama_flag = skip_ollama.unwrap_or(false);
    let skip_voice_flag = skip_voice.unwrap_or(false);
    if skip_ollama_flag {
        args.push("--skip-ollama");
    }
    if skip_voice_flag {
        args.push("--skip-voice");
    }

    let lines = Arc::new(Mutex::new(Vec::<String>::new()));
    let mut child = spawn_python_module("scripts.apxv_bootstrap", &args, &apxv_root, true)?;
    attach_output_reader(&mut child, Arc::clone(&lines));
    guard.child = Some(child);
    guard.exit_code = None;
    guard.error = None;
    guard.last_lines = Vec::new();
    drop(guard);

    let state_lines = lines;
    thread::spawn(move || {
        loop {
            thread::sleep(std::time::Duration::from_millis(400));
            let snapshot = state_lines
                .lock()
                .map(|g| g.clone())
                .unwrap_or_default();
            if let Ok(mut guard) = BOOTSTRAP.lock() {
                guard.last_lines = snapshot;
                if let Some(child) = guard.child.as_mut() {
                    if let Ok(Some(status)) = child.try_wait() {
                        guard.exit_code = status.code();
                        guard.child = None;
                        if status.success() {
                            break;
                        }
                        guard.error = Some(format!(
                            "Bootstrap exited with code {}",
                            status.code().unwrap_or(-1)
                        ));
                        break;
                    }
                } else {
                    break;
                }
            }
        }
    });

    Ok("started".into())
}

pub fn sovereign_ready() -> bool {
    is_sovereign_bootstrap_complete(&resolve_apxv_root())
}