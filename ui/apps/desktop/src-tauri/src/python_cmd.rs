use std::path::Path;
use std::process::{Child, Command, Stdio};

/// Resolve the real Python executable (not the Windows `py` launcher stub).
pub fn resolve_python_executable() -> Result<String, String> {
    #[cfg(windows)]
    {
        if let Ok(output) = Command::new("py")
            .args(["-3", "-c", "import sys; print(sys.executable)"])
            .output()
        {
            if output.status.success() {
                let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !path.is_empty() && Path::new(&path).is_file() {
                    return Ok(path);
                }
            }
        }
        return Ok("python".into());
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

    Command::new(&python)
        .args(&module_args)
        .current_dir(cwd)
        .spawn()
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
        let mut cmd = Command::new("py");
        cmd.arg("-3").args(&module_args).current_dir(cwd);
        if capture_output {
            cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
        }
        return cmd
            .spawn()
            .or_else(|_| {
                let mut fallback = Command::new("python");
                fallback.args(&module_args).current_dir(cwd);
                if capture_output {
                    fallback.stdout(Stdio::piped()).stderr(Stdio::piped());
                }
                fallback.spawn()
            })
            .map_err(|e| format!("Failed to start {module}: {e}"));
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