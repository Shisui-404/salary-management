import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, fetchJson } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("fetchJson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed JSON body on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(200, { id: 1, name: "Ada" })),
    );

    const result = await fetchJson<{ id: number; name: string }>("/employees/1");
    expect(result).toEqual({ id: 1, name: "Ada" });
  });

  it("parses the contract's error envelope into a typed ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(404, {
          error: {
            code: "employee_not_found",
            message: "Employee 42 does not exist",
            details: null,
          },
        }),
      ),
    );

    await expect(fetchJson("/employees/42")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      code: "employee_not_found",
      message: "Employee 42 does not exist",
      details: null,
    });
  });

  it("carries validation_error field details through to the thrown error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          error: {
            code: "validation_error",
            message: "Validation failed",
            details: [{ field: "email", message: "Invalid email" }],
          },
        }),
      ),
    );

    try {
      await fetchJson("/employees", { method: "POST", body: {} });
      expect.unreachable("fetchJson should have thrown");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiError = error as ApiError;
      expect(apiError.code).toBe("validation_error");
      expect(apiError.details).toEqual([
        { field: "email", message: "Invalid email" },
      ]);
    }
  });

  it("throws a network_error ApiError when fetch itself rejects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("fetch failed")),
    );

    await expect(fetchJson("/employees")).rejects.toMatchObject({
      name: "ApiError",
      code: "network_error",
      status: 0,
    });
  });

  it("falls back to a generic ApiError for a non-JSON error response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("Internal Server Error", {
          status: 500,
          headers: { "content-type": "text/plain" },
        }),
      ),
    );

    await expect(fetchJson("/employees")).rejects.toMatchObject({
      name: "ApiError",
      status: 500,
    });
  });

  it("appends query params and drops undefined/null/empty values", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { items: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchJson("/employees", {
      query: { search: "ada", department_id: undefined, gender: null, limit: 25 },
    });

    const calledUrl = new URL(fetchMock.mock.calls[0][0] as string);
    expect(calledUrl.searchParams.get("search")).toBe("ada");
    expect(calledUrl.searchParams.has("department_id")).toBe(false);
    expect(calledUrl.searchParams.has("gender")).toBe(false);
    expect(calledUrl.searchParams.get("limit")).toBe("25");
  });

  it("sends a JSON body with a JSON content-type for object bodies", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(201, { id: 1 }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchJson("/employees", { method: "POST", body: { first_name: "Ada" } });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(JSON.stringify({ first_name: "Ada" }));
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe(
      "application/json",
    );
  });

  it("sends a FormData body as-is, without a JSON content-type", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { total_rows: 0 }));
    vi.stubGlobal("fetch", fetchMock);

    const form = new FormData();
    form.append("file", new Blob(["a,b"], { type: "text/csv" }), "test.csv");
    await fetchJson("/employees/import", { method: "POST", body: form });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(form);
    expect(
      (init.headers as Record<string, string>)["Content-Type"],
    ).toBeUndefined();
  });
});
