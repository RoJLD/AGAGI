import { describe, it, expect } from "vitest";
import { wsUrl, ApiError } from "./client";

describe("api/client", () => {
  it("wsUrl convertit http(s) en ws(s) et conserve le chemin", () => {
    const url = wsUrl("/ws/evolution");
    expect(url.startsWith("ws")).toBe(true);
    expect(url).toContain("/ws/evolution");
  });

  it("ApiError porte status, endpoint et hérite d'Error", () => {
    const err = new ApiError(404, "/api/experiments/NAND", "introuvable");
    expect(err.status).toBe(404);
    expect(err.endpoint).toBe("/api/experiments/NAND");
    expect(err).toBeInstanceOf(Error);
  });
});
