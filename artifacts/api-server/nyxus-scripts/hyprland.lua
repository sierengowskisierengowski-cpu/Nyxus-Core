-- NYXUS Window Rules (Hyprland 0.55 Lua)
-- © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

-- Float all windows by default
hl.window_rule({ match = { class = ".*" }, float = true })

-- NYXUS app rules
hl.window_rule({ match = { class = "[Nn]yxus.*" }, center = true, size = {960, 680}, opacity = "0.92 override 0.78 override" })
hl.window_rule({ match = { class = "(io|org|app)\\.nyxus\\..*" }, center = true, size = {960, 680}, opacity = "0.92 override 0.78 override" })
hl.window_rule({ match = { class = "godsapp|intel|notepad|notes|passwords|phantom|sage|shield|start|store|studio|weather" }, center = true, size = {960, 680}, opacity = "0.92 override 0.78 override" })
hl.window_rule({ match = { class = "panel|nyxus-panel" }, pin = true, size = {460, 680}, opacity = "0.92 override 0.78 override" })
hl.window_rule({ match = { class = ".*nyxus\\.(sysmon|control|terminal|settings|security|wallpaperstudio)" }, size = {1280, 800} })
hl.window_rule({ match = { class = ".*nyxus\\.(store|files|updater)" }, size = {1240, 820} })
hl.window_rule({ match = { class = ".*nyxus\\.(backup|drop)" }, size = {1040, 720} })
hl.window_rule({ match = { class = ".*nyxus\\.(screenshot|doctor)" }, size = {980, 700} })
hl.window_rule({ match = { class = ".*nyxus\\.(notepad|notes|clipboard)" }, size = {920, 640} })
hl.window_rule({ match = { class = ".*nyxus\\.(launcher|powermenu)" }, size = {760, 540} })
hl.window_rule({ match = { class = ".*nyxus\\.weather" }, size = {380, 560}, pin = true, move = {20, 100} })
-- NYXUS Layer Rules (Hyprland 0.55 Lua)
-- © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

hl.layer_rule({ match = { namespace = "nyxus-bar-bottom" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "nyxus-bar-top" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "nyxus-bar-left" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "nyxus-bar-right" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "nyxus-dashboard" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "nyxus-powermenu" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "nyxus-notifications" }, blur = true, animation = "slide" })
hl.layer_rule({ match = { namespace = "nyxus-quicksettings" }, blur = true, animation = "slide" })
hl.layer_rule({ match = { namespace = "notifications" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "rofi" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "wofi" }, blur = true, ignore_alpha = 0.2 })
hl.layer_rule({ match = { namespace = "nyxus-fog" }, no_anim = true, blur = false })
