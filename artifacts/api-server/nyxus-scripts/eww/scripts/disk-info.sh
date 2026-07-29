#!/usr/bin/env bash
# NYXUS · EWW · disk usage feed for CORE station deck
# Probes /, /home, and ~/Projects and emits compact JSON.
set -u

get_df() {
  local path="$1"
  df -h "$path" 2>/dev/null | awk 'NR==2 {
    # Strip trailing % from column 5
    pct = $5; gsub(/%/, "", pct)
    printf "{\"used\":\"%s\",\"total\":\"%s\",\"pct\":%d}", $3, $2, int(pct)
  }' || echo '{"used":"--","total":"--","pct":0}'
}

projects_path="${HOME}/Projects"
[[ -d "$projects_path" ]] || projects_path="${HOME}"

printf '{"root":%s,"home":%s,"projects":%s}\n' \
  "$(get_df /)" \
  "$(get_df "${HOME}")" \
  "$(get_df "${projects_path}")"
