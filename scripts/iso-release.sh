#!/usr/bin/env bash
# NYXUS · ISO release helper.
#
# Runs on the Arch host where mkarchiso has produced an ISO under
# iso-builder/out/. Generates checksums, signs (if a GPG key is
# available), and updates the download portal's manifest at
# artifacts/nyxus-web/public/releases.json.
#
# Usage:  ./scripts/iso-release.sh <version>
# Example: ./scripts/iso-release.sh 2026.05.14
set -euo pipefail

ver="${1:-}"
if [[ -z "$ver" ]]; then
  echo "usage: $0 <version>  (example: 2026.05.14)" >&2
  exit 2
fi
if ! [[ "$ver" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}$ ]]; then
  echo "version must look like YYYY.MM.DD" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/iso-builder/out"
MANIFEST="$ROOT/artifacts/nyxus-web/public/releases.json"

iso="$OUT/nyxus-${ver}-x86_64.iso"
if [[ ! -f "$iso" ]]; then
  # Fall back to whatever .iso archiso produced — it usually adds the
  # date itself. We pick the most recent ISO and rename it for parity.
  candidate="$(find "$OUT" -maxdepth 1 -type f -name "*.iso" -printf '%T@ %p\n' \
              | sort -rn | head -1 | cut -d' ' -f2-)"
  if [[ -z "$candidate" ]]; then
    echo "no ISO found in $OUT — run mkarchiso first" >&2
    exit 1
  fi
  echo "renaming $(basename "$candidate") → $(basename "$iso")"
  mv "$candidate" "$iso"
fi

cd "$OUT"
sha256sum    "$(basename "$iso")" > "${iso}.sha256"
sha512sum    "$(basename "$iso")" > "${iso}.sha512"

if command -v gpg >/dev/null && gpg --list-secret-keys >/dev/null 2>&1; then
  gpg --detach-sign --armor --output "${iso}.sig" "$iso"
  echo "signed → ${iso}.sig"
else
  echo "skipping GPG sign — no secret key available"
fi

bytes=$(stat -c %s "$iso")
sha=$(awk '{print $1}' "${iso}.sha256")

mkdir -p "$(dirname "$MANIFEST")"
python3 - <<PY
import json, os, sys, time
m = "$MANIFEST"
data = {"releases": []}
if os.path.exists(m):
    try:    data = json.load(open(m))
    except Exception: pass
data.setdefault("releases", [])
entry = {
    "version":   "$ver",
    "filename":  os.path.basename("$iso"),
    "sha256":    "$sha",
    "bytes":     int("$bytes"),
    "publishedAt": int(time.time()),
}
data["releases"] = [r for r in data["releases"] if r.get("version") != "$ver"]
data["releases"].insert(0, entry)
data["latest"] = "$ver"
json.dump(data, open(m, "w"), indent=2)
print("manifest updated:", m)
PY

echo
echo "RELEASE READY  ver=$ver  size=$(numfmt --to=iec "$bytes")"
echo "  iso:    $iso"
echo "  sha256: $sha"
echo "  manifest: $MANIFEST"
