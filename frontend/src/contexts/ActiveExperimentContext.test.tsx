import { act, render, screen, cleanup } from "@testing-library/react";
import { beforeEach, expect, test, afterEach } from "vitest";
import {
  ActiveExperimentProvider,
  useActiveExperiment,
  type ActiveExperiment,
} from "./ActiveExperimentContext";

const SAMPLE: ActiveExperiment = {
  condition: "robust_hof_K",
  variableTested: "robust_hof_K",
  scriptName: "run.py",
  worldType: "stoneage",
  seeds: [0, 1, 2, 3],
  launchedAt: 1000,
};

let api: ReturnType<typeof useActiveExperiment>;
function Probe() {
  api = useActiveExperiment();
  return <div>{api.activeExperiment?.condition ?? "none"}</div>;
}
const renderProbe = () =>
  render(
    <ActiveExperimentProvider>
      <Probe />
    </ActiveExperimentProvider>,
  );

beforeEach(() => window.localStorage.clear());
afterEach(() => cleanup());

test("set persiste dans localStorage et expose la valeur", () => {
  renderProbe();
  expect(screen.getByText("none")).toBeTruthy();
  act(() => api.setActiveExperiment(SAMPLE));
  expect(screen.getByText("robust_hof_K")).toBeTruthy();
  expect(JSON.parse(window.localStorage.getItem("agiseed.activeExperiment")!).condition).toBe("robust_hof_K");
});

test("update fait un merge partiel", () => {
  window.localStorage.setItem("agiseed.activeExperiment", JSON.stringify(SAMPLE));
  renderProbe();
  act(() => api.updateActiveExperiment({ baseline: "AND" }));
  expect(JSON.parse(window.localStorage.getItem("agiseed.activeExperiment")!).baseline).toBe("AND");
  expect(api.activeExperiment!.condition).toBe("robust_hof_K");
});

test("clear vide la valeur et le storage", () => {
  window.localStorage.setItem("agiseed.activeExperiment", JSON.stringify(SAMPLE));
  renderProbe();
  act(() => api.clearActiveExperiment());
  expect(screen.getByText("none")).toBeTruthy();
  expect(window.localStorage.getItem("agiseed.activeExperiment")).toBeNull();
});

test("lecture défensive sur storage corrompu", () => {
  window.localStorage.setItem("agiseed.activeExperiment", "{pas du json");
  renderProbe();
  expect(screen.getByText("none")).toBeTruthy();
});

test("lecture défensive sur JSON valide mais forme invalide", () => {
  window.localStorage.setItem("agiseed.activeExperiment", JSON.stringify({ foo: "bar" }));
  renderProbe();
  expect(screen.getByText("none")).toBeTruthy();
});

test("updateActiveExperiment est un no-op sans expérience active", () => {
  renderProbe();
  expect(screen.getByText("none")).toBeTruthy();
  act(() => api.updateActiveExperiment({ baseline: "AND" }));
  expect(screen.getByText("none")).toBeTruthy();
  expect(window.localStorage.getItem("agiseed.activeExperiment")).toBeNull();
});
