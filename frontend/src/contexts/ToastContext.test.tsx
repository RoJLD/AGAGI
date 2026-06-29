import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { ToastProvider, useToast } from "./ToastContext";

afterEach(() => cleanup());

function Trigger({ kind }: { kind: "success" | "error" | "info" }) {
  const { notify } = useToast();
  return <button onClick={() => notify(`Message ${kind}`, kind)}>go-{kind}</button>;
}

test("un toast d'erreur expose role=alert", () => {
  render(<ToastProvider><Trigger kind="error" /></ToastProvider>);
  fireEvent.click(screen.getByText("go-error"));
  expect(screen.getByRole("alert").textContent).toContain("Message error");
});

test("un toast de succès expose role=status", () => {
  render(<ToastProvider><Trigger kind="success" /></ToastProvider>);
  fireEvent.click(screen.getByText("go-success"));
  expect(screen.getByRole("status").textContent).toContain("Message success");
});

test("le bouton Fermer retire le toast", () => {
  render(<ToastProvider><Trigger kind="info" /></ToastProvider>);
  fireEvent.click(screen.getByText("go-info"));
  expect(screen.getByText("Message info")).toBeTruthy();
  fireEvent.click(screen.getByLabelText("Fermer"));
  expect(screen.queryByText("Message info")).toBeNull();
});
