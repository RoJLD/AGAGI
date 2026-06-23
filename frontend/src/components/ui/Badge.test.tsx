import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Badge } from "./Badge";

describe("Badge", () => {
  it("applique la classe de variante", () => {
    const { getByText } = render(<Badge variant="danger">Alerte</Badge>);
    expect(getByText("Alerte").className).toContain("badge--danger");
  });
});
