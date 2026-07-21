export interface NmapPort {
  port: number;
  protocol: string;
  state: string;
  service: string;
  version: string;
}

export interface NmapHost {
  ip: string;
  hostname?: string;
  status: string;
  ports: NmapPort[];
  os?: string;
  latency?: string;
}

export interface NmapResult {
  hosts: NmapHost[];
  summary?: string;
  isNmap: boolean;
}

export function parseNmapOutput(output: string): NmapResult {
  if (!output) return { hosts: [], isNmap: false };

  const lines = output.split("\n");
  const isNmap =
    lines.some((l) => l.includes("Nmap scan report") || l.includes("Nmap done:") || l.includes("Starting Nmap"));

  if (!isNmap) return { hosts: [], isNmap: false };

  const hosts: NmapHost[] = [];
  let currentHost: NmapHost | null = null;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    // New host block
    const hostMatch =
      line.match(/^Nmap scan report for (.+?)\s*\((\d+\.\d+\.\d+\.\d+)\)$/) ||
      line.match(/^Nmap scan report for (\d+\.\d+\.\d+\.\d+)$/);

    if (hostMatch) {
      if (currentHost) hosts.push(currentHost);
      const ipMatch = line.match(/(\d+\.\d+\.\d+\.\d+)/);
      const ip = ipMatch ? ipMatch[1] : hostMatch[1];
      const hostnameMatch = line.match(/for (.+?) \(/);
      currentHost = {
        ip,
        hostname: hostnameMatch ? hostnameMatch[1] : undefined,
        status: "up",
        ports: [],
      };
      continue;
    }

    if (!currentHost) continue;

    // Host status
    if (line.startsWith("Host is")) {
      currentHost.status = line.includes("up") ? "up" : "down";
      const latencyMatch = line.match(/\((.+?)\s*latency\)/);
      if (latencyMatch) currentHost.latency = latencyMatch[1];
      continue;
    }

    // Latency in parens
    if (line.match(/^\d+\.\d+\.\d+\.\d+$/) || line.match(/latency/)) {
      const latencyMatch = line.match(/\(([0-9.]+s)\s*latency\)/);
      if (latencyMatch) currentHost.latency = latencyMatch[1];
      continue;
    }

    // Port line: "80/tcp   open  http    Apache httpd 2.4.41"
    const portMatch = line.match(/^(\d+)\/(tcp|udp)\s+(open|closed|filtered)\s+(\S+)?\s*(.*)$/);
    if (portMatch) {
      currentHost.ports.push({
        port: parseInt(portMatch[1]),
        protocol: portMatch[2],
        state: portMatch[3],
        service: portMatch[4] || "",
        version: portMatch[5]?.trim() || "",
      });
      continue;
    }

    // OS detection
    if (line.startsWith("OS details:") || line.startsWith("Running:")) {
      currentHost.os = line.replace(/^(OS details:|Running:)\s*/, "");
    }
  }

  if (currentHost) hosts.push(currentHost);

  // Summary line
  const summaryLine = lines.find((l) => l.includes("Nmap done:"));

  return {
    hosts: hosts.filter((h) => h.ports.length > 0 || h.status === "up"),
    summary: summaryLine?.trim(),
    isNmap: true,
  };
}
