import { useGetDashboardSummary } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "wouter";
import { Database, Shield, Terminal, Zap, Bug, Skull } from "lucide-react";

export default function KnowledgeBase() {
  useDocumentTitle("Knowledge Base");
  const { data: summary } = useGetDashboardSummary();

  const categories = [
    {
      title: "MITRE ATT&CK",
      desc: "Tactics, Techniques, and Procedures",
      icon: Shield,
      href: "/kb/mitre",
      count: summary?.kbStats?.mitreTechniques,
      color: "text-blue-500",
      bg: "bg-blue-500/10 border-blue-500/20"
    },
    {
      title: "Atomic Red Team",
      desc: "Small and highly portable detection tests",
      icon: Zap,
      href: "/kb/atomic",
      count: summary?.kbStats?.atomicTests,
      color: "text-yellow-500",
      bg: "bg-yellow-500/10 border-yellow-500/20"
    },
    {
      title: "LOLBAS",
      desc: "Living Off The Land Binaries and Scripts",
      icon: Terminal,
      href: "/kb/lolbas",
      count: summary?.kbStats?.lolbas,
      color: "text-green-500",
      bg: "bg-green-500/10 border-green-500/20"
    },
    {
      title: "GTFOBins",
      desc: "Bypassing local security restrictions on Unix",
      icon: Terminal,
      href: "/kb/gtfobins",
      count: summary?.kbStats?.gtfobins,
      color: "text-purple-500",
      bg: "bg-purple-500/10 border-purple-500/20"
    },
    {
      title: "CVEs",
      desc: "Common Vulnerabilities and Exposures",
      icon: Bug,
      href: "/kb/cves",
      count: summary?.kbStats?.cves,
      color: "text-red-500",
      bg: "bg-red-500/10 border-red-500/20"
    },
    {
      title: "Malware Families",
      desc: "Known adversary software and implants",
      icon: Skull,
      href: "/kb/malware",
      count: summary?.kbStats?.malware,
      color: "text-orange-500",
      bg: "bg-orange-500/10 border-orange-500/20"
    }
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="text-center mb-12">
        <Database className="w-12 h-12 text-primary mx-auto mb-4 opacity-80" />
        <h2 className="text-3xl font-bold tracking-widest text-foreground uppercase">Threat Intelligence Hub</h2>
        <p className="text-muted-foreground mt-2 font-mono text-sm max-w-2xl mx-auto">
          Centralized repository of adversary behavior, capabilities, and detection mechanisms.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {categories.map((cat) => {
          const Icon = cat.icon;
          return (
            <Link key={cat.title} href={cat.href}>
              <Card className="h-full hover:border-primary/50 transition-colors cursor-pointer group bg-card">
                <CardHeader className="pb-2">
                  <div className={`w-10 h-10 rounded-md flex items-center justify-center mb-4 border ${cat.bg}`}>
                    <Icon className={`w-5 h-5 ${cat.color}`} />
                  </div>
                  <CardTitle className="text-lg font-bold group-hover:text-primary transition-colors">{cat.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground min-h-[40px] mb-4">
                    {cat.desc}
                  </p>
                  <div className="font-mono text-xs uppercase tracking-widest text-muted-foreground border-t border-border/50 pt-4 flex justify-between items-center">
                    <span>Indexed Entities</span>
                    <span className="font-bold text-foreground">{cat.count || 0}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
