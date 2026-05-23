#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN environment variable is required." >&2
  exit 1
fi

OWNER="${GITHUB_OWNER:-sierengowskisierengowski-cpu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"
REPO_TYPES_FILE="${SCRIPT_DIR}/repo-types.json"
WORKDIR="${SCRIPT_DIR}/.tmp-init"

if [[ ! -f "${REPO_TYPES_FILE}" ]]; then
  echo "Missing repo-types mapping: ${REPO_TYPES_FILE}" >&2
  exit 1
fi

mkdir -p "${WORKDIR}"

readarray -t REPO_ENTRIES < <(python3 - <<'PY' "${REPO_TYPES_FILE}"
import json
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
for name, repo_type in data.items():
    print(f"{name}\t{repo_type}")
PY
)

declare -A REPO_TYPES
for entry in "${REPO_ENTRIES[@]}"; do
  repo="${entry%%$'\t'*}"
  type="${entry#*$'\t'}"
  REPO_TYPES["$repo"]="$type"
done

REPOS=(
  "API-Server"
  "Web"
  "Notepad"
  "Stickies"
  "Sysmon"
  "Widgets"
  "Mockup-Sandbox"
  "ISO-Builder"
  "Scripts"
  "Libs"
  "Intel"
  "Dockd"
  "Hotkeyd"
  "Snapd"
  "QSD"
  "Wallpaper-Studio"
  "Store"
  "Welcome"
)

describe_repo() {
  case "$1" in
    Nyxus-API-Server) echo "Nyxus backend API service" ;;
    Nyxus-Web) echo "Nyxus primary web application" ;;
    Nyxus-Notepad) echo "Nyxus Notepad application" ;;
    Nyxus-Stickies) echo "Nyxus Stickies application" ;;
    Nyxus-Sysmon) echo "Nyxus System Monitor application" ;;
    Nyxus-Widgets) echo "Nyxus desktop widgets application" ;;
    Nyxus-Mockup-Sandbox) echo "Nyxus mockup sandbox" ;;
    Nyxus-Store) echo "Nyxus application store" ;;
    Nyxus-Welcome) echo "Nyxus welcome and onboarding application" ;;
    Nyxus-ISO-Builder) echo "Nyxus ISO build scripts" ;;
    Nyxus-Scripts) echo "Nyxus scripts collection" ;;
    Nyxus-Libs) echo "Nyxus shared libraries" ;;
    Nyxus-Intel) echo "Nyxus Intel Python service" ;;
    Nyxus-Dockd) echo "Nyxus Dock daemon" ;;
    Nyxus-Hotkeyd) echo "Nyxus Hotkey daemon" ;;
    Nyxus-Snapd) echo "Nyxus Snap daemon" ;;
    Nyxus-QSD) echo "Nyxus quick settings daemon" ;;
    Nyxus-Wallpaper-Studio) echo "Nyxus Wallpaper Studio service" ;;
    *) echo "Nyxus repository" ;;
  esac
}

apply_placeholders() {
  local repo_name="$1"
  local repo_description="$2"

  while IFS= read -r -d '' f; do
    if file "$f" | grep -qE 'text|JSON|YAML|XML'; then
      sed -i \
        -e "s/{{REPO_NAME}}/${repo_name}/g" \
        -e "s/{{REPO_DESCRIPTION}}/${repo_description}/g" \
        "$f"
    fi
  done < <(find . -type f -not -path './.git/*' -print0)
}

for short_name in "${REPOS[@]}"; do
  repo_name="Nyxus-${short_name}"
  repo_type="${REPO_TYPES[$repo_name]:-}"

  if [[ -z "$repo_type" ]]; then
    echo "[skip] ${repo_name}: no type mapping in repo-types.json"
    continue
  fi

  template_path="${TEMPLATES_DIR}/${repo_type}"
  if [[ ! -d "$template_path" ]]; then
    echo "[skip] ${repo_name}: template directory missing (${template_path})"
    continue
  fi

  repo_dir="${WORKDIR}/${repo_name}"
  rm -rf "$repo_dir"

  echo "[clone] ${repo_name}"
  git -c http.extraHeader="AUTHORIZATION: bearer ${GITHUB_TOKEN}" clone "https://github.com/${OWNER}/${repo_name}.git" "$repo_dir"

  pushd "$repo_dir" >/dev/null

  if git rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "[skip] ${repo_name}: repository already initialized"
    popd >/dev/null
    continue
  fi

  cp -R "${template_path}/." .
  apply_placeholders "$repo_name" "$(describe_repo "$repo_name")"

  git checkout --orphan main
  git add .
  git commit -m "chore: initialize repository from Nyxus-Core template"
  git -c http.extraHeader="AUTHORIZATION: bearer ${GITHUB_TOKEN}" push -u origin main

  popd >/dev/null
  echo "[done] ${repo_name}"
done

echo "Initialization complete for all mapped repositories."
