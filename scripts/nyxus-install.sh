#!/usr/bin/env bash
# ============================================================================
# NYXUS — bootstrap installer  ·  "clone → run → working system"  (Phase 8.1)
# © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
# Installs the NYXUS Hyprland desktop onto an EXISTING Arch Linux system
# (dotfiles/rice style). This is the terminal install path — distinct from the
# NYX ISO (bare-metal) path in iso-builder/.
#
#   git clone https://github.com/sierengowskisierengowski-cpu/Nyxus-Core
#   cd Nyxus-Core && ./scripts/nyxus-install.sh              # base desktop + login/session setup
#   ./scripts/nyxus-install.sh --dry-run                     # preview, no changes
#   ./scripts/nyxus-install.sh --skip-user-config            # system phase only (used by ./install.sh)
#   ./scripts/nyxus-install.sh --no-greeter                  # keep current greeter, still fix sessions/default
#   ./scripts/nyxus-install.sh --all                         # add gated extras too
#
# ORCHESTRATOR — it composes existing, tested pieces rather than duplicating:
#   configs   → scripts/nyxus-restore-desktop.sh  (hypr/eww/rofi/dunst/walls…)
#   greeter   → scripts/nyxus-setup-greetd.sh
#   kernel    → kernel/install-kage-ryu.sh        (selectable; stock default)
#   nvidia    → scripts/nyxus-fix-nvidia-suspend.sh
#   verify    → scripts/nyxus-verify-build.sh
#
# SAFETY:
#   - Runs as your normal user; elevates with sudo only for system bits.
#   - Idempotent; safe to re-run. Config phase backs up first (restore-desktop).
#   - --dry-run prints the full plan and changes NOTHING.
#   - Greeter/session repair now runs by default so one install command fully
#     deploys NYXUS. Kernel / NVIDIA / loadout remain opt-in.
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
PROFILE="${REPO_ROOT}/iso-builder/nyx-profile"

B=$'\e[1m'; R=$'\e[0m'
PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'; GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'
step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }
run()  { if $DRY; then printf "  ${GOLD}[dry-run]${R} %s\n" "$*"; else eval "$*"; fi; }

# ── options ────────────────────────────────────────────────────────────────
DRY=false; TIER=full; ASSUME_YES=false
DO_GREETER=true; DO_KERNEL=false; DO_NVIDIA=false; DO_LOADOUT=false
SKIP_USER_CONFIG=false; KEEP_LEGACY_SESSIONS=false
REAL_USER="${USER}"
REAL_HOME="${HOME}"
usage() { sed -n '2,33p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0; }
python_set_ini_key() { # python_set_ini_key <file> <section> <key> <value> <sudo:true|false>
  local file="$1" section="$2" key="$3" value="$4" use_sudo="${5:-false}" runner=(python3)
  $use_sudo && runner=(sudo python3)
  if $DRY; then
    warn "[dry-run] would set ${file} [${section}] ${key}=${value}"
    return 0
  fi
  "${runner[@]}" - "$file" "$section" "$key" "$value" <<'PY'
import pathlib, sys
path = pathlib.Path(sys.argv[1])
section, key, value = sys.argv[2:]
lines = path.read_text().splitlines() if path.exists() else []
out = []
in_section = False
section_seen = False
key_written = False
for line in lines:
    stripped = line.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        if in_section and not key_written:
            out.append(f"{key}={value}")
            key_written = True
        current = stripped[1:-1]
        in_section = current == section
        section_seen = section_seen or in_section
        out.append(line)
        continue
    if in_section and stripped.startswith(f"{key}="):
        out.append(f"{key}={value}")
        key_written = True
    else:
        out.append(line)
if not section_seen:
    if out and out[-1] != "":
        out.append("")
    out.extend([f"[{section}]", f"{key}={value}"])
elif in_section and not key_written:
    out.append(f"{key}={value}")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(out).rstrip() + "\n")
PY
}
cleanup_sessions() {
  local dirs=(/usr/share/wayland-sessions /usr/share/xsessions) dir path base removed=0 kept=0
  step "clean session entries + set NYXUS as default"
  run "sudo install -Dm755 \"${NS}/nyxus-session-start\" /usr/local/bin/nyxus-session-start"
  run "sudo install -Dm644 \"${NS}/desktop-entries/nyxus-hyprland.desktop\" /usr/share/wayland-sessions/nyxus-hyprland.desktop"
  run "install -Dm755 \"${NS}/nyxus-session-start\" \"${REAL_HOME}/.local/bin/nyxus-session-start\""
  run "install -Dm644 \"${NS}/desktop-entries/nyxus-hyprland.desktop\" \"${REAL_HOME}/.local/share/wayland-sessions/nyxus-hyprland.desktop\""
  for dir in "${dirs[@]}"; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r -d '' path; do
      base="$(basename "$path")"
      case "$base" in
        nyxus-hyprland.desktop) continue ;;
        qtile.desktop|hyprland.desktop|hyprland-*.desktop)
          if $KEEP_LEGACY_SESSIONS; then
            warn "keeping legacy session entry (requested): $path"
            kept=$((kept+1))
          else
            run "sudo rm -f \"$path\""
            removed=$((removed+1))
          fi
          ;;
      esac
    done < <(find "$dir" -maxdepth 1 -type f -name '*.desktop' -print0)
  done
  python_set_ini_key "${REAL_HOME}/.dmrc" Desktop Session nyxus-hyprland.desktop false
  if [[ -d /var/lib/AccountsService/users ]]; then
    python_set_ini_key "/var/lib/AccountsService/users/${REAL_USER}" User Session nyxus-hyprland.desktop true
  fi
  if $DRY; then
    warn "[dry-run] would install /etc/sddm.conf.d/10-nyxus-default-session.conf"
  else
    sudo mkdir -p /etc/sddm.conf.d
    cat <<EOF | sudo tee /etc/sddm.conf.d/10-nyxus-default-session.conf >/dev/null
