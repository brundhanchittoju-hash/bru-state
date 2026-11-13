import React from "react";
import { useNavigate } from "react-router-dom";
import { ShieldAlert, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export const ForbiddenPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center text-center p-8">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-destructive mb-4">
        <ShieldAlert className="h-8 w-8 stroke-[1.7]" />
      </div>

      <h1 className="font-display text-2xl font-bold text-foreground mb-2">
        403 — Access Restricted
      </h1>

      <p className="max-w-md text-sm text-muted-foreground mb-6 leading-relaxed">
        Your current role does not have statutory clearance to access this administration section.
        Please contact your System Administrator to request role modification.
      </p>

      <Button onClick={() => navigate("/dashboard")} className="gap-2">
        <ArrowLeft className="h-4 w-4" />
        Return to Dashboard
      </Button>
    </div>
  );
};
