use tauri::{
  menu::{Menu, MenuItem},
  tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
  Manager, WindowEvent,
};
use tauri_plugin_notification::NotificationExt;

#[tauri::command]
fn send_native_toast(app: tauri::AppHandle, title: String, body: String) -> Result<(), String> {
  let _ = app.notification()
    .builder()
    .title(&title)
    .body(&body)
    .show();

  #[cfg(target_os = "windows")]
  {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x08000000;

    let escaped_title = title.replace('\'', "''").replace('"', "`\"");
    let escaped_body = body.replace('\'', "''").replace('"', "`\"");

    let ps_script = format!(
      "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null; $xml = New-Object Windows.Data.Xml.Dom.XmlDocument; $xml.LoadXml(\"<toast><visual><binding template='ToastGeneric'><text>{}</text><text>{}</text></binding></visual></toast>\"); $t = New-Object Windows.UI.Notifications.ToastNotification $xml; try {{ [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('com.slms.dashboard').Show($t) }} catch {{ [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe').Show($t) }}",
      escaped_title, escaped_body
    );

    let _ = std::process::Command::new("powershell")
      .args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", &ps_script])
      .creation_flags(CREATE_NO_WINDOW)
      .spawn();
  }

  Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_notification::init())
    .invoke_handler(tauri::generate_handler![send_native_toast])
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      // Build system tray menu
      let show_item = MenuItem::with_id(app, "show", "Show Dashboard", true, None::<&str>)?;
      let quit_item = MenuItem::with_id(app, "quit", "Quit SLMS Host", true, None::<&str>)?;
      let menu = Menu::with_items(app, &[&show_item, &quit_item])?;

      // Create System Tray
      if let Some(icon) = app.default_window_icon() {
        let _tray = TrayIconBuilder::new()
          .icon(icon.clone())
          .menu(&menu)
          .show_menu_on_left_click(false)
          .tooltip("Smart Lab Management System Host")
          .on_menu_event(|app_handle, event| match event.id.as_ref() {
            "show" => {
              if let Some(window) = app_handle.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
              }
            }
            "quit" => {
              app_handle.exit(0);
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
              let app_handle = tray.app_handle();
              if let Some(window) = app_handle.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
              }
            }
          })
          .build(app)?;
      }

      Ok(())
    })
    .on_window_event(|window, event| {
      if let WindowEvent::CloseRequested { api, .. } = event {
        api.prevent_close();
        let _ = window.hide();
      }
    })
    .run(tauri::generate_context!())
    .expect("error while building tauri application");
}
