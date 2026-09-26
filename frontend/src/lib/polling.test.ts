import { test, expect } from "vitest";
import { PILOTAGE_POLL, STATUS_POLL, livePoll } from "./polling";

test("PILOTAGE_POLL : 30 s, staleTime 5 s, pas de polling en fond", () => {
  expect(PILOTAGE_POLL).toEqual({
    refetchInterval: 30_000,
    staleTime: 5_000,
    refetchIntervalInBackground: false,
  });
});

test("STATUS_POLL : pas de polling en fond, staleTime 2s, intervalle 3s", () => {
  expect(STATUS_POLL).toEqual({
    refetchInterval: 3000,
    staleTime: 2000,
    refetchIntervalInBackground: false,
  });
});

test("livePoll : intervalle paramétré, staleTime 0, pas de polling en fond", () => {
  expect(livePoll(500)).toEqual({
    refetchInterval: 500,
    staleTime: 0,
    refetchIntervalInBackground: false,
  });
  expect(livePoll(2000).refetchInterval).toBe(2000);
});
