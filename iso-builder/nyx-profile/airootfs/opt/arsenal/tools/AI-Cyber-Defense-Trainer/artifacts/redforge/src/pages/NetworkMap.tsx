import { useListNetworkDevices } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Network, Server, Monitor, Crosshair, AlertCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export default function NetworkMap() {
  const { data: devices, isLoading } = useListNetworkDevices();

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">NETWORK MAP</h1>
        <p className="text-muted-foreground uppercase text-sm mt-1">Discovered lab assets (arp-scan / nmap)</p>
      </div>

      <Card className="flex-1 border-border bg-black relative overflow-hidden flex flex-col">
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(hsl(var(--primary)) 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
        
        <CardHeader className="relative z-10 border-b border-border/50 bg-card/80 backdrop-blur">
          <CardTitle className="text-sm font-mono text-muted-foreground flex items-center gap-2">
            <Network size={14}/> TOPOLOGY SCAN RESULTS
          </CardTitle>
        </CardHeader>
        
        <CardContent className="relative z-10 flex-1 p-6 overflow-y-auto">
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array(6).fill(0).map((_, i) => <Skeleton key={i} className="h-32 bg-muted/20" />)}
            </div>
          ) : !devices || devices.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center gap-3 py-16">
              <AlertCircle size={40} className="text-muted-foreground/50" />
              <div className="text-muted-foreground font-mono text-sm max-w-md">
                No hosts discovered yet. Run a real scan of your allowlisted lab subnet:
              </div>
              <code className="text-xs text-primary/80 bg-black/50 border border-border rounded px-3 py-2 font-mono">
                pnpm --filter @workspace/scripts run scan-network
              </code>
              <div className="text-muted-foreground/60 text-xs max-w-md">
                Ensure the lab network is up (e.g. start the lab VM so vboxnet0 is active), or set
                <span className="text-muted-foreground"> SCAN_SUBNETS</span> to an active allowlisted subnet.
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {devices?.map(device => (
                <div key={device.ip} className={`p-4 border ${device.isTarget ? 'border-primary bg-primary/5 shadow-[0_0_15px_rgba(239,68,68,0.1)]' : 'border-border bg-card/50'} rounded-lg hover:border-primary/50 transition-colors group relative overflow-hidden`}>
                  
                  {/* Status Indicator */}
                  <div className={`absolute top-4 right-4 w-2 h-2 rounded-full ${device.status === 'online' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]' : device.status === 'offline' ? 'bg-muted-foreground' : 'bg-yellow-500'}`}></div>

                  <div className="flex items-center gap-3 mb-4 text-muted-foreground group-hover:text-foreground transition-colors">
                    {device.vendor?.toLowerCase().includes('apple') || device.vendor?.toLowerCase().includes('windows') ? <Monitor size={24}/> : <Server size={24}/>}
                    <div>
                      <div className="font-mono font-bold text-sm text-foreground">{device.ip}</div>
                      <div className="text-xs uppercase truncate max-w-[120px]">{device.hostname || 'UNKNOWN HOST'}</div>
                    </div>
                  </div>

                  <div className="space-y-2 text-xs font-mono text-muted-foreground">
                    <div className="flex justify-between border-b border-border/50 pb-1">
                      <span>MAC</span>
                      <span>{device.mac || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between border-b border-border/50 pb-1">
                      <span>VENDOR</span>
                      <span className="truncate max-w-[100px]">{device.vendor || 'UNKNOWN'}</span>
                    </div>
                    <div>
                      <span className="block mb-1">OPEN PORTS</span>
                      <div className="flex gap-1 flex-wrap">
                        {device.openPorts && device.openPorts.length > 0 ? (
                          device.openPorts.map(p => <Badge key={p} variant="secondary" className="text-[10px] px-1 py-0">{p}</Badge>)
                        ) : (
                          <span className="text-muted-foreground/50">NO OPEN PORTS</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {device.isTarget && (
                    <div className="mt-4 pt-2 border-t border-primary/20 flex items-center gap-2 text-primary font-bold text-xs tracking-widest">
                      <Crosshair size={12}/> HIGH VALUE TARGET
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