[General]
DefaultSession=nyxus-hyprland.desktop

[Users]
RememberLastSession=false
RememberLastUser=true

[Wayland]
SessionDir=/usr/share/wayland-sessions,${REAL_HOME}/.local/share/wayland-sessions

[X11]
SessionDir=/usr/share/xsessions
EOF
  fi
  ok "NYXUS session entry installed system-wide and for ${REAL_USER}"
  if $KEEP_LEGACY_SESSIONS; then
    ok "legacy sessions preserved by request (${kept} kept)"
  else
    ok "legacy session entries removed (${removed} removed)"
  fi
}
verify_session_state() {
  local leftovers=() path
  step "session verification"
  for path in /usr/share/wayland-sessions/qtile.desktop \
              /usr/share/xsessions/qtile.desktop \
              /usr/share/wayland-sessions/hyprland.desktop \
              /usr/share/wayland-sessions/hyprland-uwsm.desktop \
              /usr/share/xsessions/hyprland.desktop; do
    [[ -e "$path" ]] && leftovers+=("$path")
  done
  if [[ -f /etc/sddm.conf.d/10-nyxus-default-session.conf ]] && grep -q '^DefaultSession=nyxus-hyprland.desktop$' /etc/sddm.conf.d/10-nyxus-default-session.conf 2>/dev/null; then
    ok "display-manager default session pinned to NYXUS (SDDM drop-in)"
  elif [[ -f "${REAL_HOME}/.dmrc" ]] && grep -q '^Session=nyxus-hyprland.desktop$' "${REAL_HOME}/.dmrc" 2>/dev/null; then
    ok "user default session pinned to NYXUS via ~/.dmrc"
  else
    warn "could not verify a persisted NYXUS default session"
  fi
  if (( ${#leftovers[@]} == 0 )); then
    ok "no stale qtile / stock Hyprland session entries remain"
  elif $KEEP_LEGACY_SESSIONS; then
    warn "legacy sessions kept by request: ${leftovers[*]}"
  else
    warn "stale session entries still present: ${leftovers[*]}"
  fi
}
for arg in "$@"; do case "$arg" in
  --dry-run)        DRY=true ;;
  --yes|-y)         ASSUME_YES=true ;;
  --lean)           TIER=lean ;;
  --full)           TIER=full ;;
  --greeter)        DO_GREETER=true ;;
  --no-greeter)     DO_GREETER=false ;;
  --kernel)         DO_KERNEL=true ;;
  --nvidia-suspend) DO_NVIDIA=true ;;
  --loadout)        DO_LOADOUT=true ;;
  --skip-user-config) SKIP_USER_CONFIG=true ;;
  --keep-legacy-sessions) KEEP_LEGACY_SESSIONS=true ;;
  --all)            DO_GREETER=true; DO_KERNEL=true; DO_NVIDIA=true; DO_LOADOUT=true ;;
  -h|--help)        usage ;;
  *) fail "unknown option: $arg (try --help)"; exit 2 ;;
