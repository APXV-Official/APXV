use serde::Serialize;
use std::process::Child;
use std::sync::Mutex;

use crate::paths::resolve_apxv_root;
use crate::python_cmd::spawn_python_module;

#[derive(Serialize)]
pub struct ServerStatus {
    pub running: bool,
    pub pid: Option<u32>,
}

struct ServerState {
    child: Option<Child>,
}

static SERVER: Mutex<ServerState> = Mutex::new(ServerState { child: None });

fn spawn_apxv_serve(apxv_root: &str) -> Result<Child, String> {
    spawn_python_module("scripts.apxv_serve", &[], apxv_root, false)
}

#[tauri::command]
pub fn start_apxv_server(apxv_root: Option<String>) -> Result<String, String> {
    let root = apxv_root.unwrap_or_else(resolve_apxv_root);
    let mut guard = SERVER.lock().map_err(|e| e.to_string())?;

    if let Some(child) = guard.child.as_mut() {
        match child.try_wait() {
            Ok(None) => return Ok("already_running".into()),
            Ok(Some(_)) => {
                guard.child = None;
            }
            Err(e) => return Err(format!("Process check failed: {e}")),
        }
    }

    let child = spawn_apxv_serve(&root)?;
    let pid = child.id();
    guard.child = Some(child);
    Ok(format!("started (pid {pid})"))
}

#[tauri::command]
pub fn stop_apxv_server() -> Result<(), String> {
    let mut guard = SERVER.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.child.take() {
        child
            .kill()
            .map_err(|e| format!("Failed to stop apxv_serve: {e}"))?;
        let _ = child.wait();
    }
    Ok(())
}

#[tauri::command]
pub fn get_apxv_server_status() -> Result<ServerStatus, String> {
    let mut guard = SERVER.lock().map_err(|e| e.to_string())?;

    let Some(child) = guard.child.as_mut() else {
        return Ok(ServerStatus {
            running: false,
            pid: None,
        });
    };

    match child.try_wait() {
        Ok(None) => Ok(ServerStatus {
            running: true,
            pid: Some(child.id()),
        }),
        Ok(Some(_)) => {
            guard.child = None;
            Ok(ServerStatus {
                running: false,
                pid: None,
            })
        }
        Err(e) => Err(format!("Process check failed: {e}")),
    }
}

/// v1.3.x compat — removed in desktop v1.4
#[tauri::command]
pub fn start_apx_server(apxv_root: Option<String>) -> Result<String, String> {
    start_apxv_server(apxv_root)
}

#[tauri::command]
pub fn stop_apx_server() -> Result<(), String> {
    stop_apxv_server()
}

#[tauri::command]
pub fn get_apx_server_status() -> Result<ServerStatus, String> {
    get_apxv_server_status()
}

#[tauri::command]
pub fn get_default_apxv_root() -> String {
    resolve_apxv_root()
}