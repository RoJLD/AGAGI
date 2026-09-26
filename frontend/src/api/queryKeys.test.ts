import { test, expect } from "vitest";
import { queryKeys } from "./queryKeys";

test("clé notes d'un run", () => {
  expect(queryKeys.runs.notes("lewis_42")).toEqual(["runs", "notes", "lewis_42"]);
});

test("clé du flux notes", () => {
  expect(queryKeys.notes).toEqual(["notes"]);
});

test("clé du pilotage, partagée par les trois vues", () => {
  expect(queryKeys.pm.pilotage).toEqual(["pm", "pilotage"]);
});
