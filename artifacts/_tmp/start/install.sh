#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# NYXUS Start — sub-app installer
#
# Called by the top-level nyxus_start_install.sh after the tarball is
# extracted.  Lays files into ~/.nyxus/nyxus-start/, installs Python +
# system deps, drops a launcher script, .desktop entry, and patches
# Waybar config (config + style) to add Start + Panel buttons.
#
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

B=$'\e[1m'; R=$'\e[0m'; PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'; DIM=$'\e[2m'

step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

# ── resolve real user (script may run as root via sudo)
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"
[[ -z "$REAL_HOME" || ! -d "$REAL_HOME" ]] && REAL_HOME="$HOME"

INSTALL_DIR="${REAL_HOME}/.nyxus/nyxus-start"
BIN_DIR="${REAL_HOME}/.local/bin"
APP_DIR="${REAL_HOME}/.local/share/applications"
WAYBAR_DIR="${REAL_HOME}/.config/waybar"

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

step "preflight"
for cmd in python3 install; do
  command -v "$cmd" >/dev/null || { fail "$cmd not found"; exit 1; }
done
ok "python3 / install present"

# ── system packages
step "system packages (pacman)"
if command -v pacman >/dev/null; then
  pacman -S --noconfirm --needed \
    gtk4 python-gobject python-cairo python-psutil \
    2>/dev/null \
    && ok "gtk4 / python-gobject / python-cairo / psutil" \
    || warn "pacman: some core packages failed (re-run: sudo pacman -S gtk4 python-gobject python-psutil)"

  pacman -S --noconfirm --needed gtk4-layer-shell 2>/dev/null \
    && ok "gtk4-layer-shell (Start anchors above taskbar)" \
    || warn "gtk4-layer-shell missing — falls back to centered floating window"

  pacman -S --noconfirm --needed jq 2>/dev/null \
    && ok "jq (used to patch Waybar config safely)" \
    || warn "jq missing — Waybar config patching may be skipped"
else
  warn "pacman not found — install GTK4 + python-gobject manually"
fi

# ── lay down files
step "deploy files → ${INSTALL_DIR}"
install -d -o "$REAL_USER" "${INSTALL_DIR}" "${BIN_DIR}" "${APP_DIR}" \
        "${REAL_HOME}/.config/nyxus-start" "${REAL_HOME}/.cache/nyxus-start"
cp -r "${SRC_DIR}/nyxus-start/." "${INSTALL_DIR}/"
chown -R "$REAL_USER":"$REAL_USER" "${INSTALL_DIR}"
chmod -R u+rw,go+r "${INSTALL_DIR}"
ok "deployed $(find "${INSTALL_DIR}" -maxdepth 1 -type f | wc -l) files"

# ── launcher script
# IMPORTANT: nyxus-start uses gtk4-layer-shell. On many Arch builds the
# dynamic loader brings libwayland-client in BEFORE libgtk4-layer-shell,
# which breaks LayerShell with the famous warning:
#     "GTK4 Layer Shell may have been linked after libwayland.
#      You may be able to fix … by setting LD_PRELOAD=…"
# Result: the Start window opens as a plain floating window with no
# anchoring — looks like nothing changed. We auto-detect the library via
# ldconfig and prepend it to LD_PRELOAD inside the launcher itself, so
# every invocation gets the fix without polluting the user's shell env.
step "launcher script"
cat > "${BIN_DIR}/nyxus-start" <<EOF
#!/usr/bin/env bash
# NYXUS Start launcher (auto LayerShell preload)
NYX_LAYER_LIB="\$(ldconfig -p 2>/dev/null | awk '/libgtk4-layer-shell\\.so/ {print \$NF; exit}')"
if [[ -n "\$NYX_LAYER_LIB" && -f "\$NYX_LAYER_LIB" ]]; then
  export LD_PRELOAD="\${NYX_LAYER_LIB}\${LD_PRELOAD:+:\$LD_PRELOAD}"
fi
exec python3 "${INSTALL_DIR}/main.py" "\$@"
EOF
chmod +x "${BIN_DIR}/nyxus-start"
chown "$REAL_USER":"$REAL_USER" "${BIN_DIR}/nyxus-start"
ok "${BIN_DIR}/nyxus-start (with LayerShell LD_PRELOAD)"

# ── waybar state helper (emits JSON for the custom modules)
install -m 0755 -o "$REAL_USER" -g "$REAL_USER" \
        "${SRC_DIR}/nyxus-waybar-state" "${BIN_DIR}/nyxus-waybar-state"
ok "${BIN_DIR}/nyxus-waybar-state"

# ── NYXUS App Store (discovery + one-click install for the NYXUS suite).
step "NYXUS App Store"
STORE_INSTALL_DIR="${REAL_HOME}/.local/share/nyxus-store"
install -d -o "$REAL_USER" -g "$REAL_USER" "$STORE_INSTALL_DIR"
if [[ -d "${SRC_DIR}/nyxus-store" ]]; then
  cp -r "${SRC_DIR}/nyxus-store/." "${STORE_INSTALL_DIR}/"
  chown -R "$REAL_USER":"$REAL_USER" "$STORE_INSTALL_DIR"
  chmod -R u+rw,go+r "$STORE_INSTALL_DIR"

  cat > "${BIN_DIR}/nyxus-store" <<EOF
#!/usr/bin/env bash
exec python3 "${STORE_INSTALL_DIR}/main.py" "\$@"
EOF
  chmod +x "${BIN_DIR}/nyxus-store"
  chown "$REAL_USER":"$REAL_USER" "${BIN_DIR}/nyxus-store"
  ok "${BIN_DIR}/nyxus-store"

  # .desktop file so the Start menu app-grid + every other launcher (rofi,
  # gnome-shell, xfce, etc.) finds it.
  cat > "${APP_DIR}/io.nyxus.store.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=NYXUS App Store
GenericName=Software Center
Comment=Discover and install NYXUS sub-apps
Exec=${BIN_DIR}/nyxus-store
Icon=io.nyxus.store
Terminal=false
Categories=System;Settings;PackageManager;
StartupNotify=true
EOF
  chown "$REAL_USER":"$REAL_USER" "${APP_DIR}/io.nyxus.store.desktop"
  ok "${APP_DIR}/io.nyxus.store.desktop"
else
  warn "nyxus-store/main.py not bundled — App Store launcher skipped"
fi

# ── Notifications flyout (real GTK4 LayerShell window — no longer a stub).
# Deploys nyxus-notifications/main.py alongside the start install dir, then
# writes ${BIN_DIR}/nyxus-notifications as a thin python launcher (matches
# the nyxus-start pattern). The launcher is OVERWRITTEN unconditionally on
# every install so the old "Coming soon" notify-send stub gets upgraded.
step "notifications flyout"
NOTIF_INSTALL_DIR="${REAL_HOME}/.local/share/nyxus-notifications"
install -d -o "$REAL_USER" -g "$REAL_USER" "$NOTIF_INSTALL_DIR"
if [[ -d "${SRC_DIR}/nyxus-notifications" ]]; then
  cp -r "${SRC_DIR}/nyxus-notifications/." "${NOTIF_INSTALL_DIR}/"
  chown -R "$REAL_USER":"$REAL_USER" "$NOTIF_INSTALL_DIR"
  chmod -R u+rw,go+r "$NOTIF_INSTALL_DIR"

  # Notifications also uses gtk4-layer-shell — same LD_PRELOAD shim as nyxus-start.
  cat > "${BIN_DIR}/nyxus-notifications" <<EOF
#!/usr/bin/env bash
# NYXUS Notifications launcher (auto LayerShell preload)
NYX_LAYER_LIB="\$(ldconfig -p 2>/dev/null | awk '/libgtk4-layer-shell\\.so/ {print \$NF; exit}')"
if [[ -n "\$NYX_LAYER_LIB" && -f "\$NYX_LAYER_LIB" ]]; then
  export LD_PRELOAD="\${NYX_LAYER_LIB}\${LD_PRELOAD:+:\$LD_PRELOAD}"
fi
exec python3 "${NOTIF_INSTALL_DIR}/main.py" "\$@"
EOF
  chmod +x "${BIN_DIR}/nyxus-notifications"
  chown "$REAL_USER":"$REAL_USER" "${BIN_DIR}/nyxus-notifications"
  ok "${BIN_DIR}/nyxus-notifications (real GTK4 flyout, LayerShell preload)"
else
  warn "nyxus-notifications/main.py not bundled — falling back to notify-send stub"
  cat > "${BIN_DIR}/nyxus-notifications" <<'STUB'
#!/usr/bin/env bash
command -v notify-send >/dev/null 2>&1 && \
  notify-send -a 'NYXUS' 'NYXUS · Notifications' 'Flyout payload missing from this build.'
exit 0
STUB
  chmod +x "${BIN_DIR}/nyxus-notifications"
  chown "$REAL_USER":"$REAL_USER" "${BIN_DIR}/nyxus-notifications"
fi

# ── handwritten font (Inter) — required for the Start/Panel button text.
# Drop into the user's font dir (no root needed) so it's available system-wide
# for fontconfig consumers like Waybar/Pango. fc-cache rebuilds the index.
step "fonts (Inter — handwritten button labels)"
FONT_DIR="${REAL_HOME}/.local/share/fonts/nyxus"
install -d -o "$REAL_USER" -g "$REAL_USER" "$FONT_DIR"
if [[ -f "${SRC_DIR}/fonts/Inter.ttf" ]]; then
  install -m 0644 -o "$REAL_USER" -g "$REAL_USER" \
          "${SRC_DIR}/fonts/Inter.ttf" "${FONT_DIR}/Inter.ttf"
  install -m 0644 -o "$REAL_USER" -g "$REAL_USER" \
          "${SRC_DIR}/fonts/OFL.txt" "${FONT_DIR}/OFL.txt"
  if command -v fc-cache >/dev/null; then
    # Rebuild the user font cache (verbose so we can see real failures), then
    # VERIFY fontconfig actually sees Inter — silent fc-cache failures were
    # the prior root cause of the menus rendering in the system default font.
    if sudo -u "$REAL_USER" fc-cache -f -v "${REAL_HOME}/.local/share/fonts" >/dev/null 2>&1; then
      if sudo -u "$REAL_USER" fc-list | grep -qi 'Inter'; then
        ok "Inter installed and registered with fontconfig"
      else
        warn "Inter copied but fontconfig still does NOT see it — try: fc-cache -frv ; or relog."
      fi
    else
      warn "fc-cache returned non-zero; running 'fc-cache -frv' to recover"
      sudo -u "$REAL_USER" fc-cache -frv "${REAL_HOME}/.local/share/fonts" >/dev/null 2>&1 || true
      sudo -u "$REAL_USER" fc-list | grep -qi 'Inter' \
        && ok "Inter registered after recovery" \
        || warn "Inter still missing from fc-list — handwritten font will not render."
    fi
  else
    warn "fc-cache missing — install package 'fontconfig' then re-run this installer."
  fi
else
  warn "Inter.ttf not bundled — handwritten button text will fall back"
fi

# ── kill any running flyouts so the next click loads the fresh CSS / .py code
# (otherwise users see stale rendering and assume the install didn't work).
sudo -u "$REAL_USER" pkill -f 'nyxus-(start|panel|notifications)/main\.py' 2>/dev/null || true

# ── .desktop file
cat > "${APP_DIR}/io.nyxus.start.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=NYXUS Start
GenericName=Start Menu Flyout
Comment=Left-side flyout — search · pinned apps · recent · power
Exec=${BIN_DIR}/nyxus-start
Icon=io.nyxus.start
Terminal=false
Categories=Utility;System;
StartupNotify=false
EOF
chown "$REAL_USER":"$REAL_USER" "${APP_DIR}/io.nyxus.start.desktop"
ok ".desktop entry"

sudo -u "$REAL_USER" update-desktop-database "${APP_DIR}" 2>/dev/null || true

# ──────────────────────────────────────────────────────────────────────
# Waybar integration — add Start (left) + Panel (right) buttons
# ──────────────────────────────────────────────────────────────────────
step "waybar integration"

WAYBAR_CFG="${WAYBAR_DIR}/config"
WAYBAR_CSS="${WAYBAR_DIR}/style.css"

if [[ -f "$WAYBAR_CFG" ]] && command -v jq >/dev/null; then
  cp "$WAYBAR_CFG" "${WAYBAR_CFG}.bak.nyxus-start.$(date +%s)"

  # The patcher must work whether the config is a single object OR an array
  # of bar definitions. We branch on .type and apply the same patch to either
  # the lone object (when its .position is "bottom") or every "bottom" element
  # of an array. Empty `.position` defaults to "bottom" in Waybar, so we treat
  # missing/null .position as "bottom" too.
  # The patch:
  #   • Replaces both buttons with exec-driven custom modules — they get
  #     their text + open/closed class from `nyxus-waybar-state`. The label
  #     is hand-drawn (Inter) Pango markup; the glow is in style.css.
  #   • Drops the legacy rofi "custom/start" entry entirely (key + module
  #     references) — the new Start button's search bar replaces Rofi.
  #   • Pins custom/nyxus-start as the FIRST left module and custom/nyxus-panel
  #     as the LAST right module.
  PATCH_EXPR='
    def patch_bar:
      .["custom/nyxus-start"] = {
        "exec":        ($helper + " start"),
        "interval":    1,
        "return-type": "json",
        "format":      "{}",
        "escape":      false,
        "tooltip":     true,
        "on-click":    $launcher_start
      }
      | .["custom/nyxus-panel"] = {
          "exec":        ($helper + " panel"),
          "interval":    1,
          "return-type": "json",
          "format":      "{}",
          "escape":      false,
          "tooltip":     true,
          "on-click":    $launcher_panel
        }
      | .["custom/nyxus-notifications"] = {
          "exec":        ($helper + " notifications"),
          "interval":    1,
          "return-type": "json",
          "format":      "{}",
          "escape":      false,
          "tooltip":     true,
          "on-click":    $launcher_notifications
        }
      | .["custom/nyxus-settings"] = {
          "format":      "\uf013",
          "tooltip":     "NYXUS Settings",
          "on-click":    $launcher_settings
        }
      # Drop the legacy rofi entry entirely
      | del(.["custom/start"])
      | ."modules-left" =
          ( ["custom/nyxus-start"] +
            ((."modules-left" // [])
              | map(select(. != "custom/nyxus-start"
                       and  . != "custom/start"
                       and  (. | startswith("clock") | not)))) )
      | ."modules-right" =
          ( ((."modules-right" // [])
              | map(select(. != "custom/nyxus-panel"
                       and  . != "custom/nyxus-notifications"
                       and  . != "custom/nyxus-settings"
                       and  . != "custom/start"
                       and  (. | startswith("clock") | not)))) +
            ["custom/nyxus-settings", "custom/nyxus-panel", "custom/nyxus-notifications"] )
      # Bottom bar must NOT show ANY clock variant (clock, clock#main, etc.)
      | ."modules-center" =
          ((."modules-center" // []) | map(select(. | startswith("clock") | not)));

    # ── Clock relocation ────────────────────────────────────────────────
    # User wants the date/clock module on the TOP bar (right side), not the
    # bottom bar. We strip "clock" from every module list on the bottom bar
    # in patch_bar above, and append it to the END of modules-right on the
    # top bar here. Idempotent: if "clock" already appears on the top bar
    # we leave it alone instead of duplicating.
    def is_top:    (.position == "top");
    def is_bottom: (.position == "bottom") or (.position == null) or (.position == "");

    def relocate_clock_to_top:
      ."modules-right" =
        ( if ((."modules-right" // []) | any(. == "clock"))
          then (."modules-right" // [])
          else ((."modules-right" // []) + ["clock"])
          end );

    def patch_top:
      relocate_clock_to_top;

    # ── Top-only fallback ────────────────────────────────────────────────
    # Many users (NyxOS default included) ship Waybar with ONLY a top bar —
    # no `position: "bottom"` entry exists. The CSS for the NYXUS chrome
    # buttons is position-agnostic (`window#waybar #custom-nyxus-start`),
    # so when no bottom bar is present we apply patch_bar to the TOP bar
    # instead. This adds Start/Panel/Notifications/Settings to the only
    # bar the user has, instead of silently doing nothing.
    # IMPORTANT: this whole expression is wrapped in bash single quotes
    # (PATCH_EXPR=...). Do NOT use ASCII apostrophes in comments here —
    # they close the bash string and break the jq script. Use plain words
    # like "doing nothing" instead of "no-op-ing".
    def has_bottom:
      if type == "array" then
        any(.[]; .position == "bottom"
                 or .position == null
                 or .position == "")
      else
        is_bottom
      end;

    def patch_one(top_only):
      if is_bottom         then patch_bar
      elif is_top and top_only then patch_bar
      elif is_top          then patch_top
      else .
      end;

    . as $root
    | (has_bottom | not) as $top_only
    | if type == "array" then
        $root | map(patch_one($top_only))
      elif type == "object" then
        $root | patch_one($top_only)
      else
        $root
      end
  '

  if sudo -u "$REAL_USER" jq \
       --arg launcher_start         "${BIN_DIR}/nyxus-start" \
       --arg launcher_panel         "${BIN_DIR}/nyxus-panel" \
       --arg launcher_notifications "${BIN_DIR}/nyxus-notifications" \
       --arg launcher_settings      "${BIN_DIR}/nyxus-settings" \
       --arg helper                 "${BIN_DIR}/nyxus-waybar-state" \
       "$PATCH_EXPR" "$WAYBAR_CFG" > "${WAYBAR_CFG}.tmp"; then
    mv "${WAYBAR_CFG}.tmp" "$WAYBAR_CFG"
    chown "$REAL_USER":"$REAL_USER" "$WAYBAR_CFG"
    ok "patched ${WAYBAR_CFG} (Start far-left, Panel + Notifications far-right)"
  else
    rm -f "${WAYBAR_CFG}.tmp"
    warn "jq patch failed — original config unchanged. See waybar_additions.json to merge by hand."
  fi
else
  warn "Waybar config not found OR jq missing — see waybar_additions.json"
fi

# Replace the NYXUS-managed CSS block in Waybar's style.css (upgrade-safe).
# The shipped waybar_styles.css is wrapped in BEGIN/END markers; we delete any
# existing managed block AND any legacy sentinel-only block from prior
# installs, then append the freshest version. This way users who already have
# an older Start/Panel-only block automatically get the new Notifications
# rules too.
#
# The previous (sed-based) implementation had a bug where it would delete
# from the sentinel line forward but leave the `/* ────...` comment opener
# one line above it stranded — producing an unterminated comment that broke
# Waybar's CSS loader on startup. The Python implementation below walks the
# parse tree of comment headers properly so it can never leave an orphan.
if [[ -f "$WAYBAR_CSS" ]]; then
  if python3 - "$WAYBAR_CSS" "${SRC_DIR}/waybar_styles.css" <<'PY'
import sys, re

css_path, block_path = sys.argv[1], sys.argv[2]
text = open(css_path).read()

# 1. Strip any well-formed managed block(s) we previously inserted.
text = re.sub(
    r'/\*\s*>>>\s*NYXUS-WAYBAR-MANAGED-BLOCK BEGIN.*?'
    r'NYXUS-WAYBAR-MANAGED-BLOCK END\s*<<<\s*\*/\s*',
    '', text, flags=re.DOTALL,
)

# 2. Strip the legacy NYXUS-START-BUTTON-STYLE block. Find the sentinel,
#    then walk backwards to the START of its comment-header line — that
#    header is "/* ────..." (just box-drawing dashes after the opener,
#    no closing */ on the same line). Chop from there to EOF.
m = re.search(r'NYXUS-START-BUTTON-STYLE', text)
if m:
    head_re = re.compile(r'(?m)^\s*/\*[\s\u2500\-=\*]*$')
    last_header_start = None
    for h in head_re.finditer(text, 0, m.start()):
        last_header_start = h.start()
    if last_header_start is None:
        # Fallback: nearest /* before the sentinel, then to start-of-line.
        opener = text.rfind('/*', 0, m.start())
        if opener >= 0:
            last_header_start = text.rfind('\n', 0, opener) + 1
    if last_header_start is not None:
        text = text[:last_header_start]

# 3. Defence-in-depth: pop trailing blank lines and any final unterminated
#    "/* ────" opener lines so the file never ends mid-comment.
lines = text.rstrip().splitlines()
while lines:
    last = lines[-1].strip()
    if last == '' or (last.startswith('/*') and '*/' not in last):
        lines.pop()
    else:
        break
text = '\n'.join(lines).rstrip() + '\n\n'

# 4. Append the fresh, marker-wrapped managed block.
text += open(block_path).read().rstrip() + '\n'

# 5. Sanity check: equal /* and */ counts.
opens, closes = text.count('/*'), text.count('*/')
if opens != closes:
    sys.stderr.write(
        f'NYXUS CSS merge refused — comment braces unbalanced '
        f'(opens={opens}, closes={closes}). Aborting to avoid breaking Waybar.\n'
    )
    sys.exit(1)

open(css_path, 'w').write(text)
PY
  then
    chown "$REAL_USER":"$REAL_USER" "$WAYBAR_CSS"
    ok "refreshed NYXUS Waybar CSS block in ${WAYBAR_CSS}"
  else
    warn "NYXUS CSS merge refused (see message above) — original file untouched."
  fi
else
  warn "Waybar style.css missing — see waybar_styles.css"
fi

# ── Pins migration ──────────────────────────────────────────────────
# settings.py only seeds DEFAULT_PINS when pins.json is *missing*. Anyone
# who installed NYXUS Start before the App Store existed therefore has a
# pins.json that doesn't include "nyxus-store" — so the new launcher tile
# never appears in the Pinned grid. We migrate in-place: read the existing
# JSON, prepend "nyxus-store" if absent, write atomically. Idempotent.
step "Migrating pinned-apps list"
PINS_FILE="${REAL_HOME}/.config/nyxus-start/pins.json"
if [[ -f "$PINS_FILE" ]]; then
  if sudo -u "$REAL_USER" python3 - "$PINS_FILE" <<'PY'
import json, sys, os, tempfile
path = sys.argv[1]
try:
    with open(path) as f:
        pins = json.load(f)
except Exception:
    sys.exit(0)  # leave alone if unreadable
if not isinstance(pins, list):
    sys.exit(0)
changed = False
for needed in ("nyxus-store",):
    if needed not in pins:
        pins.insert(0, needed)
        changed = True
if changed:
    fd, tmp = tempfile.mkstemp(prefix=".pins.", dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f:
        json.dump(pins, f, indent=2)
    os.replace(tmp, path)
    print("migrated")
PY
  then
    ok "${PINS_FILE} (added nyxus-store if missing)"
  else
    warn "could not migrate ${PINS_FILE} — open NYXUS Start ▸ Edit pins to add nyxus-store"
  fi
else
  ok "no existing pins.json — defaults will include nyxus-store on first launch"
fi

# ── Force-restart NYXUS GTK helpers ─────────────────────────────────
# Without this, an old running nyxus-start / nyxus-panel / nyxus-notifications
# process holds the previous code in memory — so re-running install.sh appears
# to "do nothing" because the user's open flyout still uses old code (no
# calendar, old CSS, no App Store pin). We kill them; the waybar buttons will
# spawn fresh ones on next click.
if command -v pkill >/dev/null; then
  for proc in nyxus-start nyxus-panel nyxus-notifications nyxus-store; do
    sudo -u "$REAL_USER" pkill -f "${proc}/main.py" 2>/dev/null || true
    sudo -u "$REAL_USER" pkill -x "$proc"             2>/dev/null || true
  done
  ok "killed any running NYXUS GTK helpers (next launch picks up new code)"
fi

# Restart waybar so changes take effect
if command -v pkill >/dev/null; then
  sudo -u "$REAL_USER" pkill -SIGUSR2 waybar 2>/dev/null \
    && ok "waybar reloaded (SIGUSR2)" \
    || warn "waybar not running — restart it manually to see the buttons"
fi

cat <<EOF

──────────────────────────────────────────────────────────────────────
${B}NYXUS Start installed.${R}

${B}launch:${R}    ${GOLD}nyxus-start${R}                  ${DIM}(toggles open / close)${R}
${B}pinned:${R}    ${REAL_HOME}/.config/nyxus-start/pins.json
${B}recent:${R}    ${REAL_HOME}/.config/nyxus-start/recent.json
${B}config:${R}    ${REAL_HOME}/.config/nyxus-start/config.json
${B}install:${R}   ${INSTALL_DIR}

${B}waybar:${R}    Start button is now on the FAR LEFT,
           Panel button is on the FAR RIGHT.
──────────────────────────────────────────────────────────────────────
EOF
