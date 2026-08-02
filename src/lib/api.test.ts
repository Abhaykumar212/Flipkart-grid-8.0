import { afterEach, describe, expect, it, vi } from "vitest";
import { apiGet } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("API client", () => {
  it("normalizes problem+json failures", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      type: "about:blank",
      title: "Validation error",
      status: 422,
      detail: "Request validation failed",
      errors: [{ loc: ["body", "metadata"], msg: "Invalid", type: "value_error" }],
    }), {
      status: 422,
      headers: { "Content-Type": "application/problem+json" },
    }));

    await expect(apiGet("/api/v1/example")).rejects.toMatchObject({
      status: 422,
      message: "Request validation failed",
      problem: { title: "Validation error" },
    });
  });
});
