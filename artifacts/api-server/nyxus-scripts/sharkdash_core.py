#!/usr/bin/env python3
"""
sharkdash_core — Real data collectors for SharkDash v2.0  (13-page edition)
Every function reads live from nyx-cosmic. No mock data.
"""
from __future__ import annotations
import os, time, glob, shutil, subprocess, json, re, logging, sqlite3, socket
from pathlib import Path
from dataclasses import dataclass

log = logging.getLogger("sharkdash.core")

HOME  = Path(os.path.expanduser("~"))
STATE = HOME / ".cache" / "sharkdash"
DATA  = HOME / ".local" / "share" / "sharkdash"
STATE.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

# ── Internal helpers ────────────────────────────────────────────────────────
def _run(cmd, timeout=4) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""

def _read(path, default="") -> str:
    try:
        with open(path) as f: return f.read().strip()
    except Exception: return default

def _port_open(port:int, host="127.0.0.1", timeout=0.8) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close(); return True
    except Exception: return False

def _ping(host:str, timeout=1) -> tuple[bool,float]:
    """Returns (alive, latency_ms)."""
    try:
        r = subprocess.run(
            ["ping","-c","1","-W",str(timeout),host],
            capture_output=True, text=True, timeout=timeout+1)
        if r.returncode == 0:
            m = re.search(r"time=([0-9.]+)", r.stdout)
            return True, float(m.group(1)) if m else 0.0
        return False, 0.0
    except Exception:
        return False, 0.0

# ── CPU ────────────────────────────────────────────────────────────────────
_prev_cpu: dict = {}

def cpu_usage() -> dict:
    global _prev_cpu
    out: dict = {}
    try:
        with open("/proc/stat") as f:
            for line in f:
                if not line.startswith("cpu"): break
                p = line.split(); name = p[0]
                vals = list(map(int, p[1:8]))
                idle = vals[3]+vals[4]; total = sum(vals)
                pi,pt = _prev_cpu.get(name,(idle,total))
                dt=total-pt; di=idle-pi
                pct=(100.0*(dt-di)/dt) if dt>0 else 0.0
                out[name] = max(0.0, min(100.0, pct))
                _prev_cpu[name] = (idle, total)
    except Exception: pass
    return out

