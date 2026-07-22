import { useState } from "react";
import { useListNotebooks, getListNotebooksQueryKey } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { directApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { BookMarked, Plus, Trash2, Edit2 } from "lucide-react";
import { format } from "date-fns";

export default function Notebooks() {
  useDocumentTitle("Notebooks");
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: notebooks, isLoading } = useListNotebooks();

  const [isOpen, setIsOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({ name: "", description: "", color: "#7B5EA7" });

  const handleOpen = (nb?: any) => {
    if (nb) {
      setEditingId(nb.id);
      setFormData({ name: nb.name, description: nb.description || "", color: nb.color || "#7B5EA7" });
    } else {
      setEditingId(null);
      setFormData({ name: "", description: "", color: "#7B5EA7" });
    }
    setIsOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await directApi.notebooks.update(editingId, formData);
        toast({ title: "Updated", description: "Notebook updated successfully." });
      } else {
        await directApi.notebooks.create(formData);
        toast({ title: "Created", description: "Notebook created successfully." });
      }
      queryClient.invalidateQueries({ queryKey: getListNotebooksQueryKey() });
      setIsOpen(false);
    } catch (e: any) {
      toast({ title: "Error", description: e.message, variant: "destructive" });
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete notebook? Notes inside will not be deleted, just unassigned.")) return;
    try {
      await directApi.notebooks.delete(id);
      toast({ title: "Deleted", description: "Notebook deleted." });
      queryClient.invalidateQueries({ queryKey: getListNotebooksQueryKey() });
    } catch (e: any) {
      toast({ title: "Error", description: e.message, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-widest text-primary uppercase">Notebooks</h2>
          <p className="text-sm text-muted-foreground mt-1">Organize your intelligence and observations.</p>
        </div>
        <Button onClick={() => handleOpen()} className="font-mono tracking-widest uppercase gap-2">
          <Plus className="w-4 h-4" /> Create Notebook
        </Button>
      </div>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="border-border bg-card sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="font-mono uppercase tracking-widest text-primary">
              {editingId ? "Edit Notebook" : "New Notebook"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSave} className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">Name</Label>
              <Input required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="font-mono" />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">Description</Label>
              <Input value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} className="font-mono" />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">Color Hex</Label>
              <div className="flex gap-2">
                <Input type="color" value={formData.color} onChange={e => setFormData({...formData, color: e.target.value})} className="w-12 h-10 p-1 cursor-pointer" />
                <Input value={formData.color} onChange={e => setFormData({...formData, color: e.target.value})} className="font-mono flex-1 uppercase" pattern="^#[0-9A-Fa-f]{6}$" />
              </div>
            </div>
            <div className="flex justify-end pt-4">
              <Button type="submit" className="font-mono uppercase tracking-widest w-full">Save Changes</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-full py-8 text-center text-muted-foreground font-mono animate-pulse">LOADING...</div>
        ) : notebooks?.length === 0 ? (
           <div className="col-span-full py-12 text-center text-muted-foreground border border-dashed border-border rounded-lg">
             No notebooks created. Organize your notes.
           </div>
        ) : (
          notebooks?.map((nb) => (
            <Card key={nb.id} className="border-border hover:border-primary/50 transition-colors group">
              <CardHeader className="pb-3 border-b border-border/50">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: nb.color || 'var(--primary)' }} />
                    {nb.name}
                  </CardTitle>
                  <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-primary" onClick={() => handleOpen(nb)}>
                      <Edit2 className="w-3 h-3" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive" onClick={() => handleDelete(nb.id)}>
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <p className="text-sm text-muted-foreground line-clamp-2 min-h-[40px]">
                  {nb.description || "No description provided."}
                </p>
                <div className="flex justify-between items-center text-xs font-mono text-muted-foreground pt-4 border-t border-border/50">
                  <span>{nb.noteCount || 0} Notes</span>
                  <span>Created {format(new Date(nb.createdAt), "yyyy-MM-dd")}</span>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
