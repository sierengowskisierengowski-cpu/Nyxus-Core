# Arsenal — GowskiNet Security Hub

One roof for the whole toolkit. A clean, btop-style TUI that lists every tool,
shows which ones are live, and launches any of them with a keypress.

## Launch

- Command:   `arsenal`
- App menu:  search **Arsenal** (rofi / launcher) — opens in kitty, pinnable
- Suggested keybind (add to Hyprland `~/.config/hypr/*.conf`):
  `bind = SUPER CTRL, A, exec, kitty --title Arsenal -e arsenal`
  (or Qtile: `Key([mod, "control"], "a", lazy.spawn("kitty -e arsenal"))`)

## Keys

| key | action |
|-----|--------|
| `j` / `k` or arrows | move selection |
| `Enter` | launch the selected tool |
| `r` | refresh live status |
| `q` / `Esc` | quit |

Status auto-refreshes every 5s. `●` green = running, `●` red = stopped,
`○` yellow = unknown, `•` grey = on-demand (no long-running service).

## Layout

```
Arsenal/
├── hub/            the TUI app (Rust + ratatui)
│   └── target/release/arsenal-hub   the compiled binary
├── tools/          symlinks to each real tool (NOT copies — originals stay put)
├── registry.toml   the tool list the hub reads at runtime
└── README.md
```

## Adding / editing a tool

Edit `registry.toml` — add a `[[tool]]` block. No recompile needed; the hub
reads it fresh each launch. Fields: `id, name, desc, category (defense|offense|
ai|infra), interface (service|webapp|web|cli), path, launch, status`.

`status` options: `service_system=<unit>`, `service_user=<unit>`,
`docker=<name>`, `web=<url>`, or `none`.

## Note on the symlinks

`tools/` contains **symlinks**, not copies. The real projects stay at their
canonical paths (e.g. `~/Projects/jeTT`, `~/GowskiNet-Vault/Security/*`) because
several are wired into systemd services and must not move. Arsenal is the
front door, not a new home for the code.
