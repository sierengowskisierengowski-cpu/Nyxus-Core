# NYXUS GodsApp

> Professional security auditing & research suite for NyX.x.OS.
> Native GTK4 · 30 modules · real backends · no stubs.
> © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED

GodsApp is the heavy-weight counterpart to NYXUS Shield. Where Shield
gives the household plain-English "fix it" buttons, GodsApp gives a
trained operator the full toolbox — Nmap, Wireshark, Aircrack-ng,
Bettercap, Hashcat, Metasploit, YARA, Volatility, Capstone, and dozens
more — wrapped in one cohesive themed UI.

## First-launch authorization gate

```
NYXUS GodsApp is a professional security auditing and research tool.
You are solely responsible for ensuring you have proper authorization
before scanning, auditing, or testing any network, system, or device
you do not own.
                                       [ ] I accept   [Continue]
```

Shown **once**. Acceptance is recorded to
`~/.config/nyxus-godsapp/authorized.json` with timestamp + uid as a
local audit trail. See `LEGAL.md` for the full notice.

## The 30 modules

```
01  Network Intelligence       16  Malware Analysis
02  Port & Service Scanner     17  VoIP Security
03  Packet Capture & Analysis  18  Industrial / SCADA
04  WiFi Arsenal               19  Cryptography Suite
05  Vulnerability Engine       20  Binary & File Analysis
06  Traffic Intelligence       21  Log Analysis Engine
07  Attack Surface Mapper      22  Mobile Device Security
08  OSINT Engine               23  Cloud Security
09  Password & Hash Analysis   24  Physical Security
10  Bluetooth Scanner          25  Dark Web Monitoring
11  USB & Hardware Monitor     26  Social Engineering Toolkit
12  Active Directory & Net Svc 27  Automation & Scheduling
13  Web Application Scanner    28  Forensics
14  MITM Framework             29  GOD MODE Master Dashboard
15  Exploit Framework          30  Built-in Terminal (VTE4)
```

## Architecture

```
main.py            entry; first-launch gate, theme load, app bootstrap
ui.py              MainWindow + sidebar + content stack + BaseModule
db.py              sqlite storage (scans, findings, devices, schedules)
scheduler.py       background job loop (recurring scans + workflows)
api.py             local REST API on 127.0.0.1:7331 (token-auth)
modules/m01..m30   one Python file per module — drop-in discoverable
```

Modules are auto-discovered: drop a new `modules/m31_whatever.py`
exporting a `Page(BaseModule)` class and it appears in the sidebar on
next launch — no registration step required.

## BaseModule contract

```python
from ui import BaseModule

class Page(BaseModule):
    NAME = "My module"
    ICON = "✦"
    DESCRIPTION = "What this thing does."

    def build(self):
        self.add_action("Run scan", self.action_scan, primary=True)

    def action_scan(self):
        if not self.need("nmap"):
            return
        rc, out = run_subprocess(["nmap", "-sV", self.target], timeout=120)
        self.write(out)
```

That's it. The base class supplies the spinner, the threading wrapper,
the output text view, the button-disable-while-running guard, and the
NYX theme styling.

## Theme

GodsApp uses the same shared NYXUS theme (purple/pink/gold + Caveat /
Patrick Hand handwritten fonts) installed by Shield's `install.sh` to
`/usr/share/nyxus/theme/`. If you install GodsApp standalone its own
installer brings the theme along.

## REST API

```bash
TOKEN=$(cat ~/.config/nyxus-godsapp/api_token)
curl -H "Authorization: Bearer $TOKEN"  http://127.0.0.1:7331/api/scans?limit=10
curl -H "Authorization: Bearer $TOKEN" \
     -X POST http://127.0.0.1:7331/api/schedules \
     -d '{"name":"daily-recon","module":"m01_network","target":"10.0.0.0/24","cadence_seconds":86400}'
```

Loopback-only by design. Token is auto-generated on first run and
permission-locked to `0600`.

## Install

```bash
sudo bash install.sh
nyxus-godsapp
```

## Phantom integration

When the local Phantom daemon is running, the *Forensics* module reads
`~/.nyxus/phantom/events.db` and the *Automation & Scheduling* module
can subscribe to Phantom MQTT topics so a triggered Phantom event can
chain into a deeper GodsApp scan.

## Files installed

```
/opt/nyxus-godsapp/main.py     · ui.py · db.py · scheduler.py · api.py
/opt/nyxus-godsapp/modules/    · m01..m30
/usr/share/nyxus/theme/        · nyxus_theme.css + nyxus_theme.py
/etc/udev/rules.d/99-nyxus-godsapp.rules
/usr/local/bin/nyxus-godsapp   · symlink to /opt/nyxus-godsapp/main.py
/usr/share/applications/nyxus-godsapp.desktop
~/.config/nyxus-godsapp/       · authorized.json, godsapp.db, api_token
~/.cache/nyxus-godsapp/        · transient scan output
```
