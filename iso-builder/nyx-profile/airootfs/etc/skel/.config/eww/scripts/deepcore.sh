#!/usr/bin/env bash
# NYXUS DEEP CORE - kernel + security-stack telemetry feed
# Emits one JSON object for the eww deepcore overlay. Polled every 3s.
# Reads only unprivileged /proc + /sys + systemctl + docker.
set -u

kver=$(uname -r)
kname="stock"
case "$kver" in *kage*|*xanmod*) kname="kage-ryu" ;; esac

taint=$(cat /proc/sys/kernel/tainted 2>/dev/null || echo "?")
[ "$taint" = "0" ] && taintlbl="CLEAN" || taintlbl="TAINTED($taint)"

lsm=$(cat /sys/kernel/security/lsm 2>/dev/null || echo "?")
gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "?")

vuln=0; safe=0
for f in /sys/devices/system/cpu/vulnerabilities/*; do
  [ -r "$f" ] || continue
  if grep -qi "^Vulnerable" "$f" 2>/dev/null; then vuln=$((vuln+1)); else safe=$((safe+1)); fi
done

load=$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null || echo "?")
procs=$(cut -d' ' -f4 /proc/loadavg 2>/dev/null || echo "?")
entropy=$(cat /proc/sys/kernel/random/entropy_avail 2>/dev/null || echo "?")
up=$(awk '{d=int($1/86400);h=int(($1%86400)/3600);m=int(($1%3600)/60); printf "%dd %dh %dm",d,h,m}' /proc/uptime 2>/dev/null)
ctx=$(awk '/^ctxt/{print $2}' /proc/stat 2>/dev/null || echo 0)

svc() { systemctl is-active "$1" 2>/dev/null | head -1; }
jett=$(svc jett-daemon);       [ "$jett" = "active" ]    && jett_on=true || jett_on=false
bifrost=$(svc bifrost-guardian); [ "$bifrost" = "active" ] && bifrost_on=true || bifrost_on=false
meli=$(svc meli-ingest);       [ "$meli" = "active" ]    && meli_on=true || meli_on=false
dock=$(svc docker);            [ "$dock" = "active" ]    && dock_on=true || dock_on=false

pots=0
if [ "$dock_on" = "true" ]; then
  pots=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -cE '^(cowrie|dionaea|conpot|endlessh|heralding|http-honeypot)$')
fi

ebpf="offline"
pgrep -x jett-daemon >/dev/null 2>&1 && ebpf="hooked"

jett_allow=0; jett_review=0; jett_quar=0; jett_mode="?"
if [ -r /etc/default/jett ]; then
  jett_mode=$(grep -E '^JETT_MODE=' /etc/default/jett 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "?")
fi
if [ -r /var/log/jett/jett.log ]; then
  jett_allow=$(timeout 3 grep -ac "ALLOW" /var/log/jett/jett.log 2>/dev/null || echo 0)
  jett_review=$(timeout 3 grep -ac "REVIEW" /var/log/jett/jett.log 2>/dev/null || echo 0)
  jett_quar=$(timeout 3 grep -ac "QUARANTINE (" /var/log/jett/jett.log 2>/dev/null || echo 0)
fi

feed_json='[]'
if command -v python3 >/dev/null 2>&1; then
  feed_json=$(python3 - <<'PY'
import json, re, subprocess

ANSI = re.compile(r"\x1b\[[0-9;]*m")
pots = ["cowrie", "endlessh", "heralding", "dionaea"]
lines = []
for name in pots:
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=2,
        )
        if name not in r.stdout.split():
            continue
        r = subprocess.run(
            ["docker", "logs", "--since", "4m", "--tail", "3", name],
            capture_output=True, text=True, timeout=3, errors="replace",
        )
        for raw in r.stdout.splitlines():
            s = ANSI.sub("", raw).strip()
            if s:
                lines.append(f"{name}: {s[:96]}")
    except Exception:
        pass
print(json.dumps(lines[-6:]))
PY
)
fi

printf '{"kver":"%s","kname":"%s","taint":"%s","lsm":"%s","gov":"%s","vuln":%d,"safe":%d,"load":"%s","procs":"%s","entropy":"%s","uptime":"%s","ctx":"%s","jett":%s,"bifrost":%s,"meli":%s,"docker":%s,"pots":%d,"ebpf":"%s","jett_allow":%s,"jett_review":%s,"jett_quar":%s,"jett_mode":"%s","feed":%s}\n' \
  "$kver" "$kname" "$taintlbl" "$lsm" "$gov" "$vuln" "$safe" "$load" "$procs" "$entropy" "$up" "$ctx" \
  "$jett_on" "$bifrost_on" "$meli_on" "$dock_on" "$pots" "$ebpf" \
  "$jett_allow" "$jett_review" "$jett_quar" "$jett_mode" "$feed_json"
