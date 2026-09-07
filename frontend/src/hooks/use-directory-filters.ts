"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";
import {
  type DirectoryFilters,
  filtersToSearchParams,
  searchParamsToFilters,
} from "@/lib/employee-query-params";

/**
 * Single source of truth for the employee directory's filter/sort/page
 * state, kept in the URL (`useSearchParams`) so views are shareable and
 * back/forward works — see `src/lib/employee-query-params.ts` for the
 * serialisation rules this relies on.
 */
export function useDirectoryFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo(
    () => searchParamsToFilters(searchParams),
    [searchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<DirectoryFilters>) => {
      const changingPage = Object.prototype.hasOwnProperty.call(patch, "page");
      const next: DirectoryFilters = {
        ...filters,
        ...patch,
        page: changingPage ? (patch.page ?? filters.page) : 1,
      };
      const qs = filtersToSearchParams(next).toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [filters, pathname, router],
  );

  const resetFilters = useCallback(() => {
    router.push(pathname, { scroll: false });
  }, [pathname, router]);

  return { filters, setFilters, resetFilters };
}
