import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { test, expect, vi, afterEach } from "vitest";
import { StepBar } from "./StepBar";

afterEach(cleanup);

const reached = { lancer: true, suivre: true, comparer: false, conclure: false };

test("rend 4 onglets d'étape avec aria-selected sur l'étape courante", () => {
  render(<StepBar current="suivre" reached={reached} onSelect={() => {}} />);
  const tabs = screen.getAllByRole("tab");
  expect(tabs).toHaveLength(4);
  expect(screen.getByTestId("step-suivre").getAttribute("aria-selected")).toBe("true");
  expect(screen.getByTestId("step-lancer").getAttribute("aria-selected")).toBe("false");
});

test("clic sur une étape appelle onSelect avec sa clé", () => {
  const onSelect = vi.fn();
  render(<StepBar current="lancer" reached={reached} onSelect={onSelect} />);
  fireEvent.click(screen.getByTestId("step-comparer"));
  expect(onSelect).toHaveBeenCalledWith("comparer");
});

test("roving tabindex : l'étape courante est focusable, les autres non", () => {
  render(<StepBar current="suivre" reached={{ lancer: true, suivre: true, comparer: false, conclure: false }} onSelect={() => {}} />);
  expect(screen.getByTestId("step-suivre").getAttribute("tabindex")).toBe("0");
  expect(screen.getByTestId("step-lancer").getAttribute("tabindex")).toBe("-1");
});

test("flèche droite déplace le focus sans activer (activation manuelle)", () => {
  const onSelect = vi.fn();
  render(<StepBar current="lancer" reached={{ lancer: true, suivre: false, comparer: false, conclure: false }} onSelect={onSelect} />);
  const first = screen.getByTestId("step-lancer");
  first.focus();
  fireEvent.keyDown(first, { key: "ArrowRight" });
  expect(document.activeElement).toBe(screen.getByTestId("step-suivre"));
  expect(onSelect).not.toHaveBeenCalled();
});
