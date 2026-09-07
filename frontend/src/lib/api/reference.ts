import { fetchJson } from "./client";
import type { ReferenceData } from "./types";

export function getReference(): Promise<ReferenceData> {
  return fetchJson<ReferenceData>("/reference");
}
