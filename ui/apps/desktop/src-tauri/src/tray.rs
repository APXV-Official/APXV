use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, RunEvent,
};

use crate::server::{get_apxv_server_status, stop_apxv_server};

pub fn focus_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn tray_tooltip(_app: &AppHandle) -> String {
    match get_apxv_server_status() {
        Ok(status) if status.running => "APXV — API running".to_string(),
        Ok(_) => "APXV — API stopped".to_string(),
        Err(_) => "APXV".to_string(),
    }
}

pub fn setup_tray(app: &AppHandle) -> tauri::Result<()> {
    let open_item = MenuItem::with_id(app, "open", "Open APXV", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open_item, &quit_item])?;

    let Some(icon) = app.default_window_icon() else {
        return Ok(());
    };

    let _tray = TrayIconBuilder::new()
        .icon(icon.clone())
        .tooltip(tray_tooltip(app))
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open" => focus_main_window(app),
            "quit" => {
                let _ = stop_apxv_server();
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                focus_main_window(tray.app_handle());
            }
        })
        .build(app)?;

    Ok(())
}

pub fn handle_run_event(app: &AppHandle, event: &RunEvent) {
    if let RunEvent::ExitRequested { api, .. } = event {
        api.prevent_exit();
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.hide();
        }
    }
}