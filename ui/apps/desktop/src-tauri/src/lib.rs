mod bootstrap;
mod operator_key;
mod paths;
mod python_cmd;
mod server;
mod tray;

use bootstrap::{get_bootstrap_status, run_bootstrap, sovereign_ready};
use operator_key::{read_operator_key, save_operator_key_file};
use server::{
    get_apx_server_status, get_apxv_server_status, get_default_apxv_root, start_apx_server,
    start_apxv_server, stop_apx_server, stop_apxv_server,
};

#[tauri::command]
fn show_main_window(app: tauri::AppHandle) -> Result<(), String> {
    tray::focus_main_window(&app);
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default();

    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            tray::focus_main_window(app);
        }));
    }

    builder
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .setup(|app| {
            tray::setup_tray(app.handle())?;
            if sovereign_ready() {
                if let Err(error) = start_apxv_server(None) {
                    eprintln!("APXV auto-start apxv_serve failed: {error}");
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            start_apxv_server,
            stop_apxv_server,
            get_apxv_server_status,
            start_apx_server,
            stop_apx_server,
            get_apx_server_status,
            get_default_apxv_root,
            read_operator_key,
            save_operator_key_file,
            show_main_window,
            run_bootstrap,
            get_bootstrap_status,
        ])
        .build(tauri::generate_context!())
        .expect("error while running APXV")
        .run(|app, event| {
            tray::handle_run_event(app, &event);
        });
}