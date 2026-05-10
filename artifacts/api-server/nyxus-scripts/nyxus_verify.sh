#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# NYXUS install verifier
#
# Source this file (or call its commands directly) to download NYXUS
# installer scripts/tarballs with SHA256 verification against the server's
# published manifest.
#
# Usage (interactive):
#   source ~/.nyxus/nyxus_verify.sh
#   nyxus_verified_install nyxus_panel_install.sh   # fetch + verify + sudo
#   nyxus_verified_fetch   nyxus-start.tgz /tmp/x   # fetch + verify only
#
# Usage (CLI):
#   ~/.nyxus/nyxus_verify.sh fetch   nyxus-start.tgz /tmp/x
#   ~/.nyxus/nyxus_verify.sh install nyxus_start_install.sh
#   ~/.nyxus/nyxus_verify.sh sha     nyxus-start.tgz       # echo expected sha
#   ~/.nyxus/nyxus_verify.sh check                          # full audit
#
# Threat model
# ────────────
#   • Bootstrap (the very first `curl ... | sudo bash` of nyxus_install.sh)
#     is "trust on first use" — there's no key in place yet. After bootstrap,
#     this verifier is on disk and every subsequent install fetches the
#     manifest first and refuses to execute any file whose SHA256 does not
#     match the manifest's value.
#   • Defends against: single-file transit corruption, single-file server
#     tampering, mirror swap mid-install.
#   • Does NOT defend against: full server compromise where the attacker
#     can rewrite both manifest.json AND the file in lockstep. Future work:
#     GPG-sign the manifest with an offline key, embed the public key in
#     the bootstrap.
#
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ──────────────────────────────────────────────────────────────────────

NYXUS_BASE="${NYXUS_BASE:-https://nyxus-core.replit.app/api/download/nyxus}"
NYXUS_MANIFEST_URL="${NYXUS_MANIFEST_URL:-$NYXUS_BASE/manifest.json}"
NYXUS_VERIFY_TIMEOUT="${NYXUS_VERIFY_TIMEOUT:-15}"
NYXUS_FETCH_TIMEOUT="${NYXUS_FETCH_TIMEOUT:-90}"

# ── tiny logger (writes to stderr so stdout stays clean for shell pipelines)
_nyx_v_log() { printf '\033[2m[verify]\033[0m %s\n' "$*" >&2; }
_nyx_v_ok()  { printf '\033[32m[verify ✓]\033[0m %s\n' "$*" >&2; }
_nyx_v_err() { printf '\033[31m[verify ✗]\033[0m %s\n' "$*" >&2; }

# ── manifest cache (lifetime of this shell)
_NYX_MANIFEST_CACHE=""

nyxus_manifest() {
    if [[ -z "$_NYX_MANIFEST_CACHE" ]]; then
        if ! _NYX_MANIFEST_CACHE="$(curl -fsSL --max-time "$NYXUS_VERIFY_TIMEOUT" "$NYXUS_MANIFEST_URL")"; then
            _nyx_v_err "could not fetch manifest from $NYXUS_MANIFEST_URL"
            return 2
        fi
    fi
    printf '%s' "$_NYX_MANIFEST_CACHE"
}

# Echoes expected SHA256 for a filename. Empty + non-zero exit if absent.
nyxus_expected_sha() {
    local name="$1"
    local m
    m="$(nyxus_manifest)" || return $?
    if ! command -v python3 >/dev/null 2>&1; then
        # Pure-bash fallback for the rare host without python3 (Arch ships it
        # by default, so this is just defensive). Uses a JSON-naive grep
        # against the manifest format we control.
        printf '%s' "$m" | tr -d '\n' \
            | grep -oE "\"$name\"[^}]*\"sha256\":\"[a-f0-9]{64}\"" \
            | head -1 \
            | grep -oE '[a-f0-9]{64}'
        return ${PIPESTATUS[0]}
    fi
    python3 -c '
import json, sys
m = json.loads(sys.argv[1])
files = m.get("files") or {}
entry = files.get(sys.argv[2]) or {}
sha = entry.get("sha256") or ""
print(sha)
' "$m" "$name"
}

