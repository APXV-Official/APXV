use serde::Serialize;
use std::net::{SocketAddr, TcpStream};
use std::process::Child;
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use crate::paths::resolve_apxv_root;
use crate::python_cmd::spawn_python_module_server;

const DEFAULT_API_PORT: u16 = 8741;
const PORT_CLOSE_TIMEOUT: Duration = Duration::from_secs(5);

#[derive(Serialize)]
pub struct ServerStatus {
    pub running: bool,
    pub pid: Option<u32>,
    /// True when something accepts TCP connections on :8741.
    pub port_open: bool,
    /// True when the listener is the process spawned by this desktop session.
    pub managed: bool,
}

struct ServerState {
    child: Option<Child>,
}

static SERVER: Mutex<ServerState> = Mutex::new(ServerState { child: None });

fn local_api_reachable(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(800)).is_ok()
}

fn wait_port_closed(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if !local_api_reachable(port) {
            return true;
        }
        thread::sleep(Duration::from_millis(100));
    }
    !local_api_reachable(port)
}

fn wait_port_open(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if local_api_reachable(port) {
            return true;
        }
        thread::sleep(Duration::from_millis(100));
    }
    local_api_reachable(port)
}

fn kill_process_tree(pid: u32) {
    if pid == 0 {
        return;
    }

    #[cfg(windows)]
    {
        use std::process::Command;
        let _ = Command::new("taskkill")
            .args(["/F", "/T", "/PID", &pid.to_string()])
            .status();
    }

    #[cfg(unix)]
    {
        let pgid = -(pid as i32);
        unsafe {
            libc::kill(pgid, libc::SIGTERM);
        }
        thread::sleep(Duration::from_millis(250));
        unsafe {
            libc::kill(pgid, libc::SIGKILL);
        }
    }
}

#[cfg(windows)]
fn listener_pids_on_port(port: u16) -> Vec<u32> {
    use std::process::Command;
    let script = format!(
        "Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"
    );
    let output = Command::new("powershell")
        .args(["-NoProfile", "-Command", &script])
        .output();
    let Ok(output) = output else {
        return Vec::new();
    };
    if !output.status.success() {
        return Vec::new();
    }
    String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| line.trim().parse::<u32>().ok())
        .filter(|pid| *pid > 0)
        .collect()
}

#[cfg(not(windows))]
fn listener_pids_on_port(port: u16) -> Vec<u32> {
    use std::process::Command;
    let script = format!(
        "lsof -ti tcp:{port} -sTCP:LISTEN 2>/dev/null || fuser {port}/tcp 2>/dev/null"
    );
    let output = Command::new("sh").args(["-c", &script]).output();
    let Ok(output) = output else {
        return Vec::new();
    };
    String::from_utf8_lossy(&output.stdout)
        .split_whitespace()
        .filter_map(|token| token.parse::<u32>().ok())
        .filter(|pid| *pid > 0)
        .collect()
}

#[cfg(windows)]
fn stop_listeners_on_port(port: u16) {
    for pid in listener_pids_on_port(port) {
        kill_process_tree(pid);
    }
}

#[cfg(not(windows))]
fn stop_listeners_on_port(port: u16) {
    use std::process::Command;
    for pid in listener_pids_on_port(port) {
        kill_process_tree(pid);
    }
    let _ = Command::new("sh")
        .args([
            "-c",
            &format!(
                "fuser -k -TERM {port}/tcp 2>/dev/null; fuser -k -KILL {port}/tcp 2>/dev/null; true"
            ),
        ])
        .status();
}

fn release_api_port() -> Result<(), String> {
    stop_listeners_on_port(DEFAULT_API_PORT);
    if wait_port_closed(DEFAULT_API_PORT, PORT_CLOSE_TIMEOUT) {
        return Ok(());
    }
    stop_listeners_on_port(DEFAULT_API_PORT);
    if wait_port_closed(DEFAULT_API_PORT, Duration::from_secs(2)) {
        return Ok(());
    }
    Err(format!(
        "Port {DEFAULT_API_PORT} is still in use — close other apxv_serve listeners and retry"
    ))
}

fn spawn_apxv_serve(apxv_root: &str) -> Result<Child, String> {
    spawn_python_module_server("scripts.apxv_serve", &[], apxv_root)
}

fn reconcile_child(guard: &mut ServerState) -> Result<(), String> {
    let Some(child) = guard.child.as_mut() else {
        return Ok(());
    };
    match child.try_wait() {
        Ok(None) => Ok(()),
        Ok(Some(_)) => {
            guard.child = None;
            Ok(())
        }
        Err(e) => Err(format!("Process check failed: {e}")),
    }
}

#[tauri::command]
pub fn start_apxv_server(apxv_root: Option<String>) -> Result<String, String> {
    let root = apxv_root.unwrap_or_else(resolve_apxv_root);
    let mut guard = SERVER.lock().map_err(|e| e.to_string())?;
    reconcile_child(&mut guard)?;

    if local_api_reachable(DEFAULT_API_PORT) {
        if guard.child.is_some() {
            return Ok("already_running".into());
        }
        return Ok("already_running (external listener on :8741)".into());
    }

    if guard.child.is_some() {
        return Ok("already_running".into());
    }

    let child = spawn_apxv_serve(&root)?;
    let pid = child.id();
    guard.child = Some(child);

    let deadline = Instant::now() + Duration::from_secs(30);
    while Instant::now() < deadline {
        if local_api_reachable(DEFAULT_API_PORT) {
            return Ok(format!("started (pid {pid})"));
        }
        reconcile_child(&mut guard)?;
        if guard.child.is_none() {
            return Err("apxv_serve exited before the API became reachable".into());
        }
        thread::sleep(Duration::from_millis(200));
    }

    if wait_port_open(DEFAULT_API_PORT, Duration::from_millis(500)) {
        return Ok(format!("started (pid {pid})"));
    }

    Err(format!(
        "apxv_serve (pid {pid}) did not open :{DEFAULT_API_PORT} within 30s"
    ))
}

#[tauri::command]
pub fn stop_apxv_server() -> Result<(), String> {
    let mut guard = SERVER.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.child.take() {
        let pid = child.id();
        kill_process_tree(pid);
        let _ = child.wait();
    }
    release_api_port()
}

#[tauri::command]
pub fn restart_apxv_server(apxv_root: Option<String>) -> Result<String, String> {
    stop_apxv_server()?;
    start_apxv_server(apxv_root)
}

#[tauri::command]
pub fn get_apxv_server_status() -> Result<ServerStatus, String> {
    let mut guard = SERVER.lock().map_err(|e| e.to_string())?;
    reconcile_child(&mut guard)?;

    let port_open = local_api_reachable(DEFAULT_API_PORT);

    if let Some(child) = guard.child.as_ref() {
        return Ok(ServerStatus {
            running: true,
            pid: Some(child.id()),
            port_open,
            managed: true,
        });
    }

    if port_open {
        let pid = listener_pids_on_port(DEFAULT_API_PORT).into_iter().next();
        return Ok(ServerStatus {
            running: true,
            pid,
            port_open: true,
            managed: false,
        });
    }

    Ok(ServerStatus {
        running: false,
        pid: None,
        port_open: false,
        managed: false,
    })
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unreachable_port_is_not_open() {
        assert!(!local_api_reachable(19_874));
    }
}