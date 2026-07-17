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
#   cd Nyxus-Core && ./scripts/nyxus-install.sh              # base desktop
#   ./scripts/nyxus-install.sh --dry-run                     # preview, no changes
#   ./scripts/nyxus-install.sh --greeter --nvidia-suspend    # + gated extras
#   ./scripts/nyxus-install.sh --all                         # everything
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
#   - Gated/risky steps (greeter, kernel, loadout) are OPT-IN — never run by
#     default, matching "don't deploy the login/kernel until verified".
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
DO_GREETER=false; DO_KERNEL=false; DO_NVIDIA=false; DO_LOADOUT=false
usage() { sed -n '2,33p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0; }
for arg in "$@"; do case "$arg" in
  --dry-run)        DRY=true ;;
  --yes|-y)         ASSUME_YES=true ;;
  --lean)           TIER=lean ;;
  --full)           TIER=full ;;
  --greeter)        DO_GREETER=true ;;
  --kernel)         DO_KERNEL=true ;;
  --nvidia-suspend) DO_NVIDIA=true ;;
  --loadout)        DO_LOADOUT=true ;;
  --all)            DO_GREETER=true; DO_KERNEL=true; DO_NVIDIA=true; DO_LOADOUT=true ;;
  -h|--help)        usage ;;
  *) fail "unknown option: $arg (try --help)"; exit 2 ;;
esac; done

# ── 0. preflight ─────────────────────────────────────────────────────────────
step "preflight"
if [[ $EUID -eq 0 ]]; then fail "run as your normal user, not root (sudo is used where needed)"; exit 1; fi
[[ -f /etc/arch-release ]] || { fail "this installer targets Arch Linux"; exit 1; }
[[ -d "$NS" ]] || { fail "run from a Nyxus-Core clone (missing ${NS})"; exit 1; }
command -v pacman >/dev/null || { fail "pacman not found"; exit 1; }
PKG_LIST="${PROFILE}/packages.x86_64"; [[ "$TIER" == lean ]] && PKG_LIST="${PROFILE}/packages.x86_64.lean"
[[ -f "$PKG_LIST" ]] || { fail "package list not found: $PKG_LIST"; exit 1; }
ok "Arch host, running as ${USER}, tier=${TIER}$($DRY && echo ', DRY-RUN')"
ok "plan: packages + configs + apps + verify$($DO_GREETER && echo ' + greeter')$($DO_KERNEL && echo ' + kernel')$($DO_NVIDIA && echo ' + nvidia-suspend')$($DO_LOADOUT && echo ' + security-loadout')"

if ! $DRY && ! $ASSUME_YES; then
  printf "\n${B}This will install packages and place NYXUS configs on this system.${R}\n"
  read -rp "Continue? [y/N] " a; [[ "$a" =~ ^[Yy]$ ]] || { warn "aborted"; exit 0; }
fi

# ── 1. packages ──────────────────────────────────────────────────────────────
step "install packages (${TIER} tier)"
mapfile -t WANT < <(grep -vE '^\s*#|^\s*$' "$PKG_LIST" | sort -u)
# Filter to packages that actually exist in the enabled repos so one unknown
# entry (e.g. a multilib pkg with multilib disabled) can't abort the whole run.
AVAIL="$(pacman -Slq 2>/dev/null | sort -u)"
INSTALLABLE=(); SKIPPED=()
while IFS= read -r p; do
  if grep -qxF "$p" <<<"$AVAIL"; then INSTALLABLE+=("$p"); else SKIPPED+=("$p"); fi
done < <(printf '%s\n' "${WANT[@]}")
ok "${#INSTALLABLE[@]} installable / ${#WANT[@]} listed"
(( ${#SKIPPED[@]} )) && warn "skipped ${#SKIPPED[@]} not in enabled repos (enable multilib for lib32-*, or add AUR): ${SKIPPED[*]:0:8}…"
run "sudo pacman -S --needed --noconfirm ${INSTALLABLE[*]}"

# ── 2. configs (delegate — backs up + places hypr/eww/rofi/dunst/walls) ──────
step "place desktop configs (via nyxus-restore-desktop.sh)"
if $DRY; then warn "[dry-run] would run scripts/nyxus-restore-desktop.sh"; else
  bash "${SCRIPT_DIR}/nyxus-restore-desktop.sh" || warn "restore-desktop reported issues — review above"
fi

# ── 3. NYXUS app suite → ~/.nyxus + launchers ────────────────────────────────
step "install NYXUS app suite (~/.nyxus + launchers)"
run "mkdir -p \"\$HOME/.nyxus\" \"\$HOME/.local/bin\""
if ! $DRY; then
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
  warn "[dry-run] would copy $(ls "${NS}"/nyxus_*.py 2>/dev/null | wc -l) apps + generate launchers"
fi
case ":$PATH:" in *":$HOME/.local/bin:"*) : ;; *) warn "add ~/.local/bin to PATH (e.g. in ~/.bashrc)";; esac

# ── 4. gated / opt-in system setup ───────────────────────────────────────────
if $DO_NVIDIA; then
  step "NVIDIA suspend/resume fix (opt-in)"
  run "sudo bash \"${SCRIPT_DIR}/nyxus-fix-nvidia-suspend.sh\""
fi
if $DO_GREETER; then
  step "greetd + regreet login (opt-in)"
  warn "switches the display manager. Verify you can reach a TTY before rebooting."
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

# ── 5. verify ────────────────────────────────────────────────────────────────
step "verify build health"
if $DRY; then warn "[dry-run] would run scripts/nyxus-verify-build.sh"; else
  bash "${SCRIPT_DIR}/nyxus-verify-build.sh" || warn "verify reported issues (see above)"
fi

printf "\n${GOLD}${B}NYXUS install complete${R}$($DRY && printf ' (dry-run — nothing changed)')\n"
printf "  next: log out and pick ${CYAN}NYXUS (Hyprland)${R} at the greeter"
$DO_GREETER || printf ", or run with ${CYAN}--greeter${R} to switch the login"
printf ".\n\n"