esac; done

# ── 0. preflight ─────────────────────────────────────────────────────────────
step "preflight"
if [[ $EUID -eq 0 ]]; then fail "run as your normal user, not root (sudo is used where needed)"; exit 1; fi
HOST_LABEL="Arch host"
if [[ ! -f /etc/arch-release ]]; then
  if $DRY; then warn "non-Arch host detected — dry-run preview only"; else fail "this installer targets Arch Linux"; exit 1; fi
  HOST_LABEL="non-Arch preview host"
fi
[[ -d "$NS" ]] || { fail "run from a Nyxus-Core clone (missing ${NS})"; exit 1; }
if ! command -v pacman >/dev/null 2>&1; then
  if $DRY; then warn "pacman not found on this host — package preview limited"; else fail "pacman not found"; exit 1; fi
fi
PKG_LIST="${PROFILE}/packages.x86_64"; [[ "$TIER" == lean ]] && PKG_LIST="${PROFILE}/packages.x86_64.lean"
[[ -f "$PKG_LIST" ]] || { fail "package list not found: $PKG_LIST"; exit 1; }
ok "${HOST_LABEL}, running as ${USER}, tier=${TIER}$($DRY && echo ', DRY-RUN')"
ok "plan: packages + session-cleanup + verify$($SKIP_USER_CONFIG || echo ' + configs + apps')$($DO_GREETER && echo ' + greeter')$($DO_KERNEL && echo ' + kernel')$($DO_NVIDIA && echo ' + nvidia-suspend')$($DO_LOADOUT && echo ' + security-loadout')"

if ! $DRY && ! $ASSUME_YES; then
  printf "\n${B}This will install packages and place NYXUS configs on this system.${R}\n"
  read -rp "Continue? [y/N] " a; [[ "$a" =~ ^[Yy]$ ]] || { warn "aborted"; exit 0; }
fi

# ── 1. packages ──────────────────────────────────────────────────────────────
step "install packages (${TIER} tier)"
mapfile -t WANT < <(grep -vE '^\s*#|^\s*$' "$PKG_LIST" | sort -u)
INSTALLABLE=(); SKIPPED=()
if command -v pacman >/dev/null 2>&1; then
  # Filter to packages that actually exist in the enabled repos so one unknown
  # entry (e.g. a multilib pkg with multilib disabled) can't abort the whole run.
  AVAIL="$(pacman -Slq 2>/dev/null | sort -u)"
  while IFS= read -r p; do
    if grep -qxF "$p" <<<"$AVAIL"; then INSTALLABLE+=("$p"); else SKIPPED+=("$p"); fi
  done < <(printf '%s\n' "${WANT[@]}")
else
  INSTALLABLE=("${WANT[@]}")
