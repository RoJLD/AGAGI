import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
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

test("respecte l'id de l'enfant même sans htmlFor", () => {
  render(
    <Field label="Seed">
      <input id="explicit-id" type="number" />
    </Field>,
  );
  const input = screen.getByLabelText("Seed");
  expect(input.getAttribute("id")).toBe("explicit-id");
});
