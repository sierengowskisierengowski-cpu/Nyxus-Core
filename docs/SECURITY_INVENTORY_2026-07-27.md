# NYXUS Security Inventory — 2026-07-27

> Owner: Joseph A. Sierengowski · Snapshotted from builder host + Nyxus-Core tip  
> Scope: everything security-related in the distro, Arsenal, Vault, and local Projects.  
> **Do not** treat Pranks as production security tooling.

---

## Live on this builder (at inventory time)

| Component | Status |
|---|---|
| `bifrost-guardian.service` | **active** |
| `jett-daemon.service` | **active** |
| `meli-ingest` (user) | **active** |
| Honeypot Docker stack | **up** (~16h) from `~/Projects/honeypot` — **not** at `/opt/honeypot` |

**Docker containers:** cowrie, heralding, conpot, dionaea, endlessh, http-honeypot, grafana, loki, prometheus, promtail.

---

## 1. Desktop security modes (Nyxus)

| Item | Role | Canonical |
|---|---|---|
| **Hacker Mode** | Desktop transform; surfaces Arsenal | `nyxus-hacker-mode` |
| **Ghost Mode** | Tor + nft kill-switch + MAC randomize | `nyxus-ghost` (+ helper/pkexec) |
| **Panic** | Lock / arm / poweroff | `nyxus-panic` |
| **Security Center** | GTK policy / audit / firewall / AV / panic | `nyxus-security` (`Super+Shift+Y`) |
| **DEEP CORE** | Kernel + stack telemetry overlay | eww `deepcore` (`Super+G`) |
| **GHOST station** | Live security console | station 3 / `Super+3` · `ghost-deck` + `ghost-feed.py` |
| **Shield** | Everyday security GUI | `nyxus-shield` (+ `nyxus-shield.tgz`) |
| **Phantom** | Threat-intel daemon feeding Shield | `nyxus-phantom.tgz` + unit |
| **USB watch / USBGuard** | Device monitoring helpers | `nyxus-usbwatch-event`, `nyxus-usbguard-helper` |
| **VPN / DoH / MAC / secboot** | Network + boot helpers | `nyxus-vpn`, `nyxus-doh`, `nyxus-mac-randomize`, `nyxus-secboot` |
| **Passwords** | Password vault UI | `nyxus-passwords` |
| **BlackArch full** | Post-boot install of entire `blackarch` group | `nyxus-blackarch-full` |

Feeds / bar chips: `eww/scripts/security-state.sh`, `ghost-feed.py`, `lab-feed.py`, `forge-feed.py`, `deepcore.sh`.

---

## 2. Arsenal hub (one roof)

**Commands:** `arsenal` · setup: `~/Arsenal/setup-apps.sh` or `nyxus-setup-apps`  
**Registry:** `~/Arsenal/registry.toml` (mirrored in ISO skel `etc/skel/Arsenal/` + `etc/arsenal/`)

| ID | Name | Purpose |
|---|---|---|
| `jett` | jeTT | Local AI EDR — kernel/proc watchdog (Rust + CUDA) |
| `bifrost` | Bifrost | AI Linux EDR / Heimdall guardian |
| `meli` | Meli | Honeypot command center / event ingest |
| `honeypot` | Honeypot Stack | Cowrie/Heralding/Conpot/Dionaea/Endlessh + Grafana/Loki/Prometheus |
| `axiom` | Axiom | Desktop AI assistant (tray / hotkey / local GPU) |
| `ghost-relay` | Ghost-Relay (c2) | Go operator console / network-relay lab |
| `gsl` | GSL | Personal security-lab dashboard (FastAPI + React) |
| `redforge` | RedForge | Blue-team training — missions / MITRE / AI tutor |
| `forge` | Forge | AI threat research + honeypot feed (Ollama) |
| `cipher` | CIPHER | Password-security lab — strength / hash ID / cracking |
| `trainer` | AI Cyber Defense Trainer | Red/blue operator training + live scenario logs |
| `grafana` | Grafana | Honeypot / metrics dashboards |
| `prometheus` | Prometheus | Metrics / time-series |
| `honeyhive` | HoneyHive Map | Live geo-map of attacker activity |

**ISO note:** training/web tools ship under `/opt/arsenal/tools/<name>` as **source only**. DBs/secrets are not baked. After install run setup once. Re-bake staging: `NYX_STAGE_ARSENAL_APPS=1` from Vault/Projects (see `iso-builder/build-iso.sh`).

**Known gaps:** Arsenal webapps hang on a stick without Vault/`setup-apps`; AXIOM has no wired `nyxus-webapp` backend; some app-shell vs webapp port mismatches historically (see live-boot audits).

---

## 3. GodsApp (`/opt/nyxus-godsapp`) — 30 modules

Launch: `godsapp` / `nyxus-godsapp` · install scripts in NS: `nyxus_godsapp_install.sh`, `nyxus-godsapp.tgz`

| # | Module | # | Module |
|---|---|---|---|
| 01 | Network | 16 | Malware |
| 02 | Ports | 17 | VoIP |
| 03 | Packets | 18 | SCADA |
| 04 | WiFi | 19 | Crypto |
| 05 | Vulns | 20 | Binary |
| 06 | Traffic | 21 | Logs |
| 07 | Attack Surface | 22 | Mobile |
| 08 | OSINT | 23 | Cloud |
| 09 | Password | 24 | Physical |
| 10 | Bluetooth | 25 | Darkweb |
| 11 | USB | 26 | Social |
| 12 | AD | 27 | Automation |
| 13 | Web | 28 | Forensics |
| 14 | MITM | 29 | Godmode |
| 15 | Exploit | 30 | Terminal |

