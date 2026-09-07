"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { TrendingUp } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/lib/api/client";
import { recordSalary } from "@/lib/api/employees";
import type { ChangeReason, CurrentSalary, RecordSalaryInput } from "@/lib/api/types";
import { humanizeEnum } from "@/lib/format";

interface RecordRaiseDialogProps {
  employeeId: number;
  currentSalary: CurrentSalary | null;
  changeReasons: ChangeReason[];
}

interface FormState {
  amount: string;
  currency: string;
  effective_from: string;
  change_reason: string;
  note: string;
}

const DECIMAL_RE = /^\d+(\.\d{1,2})?$/;

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function RecordRaiseDialog({
  employeeId,
  currentSalary,
  changeReasons,
}: RecordRaiseDialogProps) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>({
    amount: "",
    currency: currentSalary?.currency ?? "",
    effective_from: todayIso(),
    change_reason: "annual_review",
    note: "",
  });
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>(
    {},
  );
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (input: RecordSalaryInput) => recordSalary(employeeId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee", employeeId] });
      queryClient.invalidateQueries({
        queryKey: ["salary-history", employeeId],
      });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      toast.success("Raise recorded", {
        description: "The salary history and compensation card have been updated.",
      });
      setOpen(false);
      setForm({
        amount: "",
        currency: currentSalary?.currency ?? "",
        effective_from: todayIso(),
        change_reason: "annual_review",
        note: "",
      });
      setErrors({});
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === "salary_effective_date_invalid") {
        setErrors((prev) => ({ ...prev, effective_from: error.message }));
      }
      toast.error("Couldn't record the raise", {
        description:
          error instanceof ApiError ? error.message : "Please try again.",
      });
    },
  });

  function validate(): Partial<Record<keyof FormState, string>> {
    const next: Partial<Record<keyof FormState, string>> = {};
    if (!form.amount.trim()) {
      next.amount = "Amount is required.";
    } else if (!DECIMAL_RE.test(form.amount.trim())) {
      next.amount = "Enter a valid amount, e.g. 65000.00.";
    } else if (Number(form.amount) <= 0) {
      next.amount = "Amount must be greater than zero.";
    }
    if (!form.currency.trim()) {
      next.currency = "Currency is required.";
    } else if (!/^[A-Za-z]{3}$/.test(form.currency.trim())) {
      next.currency = "Use a 3-letter ISO currency code, e.g. USD.";
    }
    if (!form.effective_from) {
      next.effective_from = "Effective date is required.";
    } else if (
      currentSalary &&
      form.effective_from <= currentSalary.effective_from
    ) {
      // Mirrors the API's salary_effective_date_invalid rule: the new date
      // must be strictly after the current record's effective_from.
      next.effective_from = `Must be after the current record's effective date (${currentSalary.effective_from}).`;
    }
    if (!form.change_reason) {
      next.change_reason = "Select a reason.";
    }
    return next;
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const validationErrors = validate();
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    mutation.mutate({
      amount: Number(form.amount).toFixed(2),
      currency: form.currency.trim().toUpperCase(),
      effective_from: form.effective_from,
      change_reason: form.change_reason as RecordSalaryInput["change_reason"],
      note: form.note.trim() || undefined,
    });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setErrors({});
      }}
    >
      <DialogTrigger render={<Button />}>
        <TrendingUp className="size-4" aria-hidden="true" />
        Record a raise
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>Record a raise</DialogTitle>
            <DialogDescription>
              Closes the current salary record and opens a new one, effective
              from the date below. History is never overwritten.
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="raise-amount">New amount</Label>
              <Input
                id="raise-amount"
                inputMode="decimal"
                placeholder="e.g. 65000.00"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                aria-invalid={!!errors.amount}
              />
              {errors.amount && (
                <p className="text-xs text-destructive">{errors.amount}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="raise-currency">Currency</Label>
              <Input
                id="raise-currency"
                maxLength={3}
                value={form.currency}
                onChange={(e) =>
                  setForm({ ...form, currency: e.target.value.toUpperCase() })
                }
                aria-invalid={!!errors.currency}
              />
              {errors.currency && (
                <p className="text-xs text-destructive">{errors.currency}</p>
              )}
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label htmlFor="raise-effective-from">Effective from</Label>
              <Input
                id="raise-effective-from"
                type="date"
                value={form.effective_from}
                onChange={(e) =>
                  setForm({ ...form, effective_from: e.target.value })
                }
                aria-invalid={!!errors.effective_from}
              />
              {currentSalary && (
                <p className="text-xs text-muted-foreground">
                  Current record effective from {currentSalary.effective_from}.
                  The new date must be after that.
                </p>
              )}
              {errors.effective_from && (
                <p className="text-xs text-destructive">
                  {errors.effective_from}
                </p>
              )}
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label htmlFor="raise-reason">Change reason</Label>
              <Select
                value={form.change_reason}
                onValueChange={(v) =>
                  setForm({ ...form, change_reason: v ?? "" })
                }
              >
                <SelectTrigger
                  id="raise-reason"
                  className="w-full"
                  aria-invalid={!!errors.change_reason}
                >
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  {changeReasons.map((reason) => (
                    <SelectItem key={reason} value={reason}>
                      {humanizeEnum(reason)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.change_reason && (
                <p className="text-xs text-destructive">
                  {errors.change_reason}
                </p>
              )}
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label htmlFor="raise-note">Note (optional)</Label>
              <Input
                id="raise-note"
                placeholder="e.g. Strong performance in H1"
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : "Save raise"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
