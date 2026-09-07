"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { exportEmployeesCsv } from "@/lib/api/employees";
import { ApiError } from "@/lib/api/client";
import type { EmployeeListParams } from "@/lib/api/types";

/** Exports the currently filtered employee list as CSV, preserving all filters. */
export function ExportButton({ filters }: { filters: EmployeeListParams }) {
  const [isExporting, setIsExporting] = useState(false);

  async function handleExport() {
    setIsExporting(true);
    try {
      const blob = await exportEmployeesCsv(filters);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `employees-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.success("Export ready", {
        description: "Your CSV download should start automatically.",
      });
    } catch (error) {
      toast.error("Export failed", {
        description:
          error instanceof ApiError ? error.message : "Please try again.",
      });
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <Button variant="outline" onClick={handleExport} disabled={isExporting}>
      {isExporting ? (
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      ) : (
        <Download className="size-4" aria-hidden="true" />
      )}
      Export CSV
    </Button>
  );
}
