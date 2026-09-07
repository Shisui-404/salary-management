import type { ApiErrorBody } from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/**
 * Typed error thrown by `fetchJson` for any non-2xx response.
 *
 * Mirrors the contract's error envelope `{ error: { code, message, details } }`
 * so callers can branch on `code` and surface `message` directly in the UI.
 */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: { field: string; message: string }[] | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: { field: string; message: string }[] | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** True when a value already looks like a parsed `ApiErrorBody`. */
function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }
  const err = (value as { error?: unknown }).error;
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    "message" in err
  );
}

export interface FetchJsonOptions extends Omit<RequestInit, "body"> {
  /** Query params to append; `undefined`/`null` values are dropped. */
  query?: Record<string, string | number | boolean | undefined | null>;
  /**
   * Request body. A `FormData` instance is sent as-is (for multipart
   * uploads, e.g. CSV import); anything else is `JSON.stringify`'d with a
   * JSON content-type.
   */
  body?: unknown;
}

function buildUrl(path: string, query?: FetchJsonOptions["query"]): string {
  const url = new URL(
    path.startsWith("http") ? path : `${API_BASE_URL}${path}`,
  );
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === "") continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

/**
 * The single fetch wrapper the whole app funnels through.
 *
 * - Serialises `query`/`body`.
 * - Parses the API's `{ error: { code, message, details } }` envelope on
 *   failure and throws a typed `ApiError` — components never see raw
 *   `Response` objects or untyped JSON.
 * - Throws `ApiError` with code `network_error` if `fetch` itself rejects
 *   (backend unreachable), so callers have one error type to handle.
 */
export async function fetchJson<T>(
  path: string,
  options: FetchJsonOptions = {},
): Promise<T> {
  const { query, body, headers, ...rest } = options;
  const url = buildUrl(path, query);
  const isFormData = body instanceof FormData;

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      headers: {
        ...(body !== undefined && !isFormData
          ? { "Content-Type": "application/json" }
          : {}),
        Accept: "application/json",
        ...headers,
      },
      body:
        body === undefined
          ? undefined
          : isFormData
            ? (body as FormData)
            : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Could not reach the API. Confirm the backend is running and NEXT_PUBLIC_API_URL is correct.",
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload: unknown = isJson
    ? await response.json().catch(() => null)
    : await response.text().catch(() => null);

  if (!response.ok) {
    if (isApiErrorBody(payload)) {
      throw new ApiError(
        response.status,
        payload.error.code,
        payload.error.message,
        payload.error.details,
      );
    }
    throw new ApiError(
      response.status,
      "unknown_error",
      typeof payload === "string" && payload
        ? payload
        : `Request failed with status ${response.status}`,
    );
  }

  return payload as T;
}

/** Fetches a raw response for endpoints that don't return JSON (e.g. CSV export). */
export async function fetchBlob(
  path: string,
  query?: FetchJsonOptions["query"],
): Promise<Blob> {
  const url = buildUrl(path, query);
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new ApiError(0, "network_error", "Could not reach the API.");
  }
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    if (isApiErrorBody(payload)) {
      throw new ApiError(
        response.status,
        payload.error.code,
        payload.error.message,
        payload.error.details,
      );
    }
    throw new ApiError(
      response.status,
      "unknown_error",
      `Export failed with status ${response.status}`,
    );
  }
  return response.blob();
}
