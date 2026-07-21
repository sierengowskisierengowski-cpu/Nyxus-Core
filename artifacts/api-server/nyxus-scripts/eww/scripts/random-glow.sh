#!/usr/bin/env bash
set -u

pick() {
  (( RANDOM % 100 < 35 )) && echo true || echo false
}

printf '{"brand":%s,"stamp":%s,"clock":%s,"ticker":%s,"search":%s}\n' \
  "$(pick)" "$(pick)" "$(pick)" "$(pick)" "$(pick)"
