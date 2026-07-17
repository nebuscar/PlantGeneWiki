import { describe, expect, it } from "vitest";
import {
  DEFAULT_GRAPH_QUERY,
  graphQueryError,
  readGraphQuery,
  writeGraphQuery,
} from "../../src/lib/graph-query";

describe("graph query contract", () => {
  it("distinguishes a bare route from a supplied route", () => {
    expect(readGraphQuery({})).toBeNull();
    expect(readGraphQuery({ center: "Atha01", species: "arabidopsis_thaliana" })).toEqual({
      center: "Atha01",
      species: "arabidopsis_thaliana",
      view: "core",
      predicate: "",
    });
  });

  it("validates scoped public identifiers", () => {
    expect(graphQueryError({ ...DEFAULT_GRAPH_QUERY, center: "" })).toBe("Enter a gene ID.");
    expect(graphQueryError({ ...DEFAULT_GRAPH_QUERY, species: "" })).toBe(
      "Choose a species before searching by public gene ID.",
    );
    expect(
      graphQueryError({
        ...DEFAULT_GRAPH_QUERY,
        center: "gene:arabidopsis_thaliana:Atha01",
        species: "",
      }),
    ).toBe("");
  });

  it("writes only stable supported parameters", () => {
    expect(writeGraphQuery({ ...DEFAULT_GRAPH_QUERY, predicate: "has_location" })).toEqual({
      center: "Atha04G0031690.v1.36",
      species: "arabidopsis_thaliana",
      view: "core",
      predicate: "has_location",
    });
  });
});
