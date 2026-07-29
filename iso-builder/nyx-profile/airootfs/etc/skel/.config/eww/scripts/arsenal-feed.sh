#!/usr/bin/env bash
# NYXUS · EWW · ARSENAL station deck — security console port probe
# Checks whether each GowskiNet security console backend is listening.
# Uses a 1-second timeout so a down service never stalls the poll.
set -u

probe() {
  local port="$1"
  if nc -z -w1 127.0.0.1 "$port" 2>/dev/null; then
    echo true
  else
    echo false
  fi
}

printf '{"cipher":%s,"forge":%s,"redforge":%s,"gsl":%s,"trainer":%s}\n' \
  "$(probe 8080)"  \
  "$(probe 20000)" \
  "$(probe 5000)"  \
  "$(probe 19670)" \
  "$(probe 20508)"
