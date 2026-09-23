import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getOne, getPage } from "./api";

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("unwraps the data envelope and forwards query params", async () => {
    const fetchMock = mockFetch(200, {
      data: [{ patient_id: "p1" }],
      error: null,
      meta: { limit: 25, next_cursor: "abc" },
    });

    const page = await getPage("/patients", { last_name: "Doe", cursor: undefined, limit: 25 });

    expect(page).toEqual({ items: [{ patient_id: "p1" }], nextCursor: "abc" });
    const url = new URL(fetchMock.mock.calls[0][0]);
    expect(url.pathname).toBe("/patients");
    expect(url.searchParams.get("last_name")).toBe("Doe");
    expect(url.searchParams.has("cursor")).toBe(false);
  });

  it("throws ApiError with the envelope's error", async () => {
    mockFetch(404, { data: null, error: { code: "not_found", message: "Patient not found." } });

    const error = await getOne("/patients/x").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, code: "not_found", message: "Patient not found." });
  });
});
