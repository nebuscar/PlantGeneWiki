import { describe, expect, it } from "vitest";
import { routes } from "../src/router";

describe("router contract", () => {
  it("registers all PhytoAtlas routes", () => {
    expect(routes.map((route) => route.name)).toEqual([
      "home",
      "search",
      "gene",
      "species",
      "graph",
      "dataset",
      "sequence-record",
      "literature",
      "tools",
      "not-found",
    ]);
  });
});