# nyxus_verified_fetch <name> <out_path>
#   Downloads $NYXUS_BASE/<name> to <out_path>, verifies SHA256 against the
#   manifest, and removes the file (returning non-zero) if it fails.
nyxus_verified_fetch() {
    local name="$1" out="$2"
    if [[ -z "$name" || -z "$out" ]]; then
        _nyx_v_err "usage: nyxus_verified_fetch <name> <out_path>"
        return 64
    fi
    local url="$NYXUS_BASE/$name"
    local expected actual
    expected="$(nyxus_expected_sha "$name")" || return $?
    if [[ -z "$expected" ]]; then
        _nyx_v_err "no SHA256 entry for '$name' in manifest — refusing"
        return 3
    fi

    if ! curl -fsSL --max-time "$NYXUS_FETCH_TIMEOUT" "$url" -o "$out"; then
        _nyx_v_err "download failed: $url"
        rm -f "$out"
        return 4
    fi

    if command -v sha256sum >/dev/null 2>&1; then
        actual="$(sha256sum "$out" | awk '{print $1}')"
    elif command -v shasum >/dev/null 2>&1; then
        actual="$(shasum -a 256 "$out" | awk '{print $1}')"
    else
        _nyx_v_err "no sha256sum/shasum on this system — cannot verify"
        rm -f "$out"
        return 5
    fi

    if [[ "$actual" != "$expected" ]]; then
        _nyx_v_err "SHA256 mismatch for $name"
        _nyx_v_err "  expected: $expected"
        _nyx_v_err "  actual:   $actual"
        rm -f "$out"
        return 6
    fi
    _nyx_v_ok "$name verified (${expected:0:12}…)"
    return 0
}

# nyxus_verified_install <installer-name>
#   Fetches an installer script (e.g. nyxus_panel_install.sh), verifies it,
#   then executes it via `sudo bash`. Cleans up the temp file on exit.
nyxus_verified_install() {
    local name="$1"
    if [[ -z "$name" ]]; then
        _nyx_v_err "usage: nyxus_verified_install <installer-name>"
        return 64
    fi
    local tmp
    tmp="$(mktemp -t nyxus-installer.XXXXXX.sh)" || return 7
    # shellcheck disable=SC2064
    trap "rm -f '$tmp'" RETURN

    if ! nyxus_verified_fetch "$name" "$tmp"; then
        return $?
    fi
    _nyx_v_log "executing verified installer: $name"
    sudo bash "$tmp"
}

# nyxus_verified_install_user <installer-name>
#   Same as above but without sudo (for installers that elevate themselves).
nyxus_verified_install_user() {
    local name="$1"
    if [[ -z "$name" ]]; then
        _nyx_v_err "usage: nyxus_verified_install_user <installer-name>"
        return 64
    fi
    local tmp
    tmp="$(mktemp -t nyxus-installer.XXXXXX.sh)" || return 7
    # shellcheck disable=SC2064
    trap "rm -f '$tmp'" RETURN

    if ! nyxus_verified_fetch "$name" "$tmp"; then
        return $?
    fi
    _nyx_v_log "executing verified installer (user): $name"
    bash "$tmp"
}

# nyxus_audit
#   Audit every NYXUS file in the manifest against a fresh download. Useful
#   for paranoid users who want a periodic integrity check. Reports OK/FAIL.
nyxus_audit() {
    local m count=0 ok=0 fail=0 missing=0
    m="$(nyxus_manifest)" || return $?
    if ! command -v python3 >/dev/null 2>&1; then
        _nyx_v_err "audit requires python3"
        return 1
    fi
    local names
    names="$(python3 -c '
import json, sys
m = json.loads(sys.argv[1])
for n in (m.get("files") or {}).keys(): print(n)
' "$m")"
    while IFS= read -r name; do
        [[ -z "$name" ]] && continue
        count=$((count+1))
        local tmp; tmp="$(mktemp -t nyxus-audit.XXXXXX)"
        if nyxus_verified_fetch "$name" "$tmp" >/dev/null 2>&1; then
            ok=$((ok+1))
        else
            fail=$((fail+1))
            _nyx_v_err "  audit FAIL: $name"
        fi
        rm -f "$tmp"
    done <<< "$names"
    _nyx_v_log "audit: $count files · $ok OK · $fail FAIL"
    [[ $fail -eq 0 ]]
}

# ── CLI dispatch (when invoked directly, not sourced)
# Detects "executed as a script" vs "sourced into another shell" reliably.
if (return 0 2>/dev/null); then
    : # sourced — expose functions only, no CLI dispatch
else
    cmd="${1:-}"; shift || true
    case "$cmd" in
        fetch)        nyxus_verified_fetch        "$@" ;;
        install)      nyxus_verified_install      "$@" ;;
        install-user) nyxus_verified_install_user "$@" ;;
        sha)          nyxus_expected_sha          "$@" ;;
        audit|check)  nyxus_audit                 "$@" ;;
        manifest)     nyxus_manifest                   ;;
        ""|help|-h|--help)
            cat <<EOF
nyxus_verify.sh — SHA256-verified NYXUS installer

Subcommands:
  fetch        <name> <out>       download + verify a single file
  install      <installer-name>   download + verify, then sudo bash it
  install-user <installer-name>   download + verify, then bash it (no sudo)
  sha          <name>             print expected SHA256 from manifest
  audit                            verify every file in the manifest
  manifest                         print the full manifest.json
EOF
            ;;
        *)
            _nyx_v_err "unknown command: $cmd  (try: $0 help)"
            exit 64
            ;;
    esac
fi
