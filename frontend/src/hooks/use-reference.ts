"use client";

import { useQuery } from "@tanstack/react-query";
import { getReference } from "@/lib/api/reference";

export function useReference() {
  return useQuery({
    queryKey: ["reference"],
    queryFn: getReference,
    staleTime: 5 * 60_000,
  });
}
