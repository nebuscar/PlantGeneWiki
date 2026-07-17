import { describe, expect, it } from "vitest";
import { graphStyles } from "../../src/lib/graph-style";

describe("graph style contract", () => {
  it("hides default labels and distinguishes presentation summaries", () => {
    const style = (selector: string) => {
      const item = graphStyles.find((candidate) => candidate.selector === selector) as
        | { style: Record<string, unknown> }
        | undefined;
      return item?.style ?? {};
    };
    expect(style("node").label).toBe("");
    expect(style("edge").label).toBe("");
    expect(style("node[?isCenter], node:selected, node.hovered").label).toBe("data(label)");
    expect(style("edge:selected, edge.hovered").label).toBe("data(predicate)");
    expect(style('node[presentationKind = "summary"]')["border-style"]).toBe("dashed");
    expect(style('edge[presentationKind = "summary"]')["line-style"]).toBe("dashed");
  });
});
