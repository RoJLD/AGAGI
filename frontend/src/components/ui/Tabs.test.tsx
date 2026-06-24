import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, test, expect, vi } from "vitest";
import { TabList, tabId, panelId } from "./Tabs";

afterEach(() => cleanup());

const ITEMS = [
  { id: "a", label: "Un" },
  { id: "b", label: "Deux" },
  { id: "c", label: "Trois" },
];

test("rend un tablist avec aria-selected et roving tabindex", () => {
  render(<TabList items={ITEMS} activeId="b" onSelect={() => {}} ariaLabel="Sections" />);
  expect(screen.getByRole("tablist").getAttribute("aria-label")).toBe("Sections");
  const tabs = screen.getAllByRole("tab");
  expect(tabs).toHaveLength(3);
  expect(screen.getByTestId("tab-b").getAttribute("aria-selected")).toBe("true");
  expect(screen.getByTestId("tab-b").getAttribute("tabindex")).toBe("0");
  expect(screen.getByTestId("tab-a").getAttribute("tabindex")).toBe("-1");
  expect(screen.getByTestId("tab-b").getAttribute("aria-controls")).toBe(panelId("b"));
});

test("flèches déplacent le focus (avec wrap) sans activer", () => {
  const onSelect = vi.fn();
  render(<TabList items={ITEMS} activeId="a" onSelect={onSelect} ariaLabel="Sections" />);
  const first = screen.getByTestId("tab-a");
  first.focus();
  fireEvent.keyDown(first, { key: "ArrowRight" });
  expect(document.activeElement).toBe(screen.getByTestId("tab-b"));
  // wrap depuis le dernier
  screen.getByTestId("tab-c").focus();
  fireEvent.keyDown(screen.getByTestId("tab-c"), { key: "ArrowRight" });
  expect(document.activeElement).toBe(screen.getByTestId("tab-a"));
  // activation manuelle : déplacer le focus n'a pas sélectionné
  expect(onSelect).not.toHaveBeenCalled();
});

test("Home/End vont aux extrémités", () => {
  render(<TabList items={ITEMS} activeId="b" onSelect={() => {}} ariaLabel="Sections" />);
  const mid = screen.getByTestId("tab-b");
  mid.focus();
  fireEvent.keyDown(mid, { key: "End" });
  expect(document.activeElement).toBe(screen.getByTestId("tab-c"));
  fireEvent.keyDown(screen.getByTestId("tab-c"), { key: "Home" });
  expect(document.activeElement).toBe(screen.getByTestId("tab-a"));
});

test("Entrée, Espace et clic activent l'onglet", () => {
  const onSelect = vi.fn();
  render(<TabList items={ITEMS} activeId="a" onSelect={onSelect} ariaLabel="Sections" />);
  fireEvent.keyDown(screen.getByTestId("tab-b"), { key: "Enter" });
  fireEvent.keyDown(screen.getByTestId("tab-c"), { key: " " });
  fireEvent.click(screen.getByTestId("tab-b"));
  expect(onSelect.mock.calls.map((c) => c[0])).toEqual(["b", "c", "b"]);
});

test("testIdPrefix personnalise les data-testid", () => {
  render(<TabList items={ITEMS} activeId="a" onSelect={() => {}} ariaLabel="Étapes" testIdPrefix="step" />);
  expect(screen.getByTestId("step-a")).toBeTruthy();
  expect(tabId("a")).toBe("tab-a");
});
