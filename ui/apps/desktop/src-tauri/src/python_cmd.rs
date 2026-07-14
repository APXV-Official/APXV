use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};

fn python_runs_module(python: &str) -> bool {
    Command::new(python)
        .args(["-c", "import sys; assert sys.version_info >= (3, 10)"])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[cfg(windows)]
fn windows_python_candidates() -> Vec<PathBuf> {
    let mut candidates = Vec::new();
    if let Ok(local) = std::env::var("LOCALAPPDATA") {
        let local = PathBuf::from(local);
        let python_root = local.join("Python");
        if let Ok(entries) = std::fs::read_dir(&python_root) {
            for entry in entries.flatten() {
                let path = entry.path().join("python.exe");
                if path.is_file() {
                    candidates.push(path);
                }
            }
        }
        let programs = local.join("Programs").join("Python");
        if let Ok(entries) = std::fs::read_dir(&programs) {
            for entry in entries.flatten() {
                let path = entry.path().join("python.exe");
                if path.is_file() {
                    candidates.push(path);
                }
            }
        }
    }
    if let Ok(program_files) = std::env::var("ProgramFiles") {
        let root = PathBuf::from(program_files).join("Python");
        if let Ok(entries) = std::fs::read_dir(&root) {
            for entry in entries.flatten() {
                let path = entry.path().join("python.exe");
                if path.is_file() {
                    candidates.push(path);
                }
            }
        }
    }
    candidates
}

/// Resolve the real Python executable (not the Windows Store stub).
pub fn resolve_python_executable() -> Result<String, String> {
    #[cfg(windows)]
    {
        if let Ok(output) = Command::new("py")
            .args(["-3", "-c", "import sys; print(sys.executable)"])
            .output()
        {
            if output.status.success() {
                let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !path.is_empty() && Path::new(&path).is_file() && python_runs_module(&path) {
                    return Ok(path);
                }
            }
        }

        for path in windows_python_candidates() {
            let path_str = path.to_string_lossy().to_string();
            if python_runs_module(&path_str) {
                return Ok(path_str);
            }
        }

        for bin in ["python3", "python"] {
            if python_runs_module(bin) {
                return Ok(bin.into());
            }
        }

        return Err(
            "Python 3.10+ not found for desktop server spawn. Install Python 3 from python.org or the Microsoft Store, then retry Start server in Settings.".into(),
        );
    }

    #[cfg(not(windows))]
    {
        for bin in ["python3", "python"] {
            if Command::new(bin)
                .arg("--version")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false)
            {
                return Ok(bin.into());
            }
        }
        Err("Python 3 not found (install python3 or python)".into())
    }
}

/// Spawn a long-running Python module; tracks the real interpreter process (not `py` on Windows).
pub fn spawn_python_module_server(module: &str, args: &[&str], cwd: &str) -> Result<Child, String> {
    let python = resolve_python_executable()?;
    let mut module_args = vec!["-m", module];
    module_args.extend_from_slice(args);

    let mut cmd = Command::new(&python);
    cmd.args(&module_args).current_dir(cwd);

    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        unsafe {
            cmd.pre_exec(|| {
                libc::setpgid(0, 0);
                Ok(())
            });
        }
    }

    cmd.spawn()
        .map_err(|e| format!("Failed to start {module} with {python}: {e}"))
}

/// Spawn `python -m <module>` using the platform-appropriate interpreter.
pub fn spawn_python_module(
    module: &str,
    args: &[&str],
    cwd: &str,
    capture_output: bool,
) -> Result<Child, String> {
    let mut module_args = vec!["-m", module];
    module_args.extend_from_slice(args);

    #[cfg(windows)]
    {
        let python = resolve_python_executable()?;
        let mut cmd = Command::new(&python);
        cmd.args(&module_args).current_dir(cwd);
        if capture_output {
            cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
        }
        return cmd
            .spawn()
            .map_err(|e| format!("Failed to start {module} with {python}: {e}"));
    }

    #[cfg(not(windows))]
    {
        let mut last_err = String::new();
        for bin in ["python3", "python"] {
            let mut cmd = Command::new(bin);
            cmd.args(&module_args).current_dir(cwd);
            if capture_output {
                cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
            }
            match cmd.spawn() {
                Ok(child) => return Ok(child),
                Err(e) => last_err = format!("{e}"),
            }
        }
        Err(format!("Failed to start {module}: {last_err}"))
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn module_args_include_dash_m() {
        let module = "scripts.apxv_serve";
        let args = ["--help"];
        let mut module_args = vec!["-m", module];
        module_args.extend_from_slice(&args);
        assert_eq!(module_args[0], "-m");
        assert_eq!(module_args[1], module);
        assert_eq!(module_args[2], "--help");
    }
}