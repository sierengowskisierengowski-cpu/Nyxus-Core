#!/usr/bin/env bash
# NYXUS · ingest Meshy icons from ~/Downloads → normalized PNGs for EWW.
#
# Copies Meshy_AI_Nyxus*.png / Meshy_AI_nyxus*.png downloads, maps to
# kebab-case slugs, downscales to 64px (1x) + 128px (@2x), syncs to:
#   - Nyxus-Core/assets/icons/{bar,apps}/
#   - ~/.config/eww/assets/icons/{bar,apps}/
#   - iso skel (when writable)
#
# Usage:
#   scripts/ingest-bar-icons.sh              # ingest all downloads
#   scripts/ingest-bar-icons.sh /path.png    # ingest explicit file(s)
#   DRY_RUN=1 scripts/ingest-bar-icons.sh    # preview only
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BAR_CANONICAL="${REPO_ROOT}/assets/icons/bar"
APPS_CANONICAL="${REPO_ROOT}/assets/icons/apps"
EWW_BAR="${HOME}/.config/eww/assets/icons/bar"
EWW_APPS="${HOME}/.config/eww/assets/icons/apps"
ISO_BAR="${REPO_ROOT}/iso-builder/nyx-profile/airootfs/etc/skel/.config/eww/assets/icons/bar"
ISO_APPS="${REPO_ROOT}/iso-builder/nyx-profile/airootfs/etc/skel/.config/eww/assets/icons/apps"
DOWNLOADS="${HOME}/Downloads"
VARIANTS_DIR="_variants"
SIZE_1X=64
SIZE_2X=128
DRY_RUN="${DRY_RUN:-0}"

mkdir -p "$BAR_CANONICAL/$VARIANTS_DIR" "$APPS_CANONICAL/$VARIANTS_DIR" \
         "$EWW_BAR" "$EWW_APPS"

# ── slugs that live under bar/ (system UI + workspaces) ─────────────
BAR_SLUGS=(
  wifi bluetooth night-mode alerts snap quick-os microphone volume mixer
  brightness display dashboard deep-core mission updates settings keys
  lock logout power
  workspace-1 workspace-2 workspace-3 workspace-4 workspace-5
  workspace-6 workspace-7 workspace-8 workspace-9
)

# also mirrored in bar/ for bar/hub reserved slots
BAR_MIRROR_APPS=(browser code-editor discord files terminal music-player)

is_bar_slug() {
  local s="$1" x
  for x in "${BAR_SLUGS[@]}"; do [[ "$x" == "$s" ]] && return 0; done
  for x in "${BAR_MIRROR_APPS[@]}"; do [[ "$x" == "$s" ]] && return 0; done
  return 1
}

# ── explicit Meshy title → normalized slug ───────────────────────────
declare -A NAME_MAP=(
  ["WiFi"]="wifi"
  ["Bluetooth"]="bluetooth"
  ["Night Mode"]="night-mode"
  ["Alerts"]="alerts"
  ["Snap"]="snap"
  ["Quick OS"]="quick-os"
  ["Microphone"]="microphone"
  ["Volume Speaker"]="volume"
  ["Mixer"]="mixer"
  ["Brightness"]="brightness"
  ["Display Monitor"]="display"
  ["Dashboard"]="dashboard"
  ["Deep Core"]="deep-core"
  ["Mission"]="mission"
  ["Updates"]="updates"
  ["Settings Gear"]="settings"
  ["Keys"]="keys"
  ["Lock"]="lock"
  ["Logout"]="logout"
  ["Power Shutdown"]="power"
  ["Discord"]="discord"
  ["Code Editor"]="code-editor"
  ["Music Player"]="music-player"
  ["Files"]="files"
  ["Browser"]="browser"
  ["Terminal"]="terminal"
  ["4KTube"]="4ktube"
  ["Alacritty"]="alacritty"
  ["Alpaca"]="alpaca"
  ["Android Studio"]="android-studio"
  ["APEX Rig"]="apex-rig"
  ["Arduino IDE"]="arduino-ide"
  ["Arsenal"]="arsenal"
  ["Avahi Network"]="avahi-network"
  ["BAASIC Media Player"]="baasic-media-player"
  ["Bifrost"]="bifrost"
  ["Blast From The Past"]="blast-from-the-past"
  ["Blender"]="blender"
  ["btop++"]="btop"
  ["CherryTree"]="cherrytree"
  ["Chromium"]="chromium"
  ["Claude AI"]="claude-ai"
  ["CMake"]="cmake"
  ["COSMIC Files"]="cosmic-files"
  ["COSMIC Settings"]="cosmic-settings"
  ["COSMIC Store"]="cosmic-store"
)

