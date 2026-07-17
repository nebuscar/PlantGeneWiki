import { describe, expect, it } from "vitest";
import {
  SEQUENCE_SUMMARY_ID,
  toCytoscapeElements,
} from "../../src/lib/graph-elements";

const center = {
  node_id: "gene:atha:Atha01",
  object_type: "Gene",
  label: "Atha01",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: {},
};

const neighborhood = {
  node: center,
  nodes: [
    center,
    {
      node_id: "species:arabidopsis_thaliana",
      object_type: "Species",
      label: "Arabidopsis thaliana",
      species_id: "arabidopsis_thaliana",
      source_file: "species.jsonl",
      properties: {},
    },
  ],
  edges: [
    {
      source: center.node_id,
      predicate: "belongs_to_species",
      target: "species:arabidopsis_thaliana",
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "asserted",
      properties: {},
    },
  ],
  total_edges: 1,
  matched_edges: 1,
  predicate_counts: { belongs_to_species: 1 },
  truncated: false,
};

describe("toCytoscapeElements", () => {
  it("maps one neighborhood without duplicating the center node", () => {
    const elements = toCytoscapeElements(neighborhood);
    expect(elements.nodes.filter((item) => item.data.id === center.node_id)).toHaveLength(1);
    expect(elements.edges[0].data.predicate).toBe("belongs_to_species");
  });

  it("adds a derived sequence summary without mutating graph truth", () => {
    const originalNodes = [...neighborhood.nodes];
    const elements = toCytoscapeElements(neighborhood, { sequenceCount: 54 });
    const summary = elements.nodes.find((item) => item.data.id === SEQUENCE_SUMMARY_ID);

    expect(summary?.data).toMatchObject({
      label: "Sequences (54)",
      presentationKind: "summary",
      objectType: "SequenceSummary",
    });
    expect(elements.selectionById.get(SEQUENCE_SUMMARY_ID)).toEqual({
      kind: "summary",
      summary: {
        id: SEQUENCE_SUMMARY_ID,
        label: "Sequences (54)",
        predicate: "has_sequence",
        count: 54,
      },
    });
    expect(neighborhood.nodes).toEqual(originalNodes);
    expect(neighborhood.nodes.some((node) => node.node_id === SEQUENCE_SUMMARY_ID)).toBe(false);
  });
});
