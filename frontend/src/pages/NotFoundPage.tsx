import React from "react";
import { useNavigate } from "react-router-dom";
import { FileQuestion, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center text-center p-8">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted text-muted-foreground mb-4">
        <FileQuestion className="h-8 w-8 stroke-[1.7]" />
      </div>

      <h1 className="font-display text-2xl font-bold text-foreground mb-2">
        404 — Page Not Found
      </h1>

      <p className="max-w-md text-sm text-muted-foreground mb-6 leading-relaxed">
        The requested statutory audit view or case resource does not exist in the system.
      </p>

      <Button onClick={() => navigate("/dashboard")} className="gap-2">
        <ArrowLeft className="h-4 w-4" />
        Return to Dashboard
      </Button>
    </div>
  );
};