fi
ok "${#INSTALLABLE[@]} installable / ${#WANT[@]} listed"
(( ${#SKIPPED[@]} )) && warn "skipped ${#SKIPPED[@]} not in enabled repos (enable multilib for lib32-*, or add AUR): ${SKIPPED[*]:0:8}…"
run "sudo pacman -S --needed --noconfirm ${INSTALLABLE[*]}"

# ── 2. configs (delegate — backs up + places hypr/eww/rofi/dunst/walls) ──────
step "place desktop configs"
if $SKIP_USER_CONFIG; then
  ok "skipped (handled by ./install.sh user deploy)"
elif $DRY; then
  warn "[dry-run] would run scripts/nyxus-restore-desktop.sh"
else
  bash "${SCRIPT_DIR}/nyxus-restore-desktop.sh" || warn "restore-desktop reported issues — review above"
fi

# ── 3. NYXUS app suite → ~/.nyxus + launchers ────────────────────────────────
step "install NYXUS app suite (~/.nyxus + launchers)"
if $SKIP_USER_CONFIG; then
  ok "skipped (handled by ./install.sh user deploy)"
elif ! $DRY; then
  run "mkdir -p \"\$HOME/.nyxus\" \"\$HOME/.local/bin\""
  cp "${NS}"/nyxus_*.py "${HOME}/.nyxus/" 2>/dev/null || true
  n=0
  for f in "${HOME}/.nyxus"/nyxus_*.py; do
    [[ -e "$f" ]] || continue
    mod="$(basename "$f" .py)"; mod="${mod#nyxus_}"
    bin="nyxus-${mod//_/-}"; [[ "$mod" == "sysmon_gtk" ]] && bin="nyxus-sysmon"
    printf '#!/usr/bin/env bash\nexec python3 "%s/.nyxus/nyxus_%s.py" "$@"\n' "$HOME" "$mod" \
      > "${HOME}/.local/bin/${bin}"
    chmod 0755 "${HOME}/.local/bin/${bin}"; n=$((n+1))
  done
  ok "${n} apps + launchers in ~/.nyxus / ~/.local/bin"
else
  run "mkdir -p \"\$HOME/.nyxus\" \"\$HOME/.local/bin\""
  warn "[dry-run] would copy $(ls "${NS}"/nyxus_*.py 2>/dev/null | wc -l) apps + generate launchers"
fi
case ":$PATH:" in *":$HOME/.local/bin:"*) : ;; *) warn "add ~/.local/bin to PATH (e.g. in ~/.bashrc)";; esac

# ── 4. gated / opt-in system setup ───────────────────────────────────────────
if $DO_NVIDIA; then
  step "NVIDIA suspend/resume fix (opt-in)"
  run "sudo bash \"${SCRIPT_DIR}/nyxus-fix-nvidia-suspend.sh\""
fi
if $DO_GREETER; then
  step "greetd + regreet login"
  run "sudo bash \"${SCRIPT_DIR}/nyxus-setup-greetd.sh\""
fi
if $DO_KERNEL; then
  step "kage-ryu selectable kernel (opt-in; long build)"
  warn "builds + installs a custom kernel as a SELECTABLE entry; stock stays default."
  run "sudo bash \"${REPO_ROOT}/kernel/install-kage-ryu.sh\""
fi
if $DO_LOADOUT; then
  step "GowskiNet security loadout (opt-in)"
  if [[ -x "${SCRIPT_DIR}/nyxus-security-loadout.sh" ]]; then
    run "sudo bash \"${SCRIPT_DIR}/nyxus-security-loadout.sh\""
  else
    warn "nyxus-security-loadout.sh not present yet — jeTT/kage-ryu-sensor/Bifrost"
    warn "integration is tracked in docs/NYXUS_BUILD_BRIEF.md §8.1 (opt-in module)."
  fi
fi

# ── 5. session cleanup / defaults ────────────────────────────────────────────
cleanup_sessions

# ── 6. verify ────────────────────────────────────────────────────────────────
step "verify build health"
if $DRY; then warn "[dry-run] would run scripts/nyxus-verify-build.sh"; else
  bash "${SCRIPT_DIR}/nyxus-verify-build.sh" || warn "verify reported issues (see above)"
fi
if ! $DRY; then
  verify_session_state
fi

printf "\n${GOLD}${B}NYXUS install complete${R}$($DRY && printf ' (dry-run — nothing changed)')\n"
printf "  verification: greeter/session path should now default to ${CYAN}NYXUS (Hyprland)${R}\n"
$KEEP_LEGACY_SESSIONS && printf "  legacy sessions were preserved by request.\n"
printf "  next: reboot or log out and confirm the NYXUS greeter/session is selected.\n\n"