def cpu_freq_ghz() -> list[float]:
    fs = sorted(glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq"))
    vals=[]
    for f in fs:
        v=_read(f)
        if v.isdigit(): vals.append(int(v)/1e6)
    return vals

def cpu_freq_range() -> dict:
    mins,maxs,curs=[],[],[]
    for cpu_dir in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq"):
        for lst,fn in ((mins,"scaling_min_freq"),(maxs,"scaling_max_freq"),(curs,"scaling_cur_freq")):
            v=_read(f"{cpu_dir}/{fn}")
            if v.isdigit(): lst.append(int(v)/1e6)
    return dict(min_ghz=min(mins) if mins else 0.0,
                max_ghz=max(maxs) if maxs else 0.0,
                cur_ghz=sum(curs)/len(curs) if curs else 0.0,
                cores=len(curs))

def cpu_model() -> str:
    for line in _read("/proc/cpuinfo").splitlines():
        if "model name" in line: return line.split(":",1)[1].strip()
    return "CPU"

def loadavg() -> tuple:
    try: return os.getloadavg()
    except Exception: return (0,0,0)

def uptime_seconds() -> float:
    try: return float(_read("/proc/uptime").split()[0])
    except Exception: return 0.0

def uptime_str() -> str:
    s=int(uptime_seconds()); d,s=divmod(s,86400); h,s=divmod(s,3600); m,s=divmod(s,60)
    return f"{d}d {h:02d}:{m:02d}:{s:02d}" if d else f"{h:02d}:{m:02d}:{s:02d}"

def iowait() -> float:
    """Return current iowait percentage from /proc/stat cpu line."""
    try:
        with open("/proc/stat") as f:
            line=f.readline()
        vals=list(map(int,line.split()[1:8]))
        total=sum(vals)
        if total<1: return 0.0
        return 100.0*vals[4]/total
    except Exception: return 0.0

# ── TEMPS / FANS ───────────────────────────────────────────────────────────
def _hwmon_by_name() -> dict:
    m={}
    for h in glob.glob("/sys/class/hwmon/hwmon*"):
        m.setdefault(_read(os.path.join(h,"name")),h)
    return m

def temps() -> dict:
    hw=_hwmon_by_name(); out={}
    ct=hw.get("coretemp")
    if ct:
        for lbl in glob.glob(os.path.join(ct,"temp*_label")):
            name=_read(lbl); base=lbl.replace("_label","_input")
            v=_read(base)
            if v.isdigit():
                if name.startswith("Package"): out["cpu_pkg"]=int(v)/1000
                elif name.startswith("Core"): out.setdefault("cores",[]).append(int(v)/1000)
        # TJ max
        for crit_f in glob.glob(os.path.join(ct,"temp1_crit")):
            cv=_read(crit_f)
            if cv.isdigit(): out["cpu_tj_max"]=int(cv)/1000
    if "cpu_tj_max" not in out: out["cpu_tj_max"]=100.0
    nv=hw.get("nvme")
    if nv:
        v=_read(os.path.join(nv,"temp1_input"))
        if v.isdigit(): out["nvme"]=int(v)/1000
    wifi=hw.get("iwlwifi_1")
    if wifi:
        v=_read(os.path.join(wifi,"temp1_input"))
        if v.isdigit(): out["wifi"]=int(v)/1000
    return out

def fans() -> list[int]:
    hw=_hwmon_by_name(); out=[]
    plat=hw.get("msi_wmi_platform")
    if plat:
        for f in sorted(glob.glob(os.path.join(plat,"fan*_input"))):
            v=_read(f)
            if v.isdigit(): out.append(int(v))
    return out

# ── MEMORY ─────────────────────────────────────────────────────────────────
def mem() -> dict:
    info={}
    for line in _read("/proc/meminfo").splitlines():
        k,_,v=line.partition(":")
        info[k]=int(v.strip().split()[0])*1024
    total=info.get("MemTotal",0); avail=info.get("MemAvailable",0); used=total-avail
    return dict(total=total,used=used,avail=avail,cached=info.get("Cached",0),
                free=info.get("MemFree",0),
                swap_total=info.get("SwapTotal",0),
                swap_used=info.get("SwapTotal",0)-info.get("SwapFree",0),
                pct=(100.0*used/total if total else 0))

# ── DISK ───────────────────────────────────────────────────────────────────
_prev_disk: dict = {}

def disks() -> list[dict]:
    out=[]; seen=set()
    try:
        with open("/proc/mounts") as f:
            mounts=[(p.split()[1],p.split()[2]) for p in f if p.split() and p.split()[0].startswith("/dev/")]
    except Exception:
        mounts=[("/","ext4"),("/boot","vfat")]
    for mount,fstype in mounts:
        if mount in seen or any(mount.startswith(x) for x in ("/sys","/proc","/dev","/run")): continue
        seen.add(mount)
        try:
            u=shutil.disk_usage(mount)
            out.append(dict(mount=mount,fstype=fstype,total=u.total,used=u.used,
                            free=u.free,pct=100.0*u.used/u.total if u.total else 0))
        except Exception: pass
    return out

def disk_io() -> dict:
    global _prev_disk
    now=time.time(); rd=wr=0
    try:
        with open("/proc/diskstats") as f:
            for line in f:
                p=line.split(); name=p[2]
                if re.match(r"(nvme\d+n\d+|sd[a-z]|mmcblk\d+)$",name):
                    rd+=int(p[5])*512; wr+=int(p[9])*512
    except Exception: pass
    pr,pw,pt=_prev_disk.get("v",(rd,wr,now))
    dt=now-pt or 1; _prev_disk["v"]=(rd,wr,now)
    return dict(read=max(0,(rd-pr)/dt),write=max(0,(wr-pw)/dt))

# ── NETWORK ────────────────────────────────────────────────────────────────
_prev_net: dict = {}

def net(iface=None) -> dict:
    if iface is None:
        iface=_run(["bash","-lc","ip route get 1.1.1.1 2>/dev/null | grep -oP 'dev \\K\\S+' | head -1"]) or "enp47s0"
    now=time.time(); rx=tx=0
    try:
        with open("/proc/net/dev") as f:
            for line in f:
                if ":"+iface in line or line.strip().startswith(iface+":"):
                    name,data=line.split(":",1)
                    if name.strip()==iface:
                        d=data.split(); rx=int(d[0]); tx=int(d[8])
    except Exception: pass
    pr,pt2,pt=_prev_net.get(iface,(rx,tx,now)); dt=now-pt or 1
    _prev_net[iface]=(rx,tx,now)
    return dict(iface=iface,down=max(0,(rx-pr)/dt),up=max(0,(tx-pt2)/dt),total_rx=rx,total_tx=tx)

def all_interfaces() -> list[dict]:
    ifaces=[]
    try:
        with open("/proc/net/dev") as f:
            for line in f:
                if ":" in line:
                    name=line.split(":")[0].strip()
                    if name!="lo": ifaces.append(net(name))
    except Exception: pass
    return ifaces

# ── GPU ─────────────────────────────────────────────────────────────────────
def _f(x,d=0.0):
    try: return float(str(x).strip())
    except Exception: return d

def gpu() -> dict:
    out={}
    q=_run(["nvidia-smi","--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit,clocks.gr,clocks.mem","--format=csv,noheader,nounits"])
    if q and "," in q:
        p=[x.strip() for x in q.split(",")]
        if len(p)>=7:
            vt=_f(p[4])
            out["nvidia"]=dict(name=p[0],temp=_f(p[1]),util=_f(p[2]),
                               vram_used=_f(p[3]),vram_total=vt,
                               watts=_f(p[5]),watt_limit=_f(p[6]) if len(p)>6 else 0,
                               clock_gr=_f(p[7]) if len(p)>7 else 0,
                               clock_mem=_f(p[8]) if len(p)>8 else 0,
                               vram_pct=100.0*_f(p[3])/vt if vt else 0)
    if os.path.exists("/sys/class/drm/card0"):
        out["intel"]=dict(name="Intel iGPU",note="no util counter")
    return out

def vram_by_pid() -> dict:
    out=_run(["nvidia-smi","--query-compute-apps=pid,used_memory","--format=csv,noheader,nounits"])
    m={}
    for line in out.splitlines():
        p=[x.strip() for x in line.split(",")]
        if len(p)>=2 and p[0].isdigit(): m[p[0]]=int(p[1] or 0)
    return m

# ── BATTERY ────────────────────────────────────────────────────────────────
def battery() -> dict|None:
    base="/sys/class/power_supply"; bat=None
    for b in glob.glob(f"{base}/BAT*"):
        cap=_read(f"{b}/capacity"); st=_read(f"{b}/status")
        if cap.isdigit(): bat=dict(pct=int(cap),status=st)
    ac=_read(f"{base}/ADP1/online") or _read(f"{base}/AC/online")
    if bat is not None: bat["ac"]=ac=="1"
    return bat

# ── PROCESSES ──────────────────────────────────────────────────────────────
def top_procs(n=30, by="cpu") -> list[dict]:
    sort="-%cpu" if by=="cpu" else "-%mem"
    out=_run(["ps","-eo","pid,comm,%cpu,%mem,rss,user,nlwp","--sort",sort])
    vram_m=vram_by_pid(); rows=[]
    for line in out.splitlines()[1:n+1]:
        p=line.split(None,6)
        if len(p)>=6:
            pid=p[0]
            rows.append(dict(pid=pid,name=p[1],cpu=p[2],mem=p[3],
                             rss_mb=int(p[4])//1024,user=p[5],
                             threads=p[6].strip() if len(p)>6 else "?",
                             vram_mb=vram_m.get(pid,0)))
    return rows

# ── SERVICES ───────────────────────────────────────────────────────────────
USER_SVCS=["gowskinet-honeyhive","gowskinet-honeyhive-web","gowskinet-honeyhive-alerter",
           "homoousios-daemon","honeypot-ledger","meli-ingest","rclone-gdrive",
           "gowski-maze","glpayroll-site","cowrie-bridge","conpot-bridge",
           "dionaea-bridge","endlessh-bridge"]
SYS_SVCS=["mosquitto","docker","postgresql"]
DOCKERS=["cowrie","dionaea","conpot","heralding","endlessh","http-honeypot",
         "loki","prometheus","grafana","promtail"]

_svc_cache:dict={"data":None,"stamp":0}

def services(ttl=20) -> dict:
    now=time.time()
    if _svc_cache["data"] is not None and now-_svc_cache["stamp"]<ttl:
        return _svc_cache["data"]
    res={"user":{},"system":{},"docker":{}}
    for s in USER_SVCS:
        res["user"][s]=_run(["systemctl","--user","is-active",f"{s}.service"]) or "unknown"
    for s in SYS_SVCS:
        res["system"][s]=_run(["systemctl","is-active",f"{s}.service"]) or "unknown"
    ps=_run(["docker","ps","--format","{{.Names}} {{.State}} {{.Status}} {{.Ports}}"])
    state={}
    for line in ps.splitlines():
        q=line.split(None,3)
        if len(q)>=2: state[q[0]]={"state":q[1],"status":q[2] if len(q)>2 else "","ports":q[3] if len(q)>3 else ""}
    for c in DOCKERS:
        res["docker"][c]=state.get(c,{"state":"absent","status":"","ports":""})
    _svc_cache["data"]=res; _svc_cache["stamp"]=now
    return res

def docker_containers_full() -> list[dict]:
    """All docker containers with full details."""
    out=_run(["docker","ps","-a","--format","{{.Names}}\t{{.Image}}\t{{.State}}\t{{.Status}}\t{{.Ports}}"])
    rows=[]
    for line in out.splitlines():
        p=line.split("\t")
        if len(p)>=4:
            rows.append(dict(name=p[0],image=p[1] if len(p)>1 else "",
                             state=p[2] if len(p)>2 else "",
                             status=p[3] if len(p)>3 else "",
                             ports=p[4] if len(p)>4 else ""))
    return rows

# ── EVENTS ─────────────────────────────────────────────────────────────────
_events_cache:dict={"data":None,"stamp":0}

def events(ttl=90) -> dict:
    now=time.time()
    if _events_cache["data"] is not None and now-_events_cache["stamp"]<ttl:
        return _events_cache["data"]
    last=_run(["last","-x","--time-format","iso"])
    reboots=sum(1 for l in last.splitlines() if l.startswith("reboot"))
    shutdowns=sum(1 for l in last.splitlines() if l.startswith("shutdown"))
    crashes=sum(1 for l in last.splitlines() if "crash" in l)
    logins=sum(1 for l in last.splitlines() if l.startswith("cosmic"))
    af=_run(["bash","-lc",'journalctl --since "-2 days" --no-pager -q 2>/dev/null | grep -aciE "Failed password|authentication failure"'],timeout=8)
    rootses=_run(["bash","-lc",'journalctl --since "today" --no-pager -q 2>/dev/null | grep -aci "session opened for user root"'],timeout=8)
    sudo=_run(["bash","-lc",'journalctl _COMM=sudo --since "today" --no-pager -q 2>/dev/null | grep -ac "COMMAND="'],timeout=8)
    data=dict(reboots=reboots,shutdowns=shutdowns,crashes=crashes,logins=logins,
              auth_fail_2d=int(af or 0),root_sessions_today=int(rootses or 0),sudo_today=int(sudo or 0))
    _events_cache["data"]=data; _events_cache["stamp"]=now
    return data

_act_cache:dict={"data":[],"stamp":0}

def activity_feed(n=30,ttl=8) -> list[dict]:
    now=time.time()
    if _act_cache["data"] and now-_act_cache["stamp"]<ttl:
        return _act_cache["data"]
    raw=_run(["bash","-lc",
        'journalctl --no-pager -q -n 80 -o short-precise 2>/dev/null '
        '| grep -aiE "sudo|session opened|session closed|Failed password|'
        'started|stopped|docker|nvidia|usb|bluetooth|oom|error|killed|jett|bifrost"'
        f' | tail -{n}'],timeout=6)
    feed=[]
    for l in raw.splitlines()[-n:]:
        parts=l.split(None,4)
        if len(parts)>=5:
            ts=parts[2][:8]; msg=parts[4]; lvl="info"
            ml=msg.lower()
            if any(w in ml for w in ("fail","error","oom","killed","refused","crit")): lvl="warn"
            if any(w in ml for w in ("panic","emerg","quarantine","attack")): lvl="crit"
            if any(w in ml for w in ("started","opened","connected","allow")): lvl="ok"
            feed.append(dict(t=ts,msg=msg[:240],lvl=lvl))
    _act_cache["data"]=feed; _act_cache["stamp"]=now
    return feed

# ── BLUETOOTH / AUDIO ──────────────────────────────────────────────────────
def bluetooth() -> dict:
    s=_run(["bluetoothctl","show"])
    powered="Powered: yes" in s; name=""
    for l in s.splitlines():
        if "Name:" in l: name=l.split("Name:",1)[1].strip()
    conn=_run(["bash","-lc","bluetoothctl devices Connected 2>/dev/null | wc -l"])
    return dict(powered=powered,name=name,connected=int(conn or 0))

def audio() -> dict:
    s=_run(["wpctl","status"]); default=""
    for l in s.splitlines():
        if "*" in l and "." in l and "Sink" not in l:
            default=l.split("*",1)[1].strip()[:48]; break
    return dict(default=default or "n/a")

# ── PROJECTS ───────────────────────────────────────────────────────────────
PROJECT_SIGS=[("jett","jett-daemon"),("bifrost","bifrost.guardian"),
              ("meli","/opt/meli/"),("maze","gowski-maze"),("honeyhive","honeyhive")]

_proj_cache:dict={"data":[],"stamp":0}

def projects_detail(ttl=30) -> list[dict]:
    now=time.time()
    if _proj_cache["data"] and now-_proj_cache["stamp"]<ttl:
        return _proj_cache["data"]
    out=_run(["ps","-eo","pid,%cpu,rss,args","--no-headers"])
    vram=vram_by_pid(); found={}
    for line in out.splitlines():
        parts=line.split(None,3)
        if len(parts)<4: continue
        pid,cpu,rss,args=parts
        for name,sig in PROJECT_SIGS:
            if name in found: continue
            if sig in args:
                found[name]=dict(name=name,up=True,pid=pid,cpu=float(cpu),
                                 mem_mb=int(rss)//1024,vram_mb=vram.get(pid,0))
    res=[]
    for name,_ in PROJECT_SIGS:
        entry=found.get(name,dict(name=name,up=False,pid="-",cpu=0.0,mem_mb=0,vram_mb=0))
        # Git info
        pdir=HOME/"Projects"/name
        if not pdir.exists():
            for p in (HOME/"Projects").glob("*"):
                if name.lower() in p.name.lower() and p.is_dir(): pdir=p; break
        if pdir.exists():
            entry["branch"]=_run(["git","-C",str(pdir),"rev-parse","--abbrev-ref","HEAD"],timeout=2)
            entry["last_commit"]=_run(["git","-C",str(pdir),"log","-1","--format=%h %ar %s"],timeout=2)[:70]
            dirty=_run(["git","-C",str(pdir),"status","--porcelain"],timeout=2)
            entry["dirty_files"]=len(dirty.splitlines()) if dirty else 0
            # Size
            try:
                sz=sum(f.stat().st_size for f in pdir.rglob("*") if f.is_file() and ".git" not in str(f))
                entry["size_mb"]=sz//1048576
            except Exception: entry["size_mb"]=0
        else:
            entry["branch"]=""; entry["last_commit"]=""; entry["dirty_files"]=0; entry["size_mb"]=0
        res.append(entry)
    _proj_cache["data"]=res; _proj_cache["stamp"]=now
    return res

def projects_dir_sizes() -> list[dict]:
    """All ~/Projects sorted by size."""
    pdir=HOME/"Projects"
    if not pdir.exists(): return []
    result=[]
    for p in pdir.iterdir():
        if not p.is_dir(): continue
        try:
            sz=sum(f.stat().st_size for f in p.rglob("*") if f.is_file() and ".git" not in str(f))
        except Exception: sz=0
        branch=_run(["git","-C",str(p),"rev-parse","--abbrev-ref","HEAD"],timeout=1)
        last_commit=_run(["git","-C",str(p),"log","-1","--format=%h %ar"],timeout=1)
        dirty=_run(["git","-C",str(p),"status","--porcelain"],timeout=1)
        result.append(dict(name=p.name,size_mb=sz//1048576,branch=branch,
                           last_commit=last_commit[:40],dirty=len(dirty.splitlines()) if dirty else 0))
    return sorted(result,key=lambda x:x["size_mb"],reverse=True)

# ── HONEYPOTS ──────────────────────────────────────────────────────────────
_hp_cache:dict={"data":None,"stamp":0}

def honeypots(ttl=30) -> dict:
    now=time.time()
    if _hp_cache["data"] is not None and now-_hp_cache["stamp"]<ttl:
        return _hp_cache["data"]
    up=set()
    raw=_run(["bash","-lc","docker ps --format '{{.Names}}' 2>/dev/null"])
    for n in raw.splitlines(): up.add(n.strip())
    logdir=HOME/"Projects"/"honeypot"/"logs"; pots={}; today=time.strftime("%Y-%m-%d")

    # Cowrie
    ct=cr=0
    try:
        cdir=logdir/"cowrie"
        if cdir.exists():
            for jf in sorted(cdir.glob("cowrie.json*")):
                n=sum(1 for l in open(jf,errors="ignore") if '"cowrie.session.connect"' in l)
                cr+=n
                if jf.name=="cowrie.json" or today in jf.name: ct+=n
    except Exception: pass
    pots["cowrie"]=dict(up=("cowrie" in up),today=ct,recent=cr,active=0,notes="SSH honeypot",has_hits=True)

    for pot,note in [("dionaea","Malware honeypot"),("conpot","ICS honeypot"),
                     ("endlessh","SSH tarpit"),("heralding","Multi-protocol"),
                     ("http-honeypot","Web trap")]:
        pots[pot]=dict(up=(pot in up),today=None,recent=None,active=0,notes=note,has_hits=False)

    # GowskiMaze
    maze_db=HOME/"Projects"/"archive"/"gowski-maze"/"maze.db"
    maze_today=maze_total=maze_active=maze_bytes=0
    if maze_db.exists():
        try:
            conn=sqlite3.connect(str(maze_db),timeout=1)
            maze_active=conn.execute("SELECT COUNT(*) FROM sessions WHERE active=1").fetchone()[0]
            maze_total=conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            maze_bytes=conn.execute("SELECT COALESCE(SUM(bytes_sent),0) FROM sessions").fetchone()[0]
            conn.close()
        except Exception: pass
    pots["gowski-maze"]=dict(up=("gowski-maze" in up or _port_open(8001)),
                              today=maze_today,recent=maze_total,
                              active=maze_active,bytes_sent=maze_bytes,
                              notes="Payroll tarpit",has_hits=True)
    total_hits=ct+maze_total
    res=dict(pots=pots,up=sum(1 for p in pots.values() if p["up"]),total=len(pots),
             hits_today=ct+maze_today,hits_recent=total_hits)
    _hp_cache["data"]=res; _hp_cache["stamp"]=now
    return res

def top_attacking_ips(n=5) -> list[dict]:
    """Top attacking IPs today from cowrie logs."""
    logdir=HOME/"Projects"/"honeypot"/"logs"/"cowrie"
    counts:dict={}
    if logdir.exists():
        try:
            for jf in sorted(logdir.glob("cowrie.json*"))[-2:]:
                for line in open(jf,errors="ignore"):
                    if '"src_ip"' in line:
                        m=re.search(r'"src_ip":\s*"([^"]+)"',line)
                        if m: counts[m.group(1)]=counts.get(m.group(1),0)+1
        except Exception: pass
    return sorted([dict(ip=k,hits=v) for k,v in counts.items()],key=lambda x:x["hits"],reverse=True)[:n]

# ── jeTT AI EDR ────────────────────────────────────────────────────────────
_jett_cache:dict={"data":{},"stamp":0}

def jett_status(ttl=5) -> dict:
    now=time.time()
    if _jett_cache["data"] and now-_jett_cache["stamp"]<ttl:
        return _jett_cache["data"]
    base=dict(up=False,verdicts=0,allow=0,block=0,quarantine=0,
              latency_ms=0,model="n/a",ebpf=False,learn_mode=False,pid="")
    for port in (8765,9999,7070):
        if _port_open(port):
            try:
                import urllib.request, json as _j
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/status",timeout=1) as r:
                    data=_j.loads(r.read())
                    data["up"]=True
                    _jett_cache["data"]=data; _jett_cache["stamp"]=now
                    return data
            except Exception: break
    # Fallback: check process
    ps=_run(["pgrep","-a","jett"])
    if ps:
        base["up"]=True; base["model"]="local"; base["pid"]=ps.split()[0]
    _jett_cache["data"]=base; _jett_cache["stamp"]=now
    return base

def jett_verdict_stream(n=20) -> list[dict]:
    """Recent jeTT verdicts from log."""
    vlog=HOME/".local"/"share"/"sharkdash"/"jett-verdicts.log"
    if vlog.exists():
        try:
            lines=vlog.read_text().splitlines()[-n:]
            out=[]
            for line in lines:
                # Format: ts pid name verdict reason
                p=line.split("\t")
                if len(p)>=4:
                    out.append(dict(ts=p[0],pid=p[1],name=p[2],verdict=p[3],reason=p[4] if len(p)>4 else ""))
            return out
        except Exception: pass
    # Fallback: journalctl grep
    raw=_run(["bash","-lc",'journalctl -u jett-daemon --no-pager -n 20 -q 2>/dev/null'],timeout=5)
    out=[]
    for line in raw.splitlines():
        if any(v in line.upper() for v in ("ALLOW","BLOCK","QUARANTINE")):
            m=re.search(r"(ALLOW|BLOCK|QUARANTINE)",line,re.I)
            verdict=m.group(1).upper() if m else "UNKNOWN"
            out.append(dict(ts=line[:8] if len(line)>8 else "",pid="?",name="?",verdict=verdict,reason=line[20:80]))
    return out[-n:]

# ── BIFROST EDR ────────────────────────────────────────────────────────────
def bifrost_status() -> dict:
    base=dict(up=False,pid="",uptime_s=0,last_event="",last_event_ts=0,
              traps_active=0,traps_triggered=0,discord_connected=False,
              sms_connected=False,analyst_model=False,modules={})
    if _port_open(8766):
        try:
            import urllib.request, json as _j
            with urllib.request.urlopen("http://127.0.0.1:8766/status",timeout=1) as r:
                return {**base,**_j.loads(r.read()),"up":True}
        except Exception: pass
    # Check process
    ps=_run(["pgrep","-a","bifrost"])
    if ps: base["up"]=True; base["pid"]=ps.split()[0]
    return base

def bifrost_events(n=10) -> list[dict]:
    raw=_run(["bash","-lc",'journalctl -u bifrost-guardian --no-pager -n 20 -q 2>/dev/null'],timeout=5)
    out=[]
    for line in raw.splitlines()[-n:]:
        out.append(dict(ts=line[:8] if len(line)>8 else "",msg=line[20:] if len(line)>20 else line))
    return out

# ── VIRTUAL MACHINES (VirtualBox) ─────────────────────────────────────────
_VM_INFO={
    "bifrost-test":  dict(ram_mb=4096,cpus=2,net="NAT",ssh="localhost:2222",creds="nyx/123456"),
    "bifrost-test2": dict(ram_mb=8192,cpus=2,net="Host-only+NAT",ssh="127.0.0.1:3333",creds="bifrost/bifrost123"),
    "lab-attacker":  dict(ram_mb=4096,cpus=2,net="Host-only",ssh="",creds=""),
}

def virtualbox_vms() -> list[dict]:
    out=_run(["VBoxManage","list","vms"])
    if not out: return []
    vms=[]
    for line in out.splitlines():
        m=re.match(r'"([^"]+)"\s+\{([^}]+)\}',line)
        if not m: continue
        name=m.group(1); uuid=m.group(2)
        info=_run(["VBoxManage","showvminfo",name,"--machinereadable"])
        state="unknown"; last_change=""
        for il in info.splitlines():
            if il.startswith("VMState="): state=il.split("=",1)[1].strip().strip('"')
            if il.startswith("VMStateChangeTime="): last_change=il.split("=",1)[1].strip().strip('"')
        extra=_VM_INFO.get(name,{})
        vms.append(dict(name=name,uuid=uuid,state=state,last_change=last_change,**extra))
    return vms

def vm_action(vm_name:str, action:str) -> str:
    """start|stop|pause|reset|poweroff"""
    cmd_map={"start":["startvm",vm_name],"stop":["controlvm",vm_name,"savestate"],
             "pause":["controlvm",vm_name,"pause"],"reset":["controlvm",vm_name,"reset"],
             "poweroff":["controlvm",vm_name,"poweroff"]}
    if action not in cmd_map: return f"Unknown action: {action}"
    return _run(["VBoxManage"]+cmd_map[action],timeout=10) or "OK"

# ── LAB NODES ──────────────────────────────────────────────────────────────
LAB_NODES={
    "Pi Zero W2":  dict(ip="192.168.0.125",role="Cowrie host"),
    "Pi5 Kali":    dict(ip="192.168.0.80", role="Attack lab"),
    "GNI Skull":   dict(ip="192.168.0.100",role="GNI/Claude"),
    "Router":      dict(ip="192.168.0.1",  role="TP-Link BE3600"),
    "Apple TV":    dict(ip="192.168.0.110",role="Media"),
}

_lab_cache:dict={"data":{},"stamp":0}

def lab_nodes(ttl=30) -> dict:
    now=time.time()
    if _lab_cache["data"] and now-_lab_cache["stamp"]<ttl:
        return _lab_cache["data"]
    result={}
    for name,info in LAB_NODES.items():
        alive,lat=_ping(info["ip"])
        extra={}
        if alive:
            if name=="Pi Zero W2": extra["cowrie"]=_port_open(2222,info["ip"])
            if name=="GNI Skull":
                extra["gni_web"]=_port_open(6969,"127.0.0.1")
                extra["claude_api"]=bool(os.environ.get("ANTHROPIC_API_KEY"))
        result[name]=dict(alive=alive,lat_ms=lat,**info,**extra)
    # Extra services
    result["_wireguard"]=wireguard_status()
    result["_fail2ban"]=fail2ban_status()
    result["_ufw"]=ufw_status()
    result["_portainer"]=_port_open(9443)
    result["_prometheus"]=_port_open(9090)
    result["_grafana"]=_port_open(3000)
    _lab_cache["data"]=result; _lab_cache["stamp"]=now
    return result

def wireguard_status() -> dict:
    out=_run(["sudo","-n","wg","show"],timeout=3)
    if not out: return dict(up=False,peers=0,pubkey="")
    iface_m=re.search(r"interface:\s+(\S+)",out)
    peers=len(re.findall(r"^peer:",out,re.M))
    pubkey_m=re.search(r"public key:\s+(\S+)",out)
    return dict(up=True,iface=iface_m.group(1) if iface_m else "wg0",
                peers=peers,pubkey=pubkey_m.group(1)[:12]+"…" if pubkey_m else "")

def fail2ban_status() -> dict:
    out=_run(["sudo","-n","fail2ban-client","status"],timeout=3)
    bans=0; last_ip=""
    if out:
        m=re.search(r"Currently banned:\s+(\d+)",out)
        if m: bans=int(m.group(1))
    return dict(bans=bans,last_ip=last_ip)

def ufw_status() -> dict:
    out=_run(["sudo","-n","ufw","status","verbose"],timeout=3)
    active="Status: active" in out
    blocks=len(re.findall(r"DENY",out))
    return dict(active=active,blocks=blocks)

# ── BANDWIDTH ACCOUNTING ───────────────────────────────────────────────────
_bw_file=DATA/"bandwidth.json"

def bandwidth_snapshot() -> dict:
    today=time.strftime("%Y-%m-%d")
    try: existing=json.loads(_bw_file.read_text()) if _bw_file.exists() else {}
    except Exception: existing={}
    if existing.get("date")!=today: existing={"date":today,"interfaces":{}}
    for iface_data in all_interfaces():
        name=iface_data["iface"]; rx=iface_data["total_rx"]; tx=iface_data["total_tx"]
        prev=existing["interfaces"].get(name,{"rx_start":rx,"tx_start":tx})
        existing["interfaces"][name]={"rx_start":prev["rx_start"],"tx_start":prev["tx_start"],
                                       "rx_today":max(0,rx-prev["rx_start"]),
                                       "tx_today":max(0,tx-prev["tx_start"])}
    try: _bw_file.write_text(json.dumps(existing))
    except Exception: pass
    return existing

# ── SHARKSCORE ─────────────────────────────────────────────────────────────
def sharkscore() -> dict:
    score=0; detail={}
    t=temps(); pkg=t.get("cpu_pkg",0); tj=t.get("cpu_tj_max",100)
    headroom=max(0,(tj-pkg)/tj) if tj else 1.0
    detail["temp"]=round(headroom*30,1); score+=detail["temp"]
    ncpus=os.cpu_count() or 1; la=loadavg()
    detail["load"]=round(max(0,(1-min(la[0]/ncpus,2)/2))*20,1); score+=detail["load"]
    m=mem(); detail["mem"]=round(max(0,(1-m.get("pct",0)/100))*15,1); score+=detail["mem"]
    hp=honeypots(); pot_ratio=hp["up"]/max(hp["total"],1)
    detail["honeypots"]=round(pot_ratio*10,1); score+=detail["honeypots"]
    g=gpu(); nv=g.get("nvidia",{})
    detail["gpu"]=round(max(0,(1-nv.get("util",0)/100))*10,1) if nv else 10.0; score+=detail["gpu"]
    svcs=services(); active=sum(1 for v in svcs["user"].values() if v=="active")
    detail["services"]=round((active/max(len(svcs["user"]),1))*15,1); score+=detail["services"]
    grade="A" if score>=90 else "B" if score>=75 else "C" if score>=60 else "D" if score>=45 else "F"
    return dict(score=round(score,1),grade=grade,detail=detail)

# ── AUTO PERFORMANCE MODE ──────────────────────────────────────────────────
def auto_perf_tier() -> dict:
    la=loadavg()[0]
    if la<3:   return dict(tier="idle",   load=la,governor="powersave",  fan="silent",  color="ok")
    if la<10:  return dict(tier="normal", load=la,governor="schedutil",  fan="auto",    color="ok")
    if la<20:  return dict(tier="high",   load=la,governor="performance",fan="advanced",color="warn")
    return         dict(tier="max",    load=la,governor="performance",fan="cooler_boost",color="crit")

# ── PREDICTIVE HORIZON (BONUS FEATURE) ─────────────────────────────────────
def predict_trend(history:list[float], minutes_ahead:int=60) -> dict:
    """
    Linear regression over history to predict future value.
    Returns predicted value, confidence, and direction.
    """
    n=len(history)
    if n<5: return dict(predicted=history[-1] if history else 0,confidence=0,direction="stable",eta_min=None)
    xs=list(range(n)); xm=sum(xs)/n; ym=sum(history)/n
    num=sum((x-xm)*(y-ym) for x,y in zip(xs,history))
    den=sum((x-xm)**2 for x in xs)
    slope=(num/den) if den else 0
    # Project forward (each unit = 1 sample ≈ 1 second)
    predicted=history[-1]+slope*minutes_ahead*60
    predicted=max(0,min(100,predicted))
    # Confidence based on R²
    y_pred=[ym+slope*(x-xm) for x in xs]
    ss_res=sum((y-yp)**2 for y,yp in zip(history,y_pred))
    ss_tot=sum((y-ym)**2 for y in history) or 1
    r2=max(0,1-ss_res/ss_tot)
    direction="rising" if slope>0.01 else "falling" if slope<-0.01 else "stable"
    # ETA to threshold (95% for temp, 90% for cpu/mem)
    eta_min=None
    if slope>0 and history[-1]<90:
        steps=(90-history[-1])/slope
        eta_min=round(steps/60,1)
    return dict(predicted=round(predicted,1),confidence=round(r2*100,0),
                direction=direction,slope_per_min=round(slope*60,3),eta_min=eta_min)

# ── RUNPOD / BAMBU ─────────────────────────────────────────────────────────
def runpod_status() -> dict:
    """Check RunPod pod via API if RUNPOD_API_KEY is set."""
    key=os.environ.get("RUNPOD_API_KEY","")
    pod_id="7oeks6znx6r2fh"
    if not key: return dict(pod_id=pod_id,state="unknown",cost_hr=0.44,api_key_set=False)
    try:
        import urllib.request, json as _j
        req=urllib.request.Request(
            f"https://api.runpod.io/graphql?api_key={key}",
            method="POST",
            headers={"Content-Type":"application/json"},
            data=json.dumps({"query":f'{{pod(id:"{pod_id}"){{desiredStatus costPerHr}}}}'}).encode()
        )
        with urllib.request.urlopen(req,timeout=3) as r:
            d=_j.loads(r.read()); pod=d.get("data",{}).get("pod",{})
            return dict(pod_id=pod_id,state=pod.get("desiredStatus","unknown"),
                        cost_hr=pod.get("costPerHr",0.44),api_key_set=True)
    except Exception: pass
    return dict(pod_id=pod_id,state="unknown",cost_hr=0.44,api_key_set=bool(key))

def bambu_status() -> dict:
    ips=["192.168.0.50","192.168.1.50","bambulab.local"]
    for ip in ips:
        alive,lat=_ping(ip,timeout=1)
        if alive: return dict(found=True,ip=ip,lat_ms=lat)
    return dict(found=False,ip="",lat_ms=0)

def file_counts_cached() -> dict:
    f=STATE/"filecounts.json"
    try: return json.loads(f.read_text()) if f.exists() else {}
    except Exception: return {}

def jett_full_stats() -> dict:
    """Extended jeTT stats for the dedicated page."""
    base=jett_status()
    base["verdict_stream"]=jett_verdict_stream(15)
    return base

# ── Added to bridge sharkctl's expected API to real implementation ─────────

def fan_names() -> list:
    """Returns labeled fan names matching the fans() RPM list order."""
    return ["Fan1", "Fan2", "Fan3", "Fan4"]


def all_sensors() -> dict:
    """Combined snapshot of temps + fans for sharkctl's `temps` subcommand."""
    return {
        "temps": temps(),
        "fans": dict(zip(fan_names(), fans())),
    }


def msi_state() -> dict:
    """Lightweight MSI-EC state reader for shift_mode / super_battery display."""
    try:
        import sharkdash_control as K
        return {
            "shift_mode": K.get_shift_mode(),
            "super_battery": K._read_ec("super_battery", "?"),
        }
    except Exception:
        return {"shift_mode": "?", "super_battery": "?"}
