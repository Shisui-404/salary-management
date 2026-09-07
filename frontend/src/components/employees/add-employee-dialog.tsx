"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
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
import { createEmployee } from "@/lib/api/employees";
import type { CreateEmployeeInput, ReferenceData } from "@/lib/api/types";
import { humanizeEnum } from "@/lib/format";

interface FormState {
  first_name: string;
  last_name: string;
  email: string;
  gender: string;
  hire_date: string;
  department_id: string;
  job_role_id: string;
  level_id: string;
  country_id: string;
  initial_salary_amount: string;
  initial_salary_currency: string;
}

const EMPTY_FORM: FormState = {
  first_name: "",
  last_name: "",
  email: "",
  gender: "",
  hire_date: "",
  department_id: "",
  job_role_id: "",
  level_id: "",
  country_id: "",
  initial_salary_amount: "",
  initial_salary_currency: "",
};

type FormErrors = Partial<Record<keyof FormState, string>>;

const DECIMAL_RE = /^\d+(\.\d{1,2})?$/;

function validate(form: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!form.first_name.trim()) errors.first_name = "First name is required.";
  if (!form.last_name.trim()) errors.last_name = "Last name is required.";
  if (!/^\S+@\S+\.\S+$/.test(form.email)) {
    errors.email = "Enter a valid email address.";
  }
  if (!form.gender) errors.gender = "Select a gender.";
  if (!form.hire_date) {
    errors.hire_date = "Hire date is required.";
  } else if (new Date(form.hire_date) > new Date()) {
    errors.hire_date = "Hire date can't be in the future.";
  }
  if (!form.department_id) errors.department_id = "Select a department.";
  if (!form.job_role_id) errors.job_role_id = "Select a job role.";
  if (!form.level_id) errors.level_id = "Select a level.";
  if (!form.country_id) errors.country_id = "Select a country.";

  const hasAmount = form.initial_salary_amount.trim() !== "";
  const hasCurrency = form.initial_salary_currency.trim() !== "";
  if (hasAmount !== hasCurrency) {
    errors.initial_salary_amount =
      "Provide both an amount and a currency, or leave both blank.";
  } else if (hasAmount && !DECIMAL_RE.test(form.initial_salary_amount.trim())) {
    errors.initial_salary_amount = "Enter a valid amount, e.g. 50000.00.";
  }
  return errors;
}