normalize_title() {
  local raw="$1"

  # Meshy_AI_nyxus-cursor-icon.png → cursor
  if [[ "$raw" =~ ^[Mm]eshy_AI_nyxus-(.+)$ ]]; then
    local slug="${BASH_REMATCH[1]}"
    slug="${slug%-icon}"
    slug="${slug%.png}"
    echo "$slug" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
    return
  fi

  raw="${raw#Meshy_AI_Nyxus }"
  raw="${raw% Icon.png}"
  raw="${raw%.png}"
  raw="${raw% (1)}"
  raw="${raw% Icon}"

  if [[ "$raw" =~ ^Workspace[[:space:]]+([0-9]+)$ ]]; then
    echo "workspace-${BASH_REMATCH[1]}"
    return
  fi

  if [[ -n "${NAME_MAP[$raw]+isset}" ]]; then
    echo "${NAME_MAP[$raw]}"
    return
  fi

  echo "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

resize_icon() {
  local src="$1" dest_1x="$2" dest_2x="$3"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  [dry] resize → ${dest_1x##*/} (${SIZE_1X}px) + ${dest_2x##*/} (${SIZE_2X}px)"
    return
  fi
  magick "$src" -strip -resize "${SIZE_1X}x${SIZE_1X}" -filter Lanczos "$dest_1x"
  magick "$src" -strip -resize "${SIZE_2X}x${SIZE_2X}" -filter Lanczos "$dest_2x"
}

ingest_to_dir() {
  local src="$1" slug="$2" dest_dir="$3" base="$4"
  local dest_1x="${dest_dir}/${slug}.png"
  local dest_2x="${dest_dir}/${slug}@2x.png"
  local variants="${dest_dir}/${VARIANTS_DIR}"

  if [[ -f "$dest_1x" ]]; then
    local src_md5 existing_md5 existing_w
    src_md5="$(md5sum "$src" | awk '{print $1}')"
    existing_md5="$(md5sum "$dest_1x" | awk '{print $1}')"
    existing_w="$(identify -format '%w' "$dest_1x" 2>/dev/null || echo 0)"
    if [[ "$src_md5" == "$existing_md5" && "$existing_w" -le 100 ]]; then
      if [[ "$DRY_RUN" == "1" ]]; then
        echo "  [dry] duplicate of ${slug}.png in ${dest_dir##*/}/"
      else
        mkdir -p "$variants"
        cp -f "$src" "${variants}/${base}"
        echo "  duplicate → ${dest_dir##*/}/_variants/${base}"
      fi
      return 0
    fi
  fi

  echo "  → ${dest_dir##*/}/${slug}.png"
  resize_icon "$src" "$dest_1x" "$dest_2x"
  if [[ "$DRY_RUN" != "1" && "$base" != "${slug}.png" ]]; then
    mkdir -p "$variants"
    cp -f "$src" "${variants}/${base}"
  fi
}

ingest_file() {
  local src="$1" base title slug

  [[ -f "$src" ]] || { echo "skip (missing): $src" >&2; return 0; }
  base="$(basename "$src")"
  [[ "$base" == [Mm]eshy_AI_[Nn]yxus* ]] || { echo "skip (not Meshy Nyxus): $base" >&2; return 0; }

  title="${base%.png}"
  slug="$(normalize_title "$title")"
  [[ -n "$slug" ]] || { echo "skip (empty slug): $base" >&2; return 0; }

  echo "• ${base} → ${slug}"

  if is_bar_slug "$slug"; then
    ingest_to_dir "$src" "$slug" "$BAR_CANONICAL" "$base"
  else
    ingest_to_dir "$src" "$slug" "$APPS_CANONICAL" "$base"
  fi

  # mirror dual-use app icons into bar/ for pill/hub reserved slots
  for m in "${BAR_MIRROR_APPS[@]}"; do
    if [[ "$m" == "$slug" ]]; then
      ingest_to_dir "$src" "$slug" "$BAR_CANONICAL" "$base"
    fi
  done
  return 0
}

sync_tree() {
  local src="$1" dest="$2"
  [[ "$DRY_RUN" == "1" ]] && { echo "[dry] rsync ${src} → ${dest}"; return; }
  mkdir -p "$dest"
  rsync -a --delete \
    --exclude '_variants/' \
    --exclude 'MANIFEST.md' \
    "${src}/" "${dest}/"
}

sync_all() {
  sync_tree "$BAR_CANONICAL" "$EWW_BAR"
  sync_tree "$APPS_CANONICAL" "$EWW_APPS"
  echo "synced → ${EWW_BAR} + ${EWW_APPS}"

  if mkdir -p "$ISO_BAR" "$ISO_APPS" 2>/dev/null; then
    sync_tree "$BAR_CANONICAL" "$ISO_BAR"
    sync_tree "$APPS_CANONICAL" "$ISO_APPS"
    echo "synced → ISO skel icons"
  else
    echo "ISO skel icons path not writable — skipped" >&2
  fi
}

# ── collect sources ─────────────────────────────────────────────────────
sources=()
if [[ "$#" -gt 0 ]]; then
  sources=("$@")
else
  while IFS= read -r -d '' f; do
    sources+=("$f")
  done < <(find "$DOWNLOADS" -maxdepth 1 -type f \( \
    -iname 'Meshy_AI_Nyxus*.png' -o -iname 'Meshy_AI_nyxus*.png' \) -print0 | sort -z)
fi

if [[ ${#sources[@]} -eq 0 ]]; then
  echo "No Meshy Nyxus PNG files found in ${DOWNLOADS}" >&2
  exit 1
fi

echo "NYXUS icon ingest (${#sources[@]} source file(s))"
for src in "${sources[@]}"; do
  ingest_file "$src"
done

sync_all

bar_count="$(find "$BAR_CANONICAL" -maxdepth 1 -name '*.png' ! -name '*@2x.png' 2>/dev/null | wc -l)"
apps_count="$(find "$APPS_CANONICAL" -maxdepth 1 -name '*.png' ! -name '*@2x.png' 2>/dev/null | wc -l)"
echo "done — bar: ${bar_count} · apps: ${apps_count} unique icons"
