import { render, screen, cleanup } from "@testing-library/react";
import { vi, test, expect, afterEach } from "vitest";

// useWebSocket ouvre une vraie WebSocket dans un effet -> on le mocke (pas de réseau en test).
vi.mock("../hooks/useWebSocket", () => ({ useWebSocket: () => ({ status: "closed" }) }));
import { FlatlandViewer } from "./FlatlandViewer";

afterEach(() => cleanup());

test("l'overlay des métriques porte la classe DS flatland-overlay", () => {
  render(<FlatlandViewer />);
  const title = screen.getByText("Flatland Metrics");
  expect(title.parentElement?.className).toBe("flatland-overlay");
});

test("le conteneur porte la classe DS flatland-frame", () => {
  const { container } = render(<FlatlandViewer />);
  expect(container.querySelector(".flatland-frame")).toBeTruthy();
});
