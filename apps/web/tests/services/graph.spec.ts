import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getGeneWikiRecord,
  getGraphSummary,
  ObjectNotFoundError,
  resolveObject,
  searchNodes,
} from "../../src/services/graph";
import { ApiError } from "../../src/services/http";
import type { GraphNode } from "../../src/types/graph";

afterEach(() => vi.restoreAllMocks());

describe("graph service", () => {
  it("sends graph search filters to FastAPI", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ query: "Atha", count: 0, nodes: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await searchNodes({
      q: "Atha",
      objectType: "Gene",
      speciesId: "arabidopsis_thaliana",
      limit: 25,
    });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("object_type=Gene"),
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "application/json" }) }),
    );
  });

  it("resolves an exact public label from graph search", async () => {
    const node: GraphNode = {
      node_id: "gene:atha:Atha01G0000010.v1.36",
      object_type: "Gene",
      label: "Atha01G0000010.v1.36",
      species_id: "arabidopsis_thaliana",
      source_file: "genes.jsonl",
      properties: { id: "Atha01G0000010.v1.36" },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          query: "Atha01G0000010.v1.36",
          count: 1,
          nodes: [node],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(
      resolveObject("Gene", "Atha01G0000010.v1.36", "arabidopsis_thaliana"),
    ).resolves.toEqual(node);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("species_id=arabidopsis_thaliana"),
      expect.any(Object),
    );
  });

  it("throws a typed error when no exact object matches", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ query: "missing", count: 0, nodes: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(resolveObject("Gene", "missing")).rejects.toBeInstanceOf(ObjectNotFoundError);
  });

  it("requests the complete Gene Wiki record with an encoded node ID", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ node: null, edges: [], nodes: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await getGeneWikiRecord("gene:arabidopsis_thaliana:Atha01G0000010.v1.36");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining(
        "/api/wiki/genes/gene%3Aarabidopsis_thaliana%3AAtha01G0000010.v1.36",
      ),
      expect.any(Object),
    );
  });

  it("preserves FastAPI error status, path, and detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Graph database unavailable" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const error = await getGraphSummary().catch((reason: unknown) => reason);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 503,
      path: "/api/graph/summary",
      detail: "Graph database unavailable",
    });
  });
});
