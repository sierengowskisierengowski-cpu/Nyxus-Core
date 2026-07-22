import { useState, useEffect } from "react";
import { useGetSettings, getGetSettingsQueryKey } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { directApi } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { Settings as SettingsIcon, Save, Key, ShieldAlert } from "lucide-react";

export default function Settings() {
  useDocumentTitle("System Configuration");
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useGetSettings();

  const [formData, setFormData] = useState({
    targetSubnet: "",
    defaultDifficulty: "Medium",
    defaultTimerMinutes: 60,
    claudeModel: "claude-3-5-sonnet-20241022",
    ntfyUrl: "",
    notifyOnStart: false,
    notifyOnTimer: true,
    excludedDevices: ""
  });

  const [pwdData, setPwdData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });

  const [isSaving, setIsSaving] = useState(false);
  const [isChangingPwd, setIsChangingPwd] = useState(false);

  useEffect(() => {
    if (settings) {
      setFormData({
        targetSubnet: settings.targetSubnet || "",
        defaultDifficulty: settings.defaultDifficulty,
        defaultTimerMinutes: settings.defaultTimerMinutes,
        claudeModel: settings.claudeModel,
        ntfyUrl: settings.ntfyUrl || "",
        notifyOnStart: settings.notifyOnStart ?? false,
        notifyOnTimer: settings.notifyOnTimer ?? true,
        excludedDevices: settings.excludedDevices?.join(", ") || ""
      });
    }
  }, [settings]);

  const handleSaveSettings = async () => {
    setIsSaving(true);
    try {
      const payload = {
        ...formData,
        excludedDevices: formData.excludedDevices.split(",").map(s => s.trim()).filter(Boolean)
      };
      
      await directApi.settings.update(payload);

      toast({ title: "Configuration Updated", description: "System parameters saved successfully." });
      queryClient.invalidateQueries({ queryKey: getGetSettingsQueryKey() });
    } catch (err: any) {
      toast({ title: "Update Failed", description: err.message, variant: "destructive" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pwdData.newPassword !== pwdData.confirmPassword) {
      toast({ title: "Error", description: "New passwords do not match.", variant: "destructive" });
      return;
    }
    
    setIsChangingPwd(true);
    try {
      await directApi.settings.changePassword({
        currentPassword: pwdData.currentPassword,
        newPassword: pwdData.newPassword
      });

      toast({ title: "Security Updated", description: "Master passphrase changed successfully." });
      setPwdData({ currentPassword: "", newPassword: "", confirmPassword: "" });
    } catch (err: any) {
      toast({ title: "Update Failed", description: err.message, variant: "destructive" });
    } finally {
      setIsChangingPwd(false);
    }
  };

  if (isLoading) return <div className="p-8 font-mono animate-pulse">LOADING CONFIGURATION...</div>;

  return (
    <div className="max-w-4xl space-y-8 pb-12">
      <div>
        <h2 className="text-2xl font-bold tracking-widest text-primary uppercase flex items-center gap-3">
          <SettingsIcon className="w-6 h-6" />
          System Configuration
        </h2>
        <p className="text-sm text-muted-foreground mt-1">Manage core platform parameters and preferences.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Core Parameters */}
        <Card className="md:col-span-2">
          <CardHeader className="border-b border-border bg-muted/20">
            <CardTitle className="text-base uppercase tracking-widest text-secondary flex items-center gap-2">
              <ShieldAlert className="w-4 h-4" />
              Operational Parameters
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Target Subnet (CIDR)</Label>
                <Input
                  value={formData.targetSubnet}
                  onChange={e => setFormData({...formData, targetSubnet: e.target.value})}
                  className="font-mono"
                  placeholder="192.168.56.0/24"
                />
                <p className="text-[10px] text-muted-foreground">Scan target for network discovery. Must be a private (RFC1918) range on the server's allow-list.</p>
              </div>

              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Excluded Devices (IPs, comma separated)</Label>
                <Input 
                  value={formData.excludedDevices}
                  onChange={e => setFormData({...formData, excludedDevices: e.target.value})}
                  className="font-mono"
                  placeholder="192.168.0.1, 192.168.0.254"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Default Difficulty</Label>
                <Select value={formData.defaultDifficulty} onValueChange={v => setFormData({...formData, defaultDifficulty: v})}>
                  <SelectTrigger className="font-mono">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Easy">Easy</SelectItem>
                    <SelectItem value="Medium">Medium</SelectItem>
                    <SelectItem value="Hard">Hard</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Default Timer (Minutes)</Label>
                <Input 
                  type="number"
                  value={formData.defaultTimerMinutes}
                  onChange={e => setFormData({...formData, defaultTimerMinutes: Number(e.target.value)})}
                  className="font-mono"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">AI Tutor Model</Label>
                <Select value={formData.claudeModel} onValueChange={v => setFormData({...formData, claudeModel: v})}>
                  <SelectTrigger className="font-mono">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</SelectItem>
                    <SelectItem value="claude-3-haiku-20240307">Claude 3 Haiku (Fast)</SelectItem>
                    <SelectItem value="claude-3-opus-20240229">Claude 3 Opus (Thorough)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">NTFY Topic URL (Alerts)</Label>
                <Input 
                  value={formData.ntfyUrl}
                  onChange={e => setFormData({...formData, ntfyUrl: e.target.value})}
                  className="font-mono"
                  placeholder="https://ntfy.sh/my-secret-topic"
                />
              </div>

            </div>

            <div className="flex items-center gap-6 pt-4 border-t border-border">
              <div className="flex items-center space-x-2">
                <Switch 
                  id="notify-start" 
                  checked={formData.notifyOnStart}
                  onCheckedChange={c => setFormData({...formData, notifyOnStart: c})}
                />
                <Label htmlFor="notify-start" className="text-sm">Alert on Mission Start</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch 
                  id="notify-timer" 
                  checked={formData.notifyOnTimer}
                  onCheckedChange={c => setFormData({...formData, notifyOnTimer: c})}
                />
                <Label htmlFor="notify-timer" className="text-sm">Alert on Timer <span className="text-destructive font-mono">&lt; 5m</span></Label>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <Button onClick={handleSaveSettings} disabled={isSaving} className="font-mono uppercase tracking-widest gap-2">
                <Save className="w-4 h-4" />
                {isSaving ? "Saving..." : "Commit Configuration"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Security */}
        <Card className="md:col-span-2 border-destructive/30">
          <CardHeader className="border-b border-border bg-destructive/5">
            <CardTitle className="text-base uppercase tracking-widest text-destructive flex items-center gap-2">
              <Key className="w-4 h-4" />
              Access Credentials
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Current Passphrase</Label>
                <Input 
                  type="password"
                  required
                  value={pwdData.currentPassword}
                  onChange={e => setPwdData({...pwdData, currentPassword: e.target.value})}
                  className="font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">New Passphrase</Label>
                <Input 
                  type="password"
                  required
                  minLength={8}
                  value={pwdData.newPassword}
                  onChange={e => setPwdData({...pwdData, newPassword: e.target.value})}
                  className="font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Confirm New Passphrase</Label>
                <Input 
                  type="password"
                  required
                  minLength={8}
                  value={pwdData.confirmPassword}
                  onChange={e => setPwdData({...pwdData, confirmPassword: e.target.value})}
                  className="font-mono"
                />
              </div>
              <Button type="submit" variant="destructive" disabled={isChangingPwd} className="font-mono uppercase tracking-widest w-full">
                {isChangingPwd ? "Updating..." : "Update Passphrase"}
              </Button>
            </form>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
