use serde::Serialize;
use std::net::{SocketAddr, TcpStream};
use std::process::Child;
use std::sync::Mutex;
use std::time::Duration;

use crate::paths::resolve_apxv_root;
use crate::python_cmd::spawn_python_module_server;

const DEFAULT_API_PORT: u16 = 8741;

#[derive(Serialize)]
pub struct ServerStatus {
    pub running: bool,
    pub pid: Option<u32>,
}

struct ServerState {
    child: Option<Child>,
}

static SERVER: Mutex<ServerState> = Mutex::new(ServerState { child: None });

fn local_api_reachable(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(800)).is_ok()
}

#[cfg(windows)]
fn stop_listeners_on_port(port: u16) {
    use std::process::Command;
    let script = format!(
        "Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $PSItem.OwningProcess -Force -ErrorAction SilentlyContinue }}"
    );
    let _ = Command::new("powershell")
        .args(["-NoProfile", "-Command", &script])
        .status();
}

#[cfg(not(windows))]
fn stop_listeners_on_port(port: u16) {
    use std::process::Command;
    let _ = Command::new("sh")
        .args([
            "-c",
            &format!(
                "lsof -ti tcp:{port} -sTCP:LISTEN 2>/dev/null | xargs -r kill -9"
            ),
        ])
        .status();
}

fn spawn_apxv_serve(apxv_root: &str) -> Result<Child, String> {
    spawn_python_module_server("scripts.apxv_serve", &[], apxv_root)
}

#[tauri::command]
pub fn start_apxv_server(apxv_root: Option<String>) -> Result<String, String> {
    let root = apxv_root.unwrap_or_else(resolve_apxv_root);
    let mut guard = SERVER.lock().map_err(|e| e.to_string())?;

    if local_api_reachable(DEFAULT_API_PORT) {
        return Ok("already_running".into());
    }

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
        let _ = child.kill();
        let _ = child.wait();
    }
    stop_listeners_on_port(DEFAULT_API_PORT);
    Ok(())
}

#[tauri::command]
pub fn get_apxv_server_status() -> Result<ServerStatus, String> {
    let mut guard = SERVER.lock().map_err(|e| e.to_string())?;

    let Some(child) = guard.child.as_mut() else {
        if local_api_reachable(DEFAULT_API_PORT) {
            return Ok(ServerStatus {
                running: true,
                pid: None,
            });
        }
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