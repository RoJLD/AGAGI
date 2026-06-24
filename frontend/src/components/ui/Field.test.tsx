import { render, screen } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { cleanup } from "@testing-library/react";
import { Field } from "./Field";

afterEach(() => cleanup());

test("associe le label à l'input via un id généré", () => {
  render(
    <Field label="Graine">
      <input type="number" />
    </Field>,
  );
  // getByLabelText ne réussit que si label.htmlFor === input.id
  const input = screen.getByLabelText("Graine");
  expect(input.tagName).toBe("INPUT");
});

test("respecte un id fourni par l'appelant", () => {
  render(
    <Field label="Script" htmlFor="my-id">
      <select id="my-id">
        <option>a</option>
      </select>
    </Field>,
  );
  const select = screen.getByLabelText("Script");
  expect(select.getAttribute("id")).toBe("my-id");
});