export function AddEmployeeDialog({ reference }: { reference?: ReferenceData }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (input: CreateEmployeeInput) => createEmployee(input),
    onSuccess: (employee) => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      toast.success("Employee added", {
        description: `${employee.full_name} (${employee.employee_code}) was created.`,
      });
      setForm(EMPTY_FORM);
      setErrors({});
      setOpen(false);
    },
    onError: (error) => {
      if (error instanceof ApiError && error.details) {
        const fieldErrors: FormErrors = {};
        for (const detail of error.details) {
          if (detail.field in EMPTY_FORM) {
            fieldErrors[detail.field as keyof FormState] = detail.message;
          }
        }
        setErrors((prev) => ({ ...prev, ...fieldErrors }));
      }
      toast.error("Couldn't add employee", {
        description:
          error instanceof ApiError
            ? error.message
            : "An unexpected error occurred.",
      });
    },
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    const input: CreateEmployeeInput = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      gender: form.gender as CreateEmployeeInput["gender"],
      hire_date: form.hire_date,
      department_id: Number(form.department_id),
      job_role_id: Number(form.job_role_id),
      level_id: Number(form.level_id),
      country_id: Number(form.country_id),
    };
    if (form.initial_salary_amount && form.initial_salary_currency) {
      input.initial_salary = {
        amount: Number(form.initial_salary_amount).toFixed(2),
        currency: form.initial_salary_currency,
      };
    }
    mutation.mutate(input);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setForm(EMPTY_FORM);
          setErrors({});
        }
      }}
    >
      <DialogTrigger render={<Button />}>
        <Plus className="size-4" aria-hidden="true" />
        Add employee
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto sm:max-w-lg">
        <form onSubmit={handleSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>Add employee</DialogTitle>
            <DialogDescription>
              Creates a new employee record. You can record their first salary
              here, or add it later from their profile.
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-4 py-4">
            <Field label="First name" htmlFor="first_name" error={errors.first_name}>
              <Input
                id="first_name"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                aria-invalid={!!errors.first_name}
              />
            </Field>
            <Field label="Last name" htmlFor="last_name" error={errors.last_name}>
              <Input
                id="last_name"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                aria-invalid={!!errors.last_name}
              />
            </Field>
            <Field label="Email" htmlFor="email" error={errors.email} full>
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                aria-invalid={!!errors.email}
              />
            </Field>
            <Field label="Gender" htmlFor="gender" error={errors.gender}>
              <Select
                value={form.gender}
                onValueChange={(v) => setForm({ ...form, gender: v ?? "" })}
              >
                <SelectTrigger id="gender" className="w-full" aria-invalid={!!errors.gender}>
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  {reference?.genders.map((g) => (
                    <SelectItem key={g} value={g}>
                      {humanizeEnum(g)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Hire date" htmlFor="hire_date" error={errors.hire_date}>
              <Input
                id="hire_date"
                type="date"
                value={form.hire_date}
                onChange={(e) => setForm({ ...form, hire_date: e.target.value })}
                aria-invalid={!!errors.hire_date}
              />
            </Field>
            <Field label="Department" htmlFor="department_id" error={errors.department_id}>
              <Select
                value={form.department_id}
                onValueChange={(v) => setForm({ ...form, department_id: v ?? "" })}
              >
                <SelectTrigger id="department_id" className="w-full" aria-invalid={!!errors.department_id}>
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  {reference?.departments.map((d) => (
                    <SelectItem key={d.id} value={d.id.toString()}>
                      {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Job role" htmlFor="job_role_id" error={errors.job_role_id}>
              <Select
                value={form.job_role_id}
                onValueChange={(v) => setForm({ ...form, job_role_id: v ?? "" })}
              >
                <SelectTrigger id="job_role_id" className="w-full" aria-invalid={!!errors.job_role_id}>
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  {reference?.job_roles.map((r) => (
                    <SelectItem key={r.id} value={r.id.toString()}>
                      {r.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Level" htmlFor="level_id" error={errors.level_id}>
              <Select
                value={form.level_id}
                onValueChange={(v) => setForm({ ...form, level_id: v ?? "" })}
              >
                <SelectTrigger id="level_id" className="w-full" aria-invalid={!!errors.level_id}>
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  {reference?.levels.map((l) => (
                    <SelectItem key={l.id} value={l.id.toString()}>
                      {l.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Country" htmlFor="country_id" error={errors.country_id}>
              <Select
                value={form.country_id}
                onValueChange={(v) => {
                  const countryId = v ?? "";
                  const country = reference?.countries.find(
                    (c) => c.id.toString() === countryId,
                  );
                  setForm({
                    ...form,
                    country_id: countryId,
                    initial_salary_currency:
                      form.initial_salary_currency || country?.currency || "",
                  });
                }}
              >
                <SelectTrigger id="country_id" className="w-full" aria-invalid={!!errors.country_id}>
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  {reference?.countries.map((c) => (
                    <SelectItem key={c.id} value={c.id.toString()}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field
              label="Starting salary (optional)"
              htmlFor="initial_salary_amount"
              error={errors.initial_salary_amount}
            >
              <Input
                id="initial_salary_amount"
                inputMode="decimal"
                placeholder="e.g. 50000.00"
                value={form.initial_salary_amount}
                onChange={(e) =>
                  setForm({ ...form, initial_salary_amount: e.target.value })
                }
                aria-invalid={!!errors.initial_salary_amount}
              />
            </Field>
            <Field label="Currency" htmlFor="initial_salary_currency">
              <Input
                id="initial_salary_currency"
                placeholder="e.g. USD"
                maxLength={3}
                value={form.initial_salary_currency}
                onChange={(e) =>
                  setForm({
                    ...form,
                    initial_salary_currency: e.target.value.toUpperCase(),
                  })
                }
              />
            </Field>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Adding…" : "Add employee"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  htmlFor,
  error,
  full,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  full?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={full ? "col-span-2 space-y-1.5" : "space-y-1.5"}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
