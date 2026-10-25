/**
 * Native Notification Service for SLMS Desktop & Web Dashboard.
 *
 * Dispatches native Windows 10/11 Toast Notifications via Tauri plugin when running
 * in the desktop shell, with seamless fallback to the browser Notification API.
 */

let tauriNotification = null;
let permissionGranted = false;

// Attempt to load Tauri notification plugin dynamically
async function getTauriNotification() {
  if (tauriNotification !== null) {
    return tauriNotification;
  }

  try {
    // Check if running inside Tauri environment
    if (window.__TAURI_INTERNALS__ || window.__TAURI__) {
      const plugin = await import("@tauri-apps/plugin-notification");
      tauriNotification = plugin;
      return tauriNotification;
    }
  } catch (err) {
    console.debug("Tauri notification plugin not available in web mode:", err);
  }

  tauriNotification = false;
  return false;
}

/**
 * Request notification permission from the operating system / browser.
 * Safe to call on application initialization.
 */
export async function initNotificationPermissions() {
  try {
    const tauri = await getTauriNotification();
    if (tauri) {
      let granted = await tauri.isPermissionGranted();
      if (!granted) {
        const permission = await tauri.requestPermission();
        granted = permission === "granted";
      }
      permissionGranted = granted;
      return granted;
    }

    // Web Browser fallback
    if ("Notification" in window) {
      if (Notification.permission === "granted") {
        permissionGranted = true;
        return true;
      }
      if (Notification.permission !== "denied") {
        const result = await Notification.requestPermission();
        permissionGranted = result === "granted";
        return permissionGranted;
      }
    }
  } catch (err) {
    console.warn("Failed to request notification permission:", err);
  }

  return false;
}

/**
 * Dispatch a native Windows / OS notification banner.
 *
 * @param {Object} options
 * @param {string} options.title - Notification header (e.g. "⚠️ High RAM Alert")
 * @param {string} options.body - Alert details / explanation
 * @param {string} [options.severity="info"] - 'critical' | 'warning' | 'info'
 * @param {string} [options.computer] - Hostname of affected computer
 */
export async function sendNativeNotification({ title, body, severity = "info", computer = "" }) {
  try {
    const tauri = await getTauriNotification();

    // Format title with severity indicator
    let prefix = "ℹ️ SLMS";
    if (severity === "critical") {
      prefix = "🚨 SLMS Critical Alert";
    } else if (severity === "warning") {
      prefix = "⚠️ SLMS Warning";
    }

    const fullTitle = title || (computer ? `${prefix} - ${computer}` : prefix);
    const fullBody = computer && !body.includes(computer) ? `[${computer}] ${body}` : body;

    // 1. Desktop Shell (Tauri -> direct native WinRT toast via Rust command)
    if (window.__TAURI_INTERNALS__ || window.__TAURI__) {
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        await invoke("send_native_toast", { title: fullTitle, body: fullBody });
        return true;
      } catch (invokeErr) {
        console.warn("Rust send_native_toast invocation failed, falling back:", invokeErr);
      }
    }

    // 2. Tauri Plugin Fallback
    if (tauri) {
      if (!permissionGranted) {
        await initNotificationPermissions();
      }
      tauri.sendNotification({
        title: fullTitle,
        body: fullBody,
      });
      return true;
    }

    // 2. Web Browser Fallback
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(fullTitle, {
        body: fullBody,
        icon: "/favicon.ico",
      });
      return true;
    }
  } catch (err) {
    console.warn("Failed to dispatch native notification:", err);
  }

  return false;
}
