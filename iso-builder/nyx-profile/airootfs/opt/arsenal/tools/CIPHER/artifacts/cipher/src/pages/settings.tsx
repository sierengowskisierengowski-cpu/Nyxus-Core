import { PageContainer } from "@/components/page-container";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useGetSettings, useUpdateSettings } from "@workspace/api-client-react";
import { Save, Cpu, HardDrive } from "lucide-react";
import { useEffect, useState } from "react";
import { useToast } from "@/hooks/use-toast";

export default function Settings() {
  const { data: settings } = useGetSettings();
  const updateSettingsMutation = useUpdateSettings();
  const { toast } = useToast();

  const [gpuEnabled, setGpuEnabled] = useState(true);
  const [gpuDevice, setGpuDevice] = useState(0);
  const [gpuTempLimit, setGpuTempLimit] = useState(85);
  const [cpuThreads, setCpuThreads] = useState(4);
  const [hashcatPath, setHashcatPath] = useState("");
  const [johnPath, setJohnPath] = useState("");

  useEffect(() => {
    if (!settings) return;
    setGpuEnabled(settings.gpuEnabled);
    setGpuDevice(settings.gpuDevice);
    setGpuTempLimit(settings.gpuTempLimit ?? 85);
    setCpuThreads(settings.cpuThreads);
    setHashcatPath(settings.hashcatPath);
    setJohnPath(settings.johnPath);
  }, [settings]);

  const handleSave = () => {
    updateSettingsMutation.mutate(
      {
        data: {
          gpuEnabled,
          gpuDevice: Number(gpuDevice),
          gpuTempLimit: Number(gpuTempLimit),
          cpuThreads: Number(cpuThreads),
          hashcatPath,
          johnPath,
        },
      },
      {
        onSuccess: () => toast({ title: "Settings saved" }),
        onError: (err: unknown) =>
          toast({
            title: "Failed to save settings",
            description: err instanceof Error ? err.message : String(err),
            variant: "destructive",
          }),
      },
    );
  };

  if (!settings) return null;

  return (
    <PageContainer title="System Configuration">
      <div className="max-w-4xl space-y-6 pb-12">
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2 text-primary">
              <Cpu className="w-4 h-4" /> Hardware Acceleration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 border border-border/50 rounded-md bg-background/30">
              <div>
                <Label className="font-mono text-sm">Enable GPU Acceleration</Label>
                <p className="text-xs text-muted-foreground font-mono mt-1">
                  Default for new jobs (each job can override). Uses OpenCL/CUDA via hashcat.
                </p>
              </div>
              <Switch checked={gpuEnabled} onCheckedChange={setGpuEnabled} />
            </div>

            <div className="grid grid-cols-2 gap-6 pt-2">
              <div className="space-y-2">
                <Label className="font-mono text-xs text-muted-foreground">GPU Device ID</Label>
                <Input type="number" value={gpuDevice} onChange={(e) => setGpuDevice(Number(e.target.value))} className="bg-background/50 font-mono" />
              </div>
              <div className="space-y-2">
                <Label className="font-mono text-xs text-muted-foreground">Temp Limit (°C)</Label>
                <Input type="number" value={gpuTempLimit} onChange={(e) => setGpuTempLimit(Number(e.target.value))} className="bg-background/50 font-mono" />
              </div>
              <div className="space-y-2">
                <Label className="font-mono text-xs text-muted-foreground">CPU Threads</Label>
                <Input type="number" value={cpuThreads} onChange={(e) => setCpuThreads(Number(e.target.value))} className="bg-background/50 font-mono" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2 text-primary">
              <HardDrive className="w-4 h-4" /> External Tools
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="font-mono text-xs text-muted-foreground">Hashcat Path</Label>
              <Input value={hashcatPath} onChange={(e) => setHashcatPath(e.target.value)} className="bg-background/50 font-mono text-xs" />
              <p className="text-[10px] text-muted-foreground font-mono">Used to launch real jobs. Falls back to `hashcat` on PATH if the file is missing.</p>
            </div>
            <div className="space-y-2">
              <Label className="font-mono text-xs text-muted-foreground">John The Ripper Path</Label>
              <Input value={johnPath} onChange={(e) => setJohnPath(e.target.value)} className="bg-background/50 font-mono text-xs" />
              <p className="text-[10px] text-muted-foreground font-mono">Falls back to `john` on PATH if the file is missing.</p>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button onClick={handleSave} className="font-mono uppercase tracking-widest gap-2 w-full md:w-auto" disabled={updateSettingsMutation.isPending}>
            <Save className="w-4 h-4" /> Save Configuration
          </Button>
        </div>
      </div>
    </PageContainer>
  );
}
