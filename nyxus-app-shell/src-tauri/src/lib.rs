// ─────────────────────────────────────────────────────────────────────────
// NYXUS App Shell — turns a NYXUS web tool into a real native desktop app.
// One binary, driven by an app id (argv[1] or $NYXUS_APP). On launch it makes
// sure the tool's web server is up (starting it if needed), then loads it in a
// native window. Each .desktop launcher passes a different id → separate app,
// separate icon, separate window/workspace.
// © 2026 JOSEPH A. SIERENGOWSKI
// ─────────────────────────────────────────────────────────────────────────
use std::net::{TcpStream, ToSocketAddrs};
use std::process::Command;
use std::time::{Duration, Instant};
use tauri::Manager;

#[derive(Clone, Copy)]
struct AppDef {
    id: &'static str,
    title: &'static str,
    port: u16,
    /// Shell command that brings the tool's web server up (idempotent — a no-op
    /// if it's already running). `nyxus-webapp <slug>` starts UI + API.
    start: &'static str,
}

// The NYXUS tool roster. Add a line here + a .desktop launcher = a new app.
const APPS: &[AppDef] = &[
    AppDef { id: "cipher",   title: "CIPHER",                   port: 23051, start: "nyxus-webapp cipher" },
    AppDef { id: "forge",    title: "Forge",                    port: 23052, start: "nyxus-webapp forge" },
    AppDef { id: "redforge", title: "RedForge",                 port: 23053, start: "nyxus-webapp redforge" },
    AppDef { id: "gsl",      title: "GSL",                      port: 23054, start: "nyxus-webapp gsl" },
    AppDef { id: "trainer",  title: "AI Cyber Defense Trainer", port: 23055, start: "nyxus-webapp trainer" },
    AppDef { id: "axiom",    title: "AXIOM",                    port: 23056, start: "nyxus-webapp axiom" },
];

fn port_up(port: u16) -> bool {
    let addr = format!("127.0.0.1:{port}");
    match addr.to_socket_addrs() {
        Ok(mut it) => match it.next() {
            Some(sa) => TcpStream::connect_timeout(&sa, Duration::from_millis(400)).is_ok(),
            None => false,
        },
        Err(_) => false,
    }
}

fn resolve_app() -> AppDef {
    let id = std::env::args()
        .nth(1)
        .or_else(|| std::env::var("NYXUS_APP").ok())
        .unwrap_or_else(|| "cipher".to_string())
        .to_lowercase();
    APPS.iter().copied().find(|a| a.id == id).unwrap_or(APPS[0])
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app_def = resolve_app();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            let handle = app.handle().clone();
            let def = app_def;

            // Bring the server up + swap the splash for the real UI off the main
            // thread, so the loading window paints instantly.
            std::thread::spawn(move || {
                if !port_up(def.port) {
                    let _ = Command::new("sh").arg("-lc").arg(def.start).spawn();
                }
                // Wait up to 90s (a cold first start can npm/build) for the port.
                let deadline = Instant::now() + Duration::from_secs(90);
                while Instant::now() < deadline && !port_up(def.port) {
                    std::thread::sleep(Duration::from_millis(500));
                }

                if let Some(win) = handle.get_webview_window("main") {
                    let _ = win.set_title(def.title);
                    if port_up(def.port) {
                        let url = format!("http://localhost:{}/", def.port);
                        let _ = win.eval(&format!("window.location.replace('{}')", url));
                    } else {
                        // Server never came up — show a readable failure instead
                        // of an eternal spinner.
                        let msg = format!(
                            "NYXUS · {} could not start its service on port {}. \
                             Open a terminal and run:  nyxus-webapp {}",
                            def.title, def.port, def.id
                        );
                        let _ = win.eval(&format!(
                            "document.querySelector('.sub').textContent = {:?}; \
                             document.querySelector('.ring').style.borderTopColor = '#ff2dad';",
                            msg
                        ));
                    }
                }
            });

            // Set the window title up-front too (title-based splash label).
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.set_title(app_def.title);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running nyxus-app-shell");
}
