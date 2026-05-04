# NYXUS GodsApp — Legal & Authorization Notice

> © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED

## Same legal standing as the tools it integrates

NYXUS GodsApp is a single user interface that wraps and orchestrates
well-established, freely available open-source security tools, including
but not limited to:

- **Nmap** — network discovery and security auditing
- **Wireshark / TShark / PyShark** — packet analysis
- **Aircrack-ng** — wireless security auditing
- **Bettercap / Ettercap** — network attack and monitoring
- **Hashcat / John the Ripper** — password recovery
- **Metasploit Framework** — penetration testing
- **YARA / ClamAV / rkhunter** — malware detection
- **SQLmap / Nikto / gobuster** — web application testing
- **Volatility3** — memory forensics
- **Capstone / Binwalk / Foremost** — binary analysis
- **bluez / hcitool** — Bluetooth analysis

These tools are legal to install and use on systems you own or are
explicitly authorized to test. The legal status of running them against
a third-party system without written authorization varies by
jurisdiction and is, in many cases, a serious criminal offense.

## Authorization is the operator's responsibility

NYXUS GodsApp does not — and cannot — verify that you have authorization
to scan, intercept, or modify any target. Before pointing this tool at
any network, host, application, or device you do not personally own, you
**must** obtain documented permission from the system owner. Examples
of acceptable authorization include:

- a signed engagement letter from a paying client
- a bug-bounty program scope statement
- written approval from your employer covering corporate assets
- written approval from a property owner covering devices on premises

## What "first launch" actually does

The first time GodsApp launches, it presents a single dialog with the
above text, an "I accept full responsibility" checkbox, and a Continue
button. When you click Continue, GodsApp records:

```json
{
  "accepted": true,
  "ts_iso": "<UTC timestamp>",
  "user":   "<your username>",
  "uid":    <your numeric uid>
}
```

to `~/.config/nyxus-godsapp/authorized.json`. This file serves as a
local audit trail — proof that you, on your machine, accepted the terms
on a specific date. It is never transmitted off your machine.

## Defensive vs. offensive modules

Some modules (e.g. *Network Intelligence*, *Vulnerability Engine*,
*Forensics*, *Log Analysis*) are unambiguously defensive — they
analyze data you already have or scan systems you own. Others
(e.g. *MITM Framework*, *Exploit Framework*, *Social Engineering
Toolkit*) are dual-use: they exist because professional defenders need
to test their own controls. The presence of an offensive module in this
suite is **not** an invitation to use it against a system you do not own.

## Warranty disclaimer

The software is provided "as is," without warranty of any kind, express
or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, and noninfringement.
In no event shall the author be liable for any claim, damages, or other
liability, whether in an action of contract, tort, or otherwise, arising
from, out of, or in connection with the software or the use or other
dealings in the software.

## When in doubt — don't

If you are unsure whether you are authorized to use a given module
against a given target, **stop and verify in writing first.** This tool
exists to make legitimate security work easier, not to lower the bar for
abuse. Use it accordingly.