---

## 4. NYXUS Intel (`/opt/nyxus-intel`)

OSINT suite: IP · email · domain · username · person · photo · crypto · records · case manager · reports.  
Install: `nyxus_intel_install.sh` / `nyxus-intel.tgz` · desktop `io.nyxus.intel.desktop`.

---

## 5. Platforms — paths

| Platform | Role | Where |
|---|---|---|
| Bifrost | EDR / Heimdall | `/usr/lib/bifrost`, `/usr/bin/bifrost*`, `nyxus-launch-bifrost` |
| jeTT | AI security daemon | `/usr/local/lib/jett`, `/usr/local/bin/jeTT`, `jett-daemon` |
| Meli | Honeypot CC | `/opt/meli/app`, `meli`, `nyxus-launch-meli` |
| Honeypot stack | Lab pots + observability | Bake → `/opt/honeypot` from `~/Projects/honeypot` |
| Security Center | Policy GUI + daemon | `nyxus_security.py`, `nyxus-security-daemon*` |
| Shield + Phantom | Everyday GUI + intel | tarballs under `artifacts/api-server/nyxus-scripts/` |
| Arsenal tools tree | Web/training apps | `/opt/arsenal/tools/{CIPHER,Forge,RedForge,GSL,AI-Cyber-Defense-Trainer,axiom,c2}` |

**HANDOFF stay-as-is (no ALIEN NEON / Settings rewrite):** Bifrost, GodsApp, Meli, Arsenal, Security Center.

---

## 6. Local source trees (builder host)

### `~/Projects/`
`bifrost` · `jeTT` · `honeypot` · `meli` · `meli-gtk` · `meli-honeypot-web` · `axiom` · `c2` · `godsapp-gtk` · `recon` · `subdue` · `gowskinet-noc` · `insight-hub`

### `~/GowskiNet-Vault/Security/`
`Bifrost` · `CIPHER` · `Forge` · `RedForge` · `GSL` · `honeypot` · `Meli` · `Meli-Honeypot-Web` · `ghost-relay` · `recon` · `Cyber/` (Cyber-Defense-Trainer variants, Cyber-Range, …) · `Pranks/` (Scare-Bomb, Scare-Prank-Sender)

### `~/Arsenal/tools/`
`AI-Cyber-Defense-Trainer` · `axiom` · `bifrost` · `CIPHER` · `Forge` · `ghost-relay` · `GSL` · `honeypot` · `jeTT` · `meli` · `RedForge`

### Extra local helpers
`honeyhive-app` · `gowskinet-honeyhive*` · `honey-intel` · `gowskinet-honey-intel` · `gowskinet-flipper-intel` · `honeypot-ledger.sh` · `noc-honey`

---

## 7. BlackArch on the ISO

- Repo wired (`blackarch-keyring`, `blackarch-mirrorlist`).
- **Curated ~67-tool set** in `iso-builder/nyx-profile/packages.x86_64` (recon, scanners, webapp, exploitation, wireless, crackers, forensics, sniffer/MITM, crypto) — not the full ~2800-pkg group.
- Official-repo tools already on ISO (nmap, wireshark, ghidra, radare2, yara, tor, macchanger, …) are not double-listed.
- Full group: run `nyxus-blackarch-full` post-boot (explicit confirm).

**Curated names (packages.x86_64 excerpt):**  
amass, subfinder, assetfinder, theharvester, recon-ng, dnsrecon, dnsenum, fierce, sublist3r, masscan, nikto, wpscan, nuclei, naabu, rustscan, enum4linux, sqlmap, gobuster, ffuf, feroxbuster, dirb, wfuzz, whatweb, commix, xsser, dalfox, zaproxy, metasploit, exploitdb, routersploit, crackmapexec, impacket, aircrack-ng, wifite, reaver, bully, bettercap, kismet, hcxtools, hcxdumptool, mdk4, pixiewps, hashcat, john, hydra, medusa, ncrack, crunch, cewl, hashid, patator, foremost, bulk-extractor, stegseek, perl-image-exiftool, bleachbit, secure-delete, mat2, ettercap, dsniff, responder, mitmproxy, proxychains-ng, (+ SSL/crypto block below in that file).

---

## 8. Stations (security-relevant)

Tip `nyxus-stations.conf`: **3 GHOST** (Security · Intel · Recon), Arsenal apps float toward CORE/6 via `nyxus-arsenal-apps.conf`.  
Live `stations.json` may drift (e.g. BIFROST/ARSENAL renames) — sync before bake so skel matches what you use.

UI surfaces: **START** arsenal live feed (`start-feed.py`) · **GHOST** deck · bar security chips · DEEP CORE.

---

## 9. Desktop entries (security subset)

`arsenal.desktop` · `bifrost.desktop` · `meli.desktop` · `nyxus-security.desktop` · `nyxus-shield.desktop` · `nyxus-godsapp.desktop` · `io.nyxus.intel.desktop` · `nyxus-{cipher,forge,redforge,gsl,trainer,axiom,c2}.desktop` (+ `gowskinet-*` aliases).

---

## Reality checklist for bake / stick

1. Arsenal webapps need **`setup-apps.sh`** after first boot — sources ≠ running stack.  
2. Honeypot lands at `/opt/honeypot` **only if** bake host has `~/Projects/honeypot`.  
3. AXIOM backend gap — expect fail-fast without a wired webapp.  
4. Do not assume Vault paths exist on a fresh ISO user home.  
5. Keep Hacker Mode off unless intentional (stale `hacker-mode.state=on` can SIGSTOP reflex daemons).

---

*Generated for owner handoff · update this file when Arsenal registry or `/opt` security trees change.*
