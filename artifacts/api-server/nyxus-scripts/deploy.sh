#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS — full-payload deployer (live-session install)                ║
# ║                                                                      ║
# ║  Run this from a working Hyprland session when you want the entire   ║
# ║  NYXUS payload (apps, configs, services, wallpapers, polkit) put on  ║
# ║  the system without rebooting or rebuilding the ISO.                 ║
# ║                                                                      ║
# ║    curl -fsSL <api>/api/download/nyxus/deploy.sh | bash              ║
# ║                                                                      ║
# ║  Differences from rescue.sh:                                         ║
# ║   · Deploys EVERY allowlisted file (not just the rescue subset)      ║
# ║   · Categorises by prefix/extension and installs to canonical paths  ║
# ║   · Skips ISO-only stuff (boot-splash, calamares, *.tgz, .md docs)   ║
# ║   · Skips eww install (handled separately — known build failure)     ║
# ║                                                                      ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -u

N="${NYXUS_API:-https://7d45d4aa-bc2d-4fae-a4a4-a672ca904937-00-2ixlfhdaz3p4i.kirk.replit.dev/api/download/nyxus}"

echo "=== NYXUS deploy starting ==="
echo "    api: $N"

# Fetch the manifest (one filename per line, sha256 + filename).
MANIFEST="$(mktemp)"
curl -fsSL "$N/manifest.txt" -o "$MANIFEST" || {
  echo "FAIL  could not fetch manifest"; exit 1; }
TOTAL=$(wc -l < "$MANIFEST")
echo "    manifest: $TOTAL files"

# Skip-list: things that are ISO-only or known-broken in live deploy.
SKIP_REGEX='^(boot-splash|calamares|.*\.(tgz|md|tar\.gz)$|nyxus-build-iso\.sh|nyxus-bootstrap)'

# Counters
ok=0; skip=0; fail=0

# Ensure destination dirs exist
sudo mkdir -p /usr/local/bin /opt/nyxus/lib /usr/share/applications \
              /usr/share/polkit-1/actions /etc/systemd/system \
              /usr/share/backgrounds/nyxus
mkdir -p ~/.config/hypr/conf.d ~/.config/eww/scripts ~/.config/nyxus

# Helper: download to a temp file, then move into place with right perms.
fetch() {
  local name="$1" dest="$2" mode="$3" use_sudo="$4"
  local tmp; tmp="$(mktemp)"
  if curl -fsSL "$N/$name" -o "$tmp" 2>/dev/null && [ -s "$tmp" ]; then
    if [ "$use_sudo" = "1" ]; then
      sudo install -m "$mode" "$tmp" "$dest" 2>/dev/null && return 0
    else
      install -m "$mode" "$tmp" "$dest" 2>/dev/null && return 0
    fi
  fi
  rm -f "$tmp"
  return 1
}

# Iterate every file in the manifest.
while read -r sha name; do
  [ -z "$name" ] && continue
  # Skip if matches blacklist regex
  if [[ "$name" =~ $SKIP_REGEX ]]; then
    skip=$((skip+1)); continue
  fi

  base="$(basename "$name")"
  case "$name" in
    # ── Python apps → /opt/nyxus/lib/, wrapper in /usr/local/bin
    nyxus_*.py)
      stem="${base%.py}"; cmd="${stem//_/-}"
      if fetch "$name" "/opt/nyxus/lib/$base" 0644 1; then
        sudo tee "/usr/local/bin/$cmd" >/dev/null <<EOF
#!/usr/bin/env bash
exec python3 /opt/nyxus/lib/$base "\$@"
EOF
        sudo chmod +x "/usr/local/bin/$cmd"
        ok=$((ok+1))
      else fail=$((fail+1)); fi
      ;;

    # ── Desktop entries → /usr/share/applications/
    desktop-entries/*.desktop)
      fetch "$name" "/usr/share/applications/$base" 0644 1 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── Polkit policies → /usr/share/polkit-1/actions/
    *.policy)
      fetch "$name" "/usr/share/polkit-1/actions/$base" 0644 1 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── Systemd units → /etc/systemd/system/  (NOT enabled — user opt-in)
    *.service|*.timer)
      fetch "$name" "/etc/systemd/system/$base" 0644 1 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── Wallpapers → /usr/share/backgrounds/nyxus/
    nyxus-bg-*.png|nyxus-bg-*.mp4|nyxus-bg-*.jpg)
      fetch "$name" "/usr/share/backgrounds/nyxus/$base" 0644 1 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── Hyprland conf shards → ~/.config/hypr/conf.d/
    nyxus-hyprland-*.conf|hypr*.conf)
      fetch "$name" "$HOME/.config/hypr/conf.d/$base" 0644 0 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── EWW (already deployed by rescue.sh; refresh in place)
    eww/*)
      target="$HOME/.config/eww/${name#eww/}"
      mkdir -p "$(dirname "$target")"
      fetch "$name" "$target" 0644 0 \
        && ok=$((ok+1)) || fail=$((fail+1))
      [[ "$name" == eww/scripts/* ]] && chmod +x "$target"
      ;;

    # ── Browser configs → ~/.config/<app>/
    browser/*)
      target="$HOME/.config/${name#browser/}"
      mkdir -p "$(dirname "$target")"
      fetch "$name" "$target" 0644 0 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── Locales → /usr/share/locale/
    locale/*)
      target="/usr/share/$name"
      sudo mkdir -p "$(dirname "$target")"
      fetch "$name" "$target" 0644 1 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── Top-level shell helpers / no-extension binaries → /usr/local/bin/
    nyxus-*)
      # strip any directory; binaries are flat in nyxus-scripts/
      [[ "$name" == */* ]] && { skip=$((skip+1)); continue; }
      fetch "$name" "/usr/local/bin/$base" 0755 1 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── Hyprland top-level configs → ~/.config/hypr/
    hypridle.conf|hyprland.conf|hyprlock.conf|alacritty.toml)
      fetch "$name" "$HOME/.config/hypr/$base" 0644 0 \
        && ok=$((ok+1)) || fail=$((fail+1))
      ;;

    # ── Anything else: skip silently
    *)
      skip=$((skip+1))
      ;;
  esac
done < "$MANIFEST"

rm -f "$MANIFEST"

echo ""
echo "=== NYXUS deploy complete ==="
echo "  installed: $ok"
echo "  skipped:   $skip   (ISO-only / docs / archives)"
echo "  failed:    $fail"
echo ""
echo "Refreshing systemd unit cache + desktop database…"
sudo systemctl daemon-reload 2>/dev/null
sudo update-desktop-database /usr/share/applications 2>/dev/null
echo ""
echo "Reload Hyprland to pick up new conf shards:  hyprctl reload"
echo "Start the bar:                               nyxus-eww-launch &"
echo ""
echo "DO NOT run 'systemctl restart sddm' — it kills your live session."
