export interface MitreTactic {
  id: string;
  name: string;
  description: string;
}

export interface MitreTechnique {
  id: string;
  name: string;
  description: string;
  tactics: string[];
  platforms: string[];
  detection: string;
  mitigation: string;
  dataSources: string[];
  references: { title: string; url: string }[];
  subTechniques?: { id: string; name: string; description: string }[];
}

export const TACTICS: MitreTactic[] = [
  { id: "TA0043", name: "Reconnaissance", description: "Gather information to plan future operations." },
  { id: "TA0042", name: "Resource Development", description: "Establish resources to support operations." },
  { id: "TA0001", name: "Initial Access", description: "Get into the network." },
  { id: "TA0002", name: "Execution", description: "Run malicious code." },
  { id: "TA0003", name: "Persistence", description: "Maintain foothold." },
  { id: "TA0004", name: "Privilege Escalation", description: "Gain higher-level permissions." },
  { id: "TA0005", name: "Defense Evasion", description: "Avoid being detected." },
  { id: "TA0006", name: "Credential Access", description: "Steal account names and passwords." },
  { id: "TA0007", name: "Discovery", description: "Figure out the environment." },
  { id: "TA0008", name: "Lateral Movement", description: "Move through the environment." },
  { id: "TA0009", name: "Collection", description: "Gather data of interest." },
  { id: "TA0011", name: "Command and Control", description: "Communicate with compromised systems." },
  { id: "TA0010", name: "Exfiltration", description: "Steal data." },
  { id: "TA0040", name: "Impact", description: "Manipulate, interrupt, or destroy systems and data." },
];

const t = (
  id: string,
  name: string,
  description: string,
  tactics: string[],
  platforms: string[],
  detection: string,
  mitigation: string,
  dataSources: string[],
  refs: { title: string; url: string }[],
): MitreTechnique => ({ id, name, description, tactics, platforms, detection, mitigation, dataSources, references: refs });

