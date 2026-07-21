import { createContext, useContext, useEffect, useState } from "react";
import { useGetAuthStatus, useGetDisclaimerStatus } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { Loader2 } from "lucide-react";

export const AuthContext = createContext<{ isAuthenticated: boolean; needsSetup: boolean }>({
  isAuthenticated: false,
  needsSetup: false,
});

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [location, setLocation] = useLocation();
  const { data: authStatus, isLoading: authLoading } = useGetAuthStatus();
  const { data: disclaimerStatus, isLoading: disclaimerLoading } = useGetDisclaimerStatus();

  useEffect(() => {
    if (authLoading || disclaimerLoading) return;

    if (authStatus?.needsSetup && location !== "/setup") {
      setLocation("/setup");
      return;
    }

    if (!authStatus?.needsSetup && !authStatus?.authenticated && location !== "/login") {
      setLocation("/login");
      return;
    }

    if (authStatus?.authenticated && disclaimerStatus && !disclaimerStatus.accepted && location !== "/disclaimer") {
      setLocation("/disclaimer");
      return;
    }

    if (authStatus?.authenticated && disclaimerStatus?.accepted && ["/login", "/setup", "/disclaimer"].includes(location)) {
      setLocation("/");
      return;
    }
  }, [authStatus, disclaimerStatus, authLoading, disclaimerLoading, location, setLocation]);

  if (authLoading || disclaimerLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!authStatus?.authenticated,
        needsSetup: !!authStatus?.needsSetup,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
