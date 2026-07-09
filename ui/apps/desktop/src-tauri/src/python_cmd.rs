use std::process::{Child, Command, Stdio};

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