export const TECHNIQUES: MitreTechnique[] = [
  t("T1046", "Network Service Discovery", "Scan for open services to identify exploitable targets.", ["Discovery", "Reconnaissance"], ["Linux", "Windows", "macOS", "Network"], "Network IDS rules for fast sequential port connection attempts. SYN-to-ACK ratio anomalies.", "Network segmentation, intrusion prevention.", ["Network Traffic", "Cloud Service Enumeration"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1046/" }]),
  t("T1059.001", "PowerShell", "Adversaries abuse PowerShell for execution.", ["Execution"], ["Windows"], "Sysmon Event 1 with PowerShell, Script Block Logging (4104), Module Logging.", "Constrained Language Mode, AppLocker, AMSI.", ["Process", "Command", "Module Load"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1059/001/" }]),
  t("T1059.003", "Windows Command Shell", "cmd.exe abuse.", ["Execution"], ["Windows"], "Sysmon Event 1 cmd.exe with suspicious children.", "Restrict cmd via WDAC.", ["Process"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1059/003/" }]),
  t("T1059.004", "Unix Shell", "bash/sh abuse for execution.", ["Execution"], ["Linux", "macOS"], "auditd execve monitoring, shell history.", "Restrict interactive shells, SELinux/AppArmor.", ["Process"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1059/004/" }]),
  t("T1053.005", "Scheduled Task", "Windows Task Scheduler abuse.", ["Persistence", "Privilege Escalation", "Execution"], ["Windows"], "Security Event 4698, Sysmon FileCreate in Tasks folder.", "Audit task creation rights.", ["Process", "File", "Scheduled Job"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1053/005/" }]),
  t("T1053.003", "Cron", "Linux cron abuse.", ["Persistence", "Privilege Escalation", "Execution"], ["Linux", "macOS"], "auditd watch on /etc/cron.* and /var/spool/cron.", "Restrict cron to specific users.", ["File", "Process", "Scheduled Job"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1053/003/" }]),
  t("T1547.001", "Registry Run Keys / Startup Folder", "HKCU/HKLM Run keys for persistence.", ["Persistence", "Privilege Escalation"], ["Windows"], "Sysmon Event 13 (RegistryValueSet) on Run keys.", "Restrict registry write, baseline autoruns.", ["Registry", "File"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1547/001/" }]),
  t("T1218.005", "Mshta", "Microsoft-signed HTA executor.", ["Defense Evasion"], ["Windows"], "Sysmon Event 1 mshta.exe with URL or .hta.", "Block mshta via WDAC, disassociate .hta.", ["Process", "Network Traffic"], [{ title: "LOLBAS", url: "https://lolbas-project.github.io/lolbas/Binaries/Mshta/" }]),
  t("T1218.011", "Rundll32", "rundll32.exe abuse for DLL execution.", ["Defense Evasion"], ["Windows"], "Sysmon Event 1 rundll32 with unusual DLL paths.", "WDAC, block specific exports (e.g. comsvcs MiniDump).", ["Process"], [{ title: "LOLBAS rundll32", url: "https://lolbas-project.github.io/lolbas/Binaries/Rundll32/" }]),
  t("T1003.001", "LSASS Memory", "Dump credentials from lsass.exe memory.", ["Credential Access"], ["Windows"], "Sysmon Event 10 ProcessAccess on lsass with read rights.", "Credential Guard, RunAsPPL, EDR memory protection.", ["Process", "Command", "OS API Execution"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1003/001/" }]),
  t("T1003.003", "NTDS", "Dump NTDS.dit to extract domain credentials.", ["Credential Access"], ["Windows"], "ntdsutil.exe execution, volume shadow copy creation on DCs.", "DC tier-0 isolation, EDR.", ["Process", "Command"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1003/003/" }]),
  t("T1558.003", "Kerberoasting", "Crack RC4 service tickets offline.", ["Credential Access"], ["Windows"], "Event 4769 RC4 etype anomaly, SPN request volume.", "AES-only tickets, gMSA, long passwords.", ["Active Directory"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1558/003/" }]),
  t("T1110.003", "Password Spraying", "One password against many accounts.", ["Credential Access"], ["Windows", "Linux", "SaaS"], "Many 4625 events with same source IP across many usernames.", "MFA everywhere, lockout policies, anomaly alerts.", ["Application Log", "User Account Authentication"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1110/003/" }]),
  t("T1021.002", "SMB/Windows Admin Shares", "Lateral movement via ADMIN$/C$.", ["Lateral Movement"], ["Windows"], "Event 7045 service install, 4624 type 3 logons.", "Disable SMBv1, restrict ADMIN$, LAPS.", ["Network Share", "Logon Session", "Process"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1021/002/" }]),
  t("T1021.001", "RDP", "Lateral movement via Remote Desktop.", ["Lateral Movement"], ["Windows"], "Event 4624 type 10 logons, RDP from non-admin hosts.", "Restrict RDP, MFA, jump hosts.", ["Network Traffic", "Logon Session"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1021/001/" }]),
  t("T1569.002", "Service Execution", "Execute via Windows service (PsExec etc).", ["Execution"], ["Windows"], "Event 7045 service install with random names.", "Restrict admin shares, monitor service creation.", ["Process", "Service"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1569/002/" }]),
  t("T1027", "Obfuscated Files or Information", "Encode/encrypt payloads to evade detection.", ["Defense Evasion"], ["Linux", "Windows", "macOS"], "Entropy analysis, base64 in command lines, AMSI.", "AMSI, decompile/decrypt analysis.", ["File", "Process", "Script"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1027/" }]),
  t("T1070.001", "Clear Windows Event Logs", "wevtutil cl to wipe logs.", ["Defense Evasion"], ["Windows"], "Event 1102 (Security), 104 (System).", "Off-host log shipping, restrict Manage Auditing right.", ["Application Log"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1070/001/" }]),
  t("T1070.004", "File Deletion", "Remove artifacts post-exploitation.", ["Defense Evasion"], ["Linux", "Windows", "macOS"], "File modification logs, EDR file-event timelines.", "Append-only forensic logging, file integrity monitoring.", ["File"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1070/004/" }]),
  t("T1071.001", "Application Layer Protocol: Web", "C2 over HTTP/HTTPS.", ["Command and Control"], ["Linux", "Windows", "macOS"], "Beaconing analysis, JA3 fingerprints, NIDS.", "TLS inspection, egress allow-list, behavioral C2 detection.", ["Network Traffic"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1071/001/" }]),
  t("T1071.004", "Application Layer Protocol: DNS", "C2 / exfil over DNS.", ["Command and Control"], ["Linux", "Windows", "macOS"], "DNS query rate per domain, subdomain entropy, TXT volume.", "Internal DNS only, anomaly detection.", ["Network Traffic"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1071/004/" }]),
  t("T1048.003", "Exfil Over Unencrypted Non-C2 Protocol", "Exfil via DNS/ICMP/etc.", ["Exfiltration"], ["Linux", "Windows", "macOS"], "Volume per egress protocol, DLP, NIDS rules.", "DLP, egress segmentation.", ["Network Traffic"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1048/003/" }]),
  t("T1190", "Exploit Public-Facing Application", "Web/network service exploitation.", ["Initial Access"], ["Linux", "Windows", "Network"], "WAF, NIDS, app-level anomaly logging.", "Patch, WAF, least-privilege service accounts.", ["Application Log", "Network Traffic"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1190/" }]),
  t("T1566.001", "Spearphishing Attachment", "Malicious email attachment.", ["Initial Access"], ["Linux", "Windows", "macOS"], "Email gateway sandboxing, ASR rules.", "Disable macros, sandbox attachments.", ["File", "Network Traffic"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1566/001/" }]),
  t("T1204.002", "Malicious File", "User executes attacker file.", ["Execution"], ["Linux", "Windows", "macOS"], "EDR file execution audit.", "Application allow-listing, user training.", ["File", "Process"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1204/002/" }]),
  t("T1548.003", "Sudo and Sudo Caching", "Abuse sudo for privilege escalation.", ["Privilege Escalation", "Defense Evasion"], ["Linux", "macOS"], "auditd execve where uid=0 and parent in known abusable binaries.", "Audit sudoers, avoid NOPASSWD, see GTFOBins.", ["Process", "Command"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1548/003/" }]),
  t("T1087.002", "Domain Account Discovery", "Enumerate AD users.", ["Discovery"], ["Windows"], "LDAP query volume per user, BloodHound collector signatures.", "MS Defender for Identity, AD audit.", ["Active Directory", "Process"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1087/002/" }]),
  t("T1482", "Domain Trust Discovery", "Enumerate AD trusts.", ["Discovery"], ["Windows"], "LDAP query for trustedDomain objects, nltest /trusts.", "Tier-0 protection.", ["Active Directory", "Process"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1482/" }]),
  t("T1490", "Inhibit System Recovery", "Delete backups/shadow copies.", ["Impact"], ["Windows", "Linux"], "Sysmon Event 1 vssadmin/wmic shadow delete.", "Restrict vssadmin, immutable backups.", ["Process", "Command"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1490/" }]),
  t("T1486", "Data Encrypted for Impact", "Ransomware file encryption.", ["Impact"], ["Linux", "Windows", "macOS"], "Mass file modifications, entropy spike, file extension changes.", "Controlled Folder Access, immutable backups, EDR ransomware protection.", ["File", "Process"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1486/" }]),
  t("T1505.003", "Web Shell", "Persistence via web app upload.", ["Persistence"], ["Linux", "Windows"], "Web access log anomaly, file integrity monitoring on web root.", "FIM on web root, WAF, least-privilege web user.", ["File", "Network Traffic", "Application Log"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1505/003/" }]),
  t("T1573.002", "Asymmetric Cryptography (C2)", "TLS/encrypted C2 channels.", ["Command and Control"], ["Linux", "Windows", "macOS"], "JA3/JA3S, TLS metadata anomaly, beaconing patterns.", "TLS inspection where possible, behavioral C2 detection.", ["Network Traffic"], [{ title: "ATT&CK", url: "https://attack.mitre.org/techniques/T1573/002/" }]),
];

export function getTechnique(id: string): MitreTechnique | undefined {
  return TECHNIQUES.find((x) => x.id === id);
}
