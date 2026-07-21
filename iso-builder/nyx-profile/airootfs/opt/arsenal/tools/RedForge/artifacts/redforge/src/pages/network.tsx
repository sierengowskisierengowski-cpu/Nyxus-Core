import { useGetSettings, useScanNetwork, useListNetworkDevices } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Network as NetworkIcon, RefreshCw, AlertTriangle, Monitor, Server, Smartphone, HelpCircle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

export default function Network() {
  useDocumentTitle("Network Intelligence");
  const { toast } = useToast();
  
  const { data: settings } = useGetSettings();
  const { data: devices, isLoading, refetch } = useListNetworkDevices();
  const scanMutation = useScanNetwork();

  const handleScan = () => {
    scanMutation.mutate(undefined, {
      onSuccess: () => {
        toast({ title: "Scan Complete", description: "Network discovery finished." });
        refetch();
      },
      onError: (err) => {
        toast({ title: "Scan Failed", description: "Failed to run network discovery.", variant: "destructive" });
      }
    });
  };

  const getDeviceIcon = (vendor?: string) => {
    if (!vendor) return <HelpCircle className="w-4 h-4 text-muted-foreground" />;
    const v = vendor.toLowerCase();
    if (v.includes("apple") || v.includes("samsung")) return <Smartphone className="w-4 h-4 text-foreground" />;
    if (v.includes("intel") || v.includes("dell") || v.includes("lenovo")) return <Monitor className="w-4 h-4 text-foreground" />;
    if (v.includes("cisco") || v.includes("raspberry")) return <Server className="w-4 h-4 text-foreground" />;
    return <Monitor className="w-4 h-4 text-foreground" />;
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-widest text-primary uppercase">Network Discovery</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Target Subnet: <code className="bg-muted px-1 py-0.5 rounded text-secondary">{settings?.targetSubnet || "Unknown"}</code>
          </p>
        </div>
        <Button 
          onClick={handleScan} 
          disabled={scanMutation.isPending}
          className="font-mono tracking-widest uppercase gap-2"
        >
          <RefreshCw className={cn("w-4 h-4", scanMutation.isPending && "animate-spin")} />
          {scanMutation.isPending ? "Scanning..." : "Execute Scan"}
        </Button>
      </div>

      <Card className="flex-1 flex flex-col min-h-0 border-border">
        <CardHeader className="border-b border-border bg-muted/20 py-3">
          <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
            <NetworkIcon className="w-4 h-4 text-primary" />
            Discovered Entities ({devices?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-auto p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground animate-pulse font-mono text-sm">RUNNING DISCOVERY PROTOCOL...</div>
          ) : devices?.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground border border-dashed border-border m-8 rounded-lg flex flex-col items-center gap-4">
              <AlertTriangle className="w-8 h-8 text-muted-foreground/50" />
              <p>No entities discovered. Execute scan to map local subnet.</p>
            </div>
          ) : (
            <Table>
              <TableHeader className="bg-muted/50 sticky top-0 z-10">
                <TableRow>
                  <TableHead className="w-[50px]"></TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">IP ADDRESS</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">HOSTNAME</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">MAC ADDRESS</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">VENDOR / FINGERPRINT</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground text-right">LAST SEEN</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices?.map((device) => (
                  <TableRow key={device.ip} className={cn("hover:bg-muted/30 transition-colors", device.excluded && "opacity-50 grayscale")}>
                    <TableCell className="text-center">{getDeviceIcon(device.vendor)}</TableCell>
                    <TableCell className="font-mono text-primary font-medium">{device.ip}</TableCell>
                    <TableCell className="font-medium">{device.hostname || <span className="text-muted-foreground italic">UNKNOWN</span>}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{device.mac || "—"}</TableCell>
                    <TableCell className="text-sm">{device.vendor || "—"}</TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(device.lastSeen), { addSuffix: true })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
