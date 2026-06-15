import { describe, it, expect, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useHashRoute } from "./useHashRoute";

const TABS = ["edr", "sandbox", "comparison"] as const;

describe("useHashRoute", () => {
  beforeEach(() => {
    window.location.hash = "";
  });

  it("retombe sur l'onglet par défaut quand le hash est vide", () => {
    const { result } = renderHook(() => useHashRoute(TABS, "edr"));
    expect(result.current.tab).toBe("edr");
    expect(result.current.gate).toBe("");
  });

  it("parse l'onglet et la gate depuis le hash", () => {
    window.location.hash = "#/sandbox?gate=XOR";
    const { result } = renderHook(() => useHashRoute(TABS, "edr"));
    expect(result.current.tab).toBe("sandbox");
    expect(result.current.gate).toBe("XOR");
  });

  it("ignore un onglet inconnu et garde le défaut", () => {
    window.location.hash = "#/inconnu";
    const { result } = renderHook(() => useHashRoute(TABS, "edr"));
    expect(result.current.tab).toBe("edr");
  });

  it("expose les paramètres de query (ex: ab pour le deep-link A/B)", () => {
    window.location.hash = "#/comparison?ab=robust_eval";
    const { result } = renderHook(() => useHashRoute(TABS, "edr"));
    expect(result.current.tab).toBe("comparison");
    expect(result.current.query.ab).toBe("robust_eval");
  });

  it("navigate écrit un hash avec onglet + paramètres", () => {
    const { result } = renderHook(() => useHashRoute(TABS, "edr"));
    result.current.navigate("comparison", { ab: "baseline" });
    expect(window.location.hash).toContain("/comparison");
    expect(window.location.hash).toContain("ab=baseline");
  });
});
