import { Link } from "wouter";
import { AlertCircle, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-5">
      <div className="w-14 h-14 rounded-2xl bg-destructive/10 border border-destructive/20 flex items-center justify-center">
        <AlertCircle className="w-7 h-7 text-destructive" />
      </div>
      <div className="text-center">
        <h1 className="text-lg font-semibold">Page Not Found</h1>
        <p className="text-sm text-muted-foreground mt-1">This route doesn't exist in AXIOM.</p>
      </div>
      <Link href="/chat">
        <Button size="sm" variant="ghost" className="border border-white/10 text-xs">
          <Home className="w-3.5 h-3.5 mr-1.5" />
          Back to Chat
        </Button>
      </Link>
    </div>
  );
}
