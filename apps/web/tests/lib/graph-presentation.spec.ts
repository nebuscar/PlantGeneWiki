import { describe, expect, it } from "vitest";
import { filterSequenceNeighborhood } from "../../src/lib/graph-presentation";
import type { GraphNeighborhood, GraphNode } from "../../src/types/graph";

const center: GraphNode = {
  node_id: "gene:test",
  object_type: "Gene",
  label: "Gene test",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: {},
};
const cds: GraphNode = {
  ...center,
  node_id: "seq:cds:1",
  object_type: "SequenceRecord",
  properties: { sequence_type: "CDS" },
};
const protein: GraphNode = {
  ...center,
  node_id: "seq:protein:1",
  object_type: "SequenceRecord",
  properties: { sequence_type: "PROTEIN" },
};
const sequenceNeighborhood: GraphNeighborhood = {
  node: center,
  nodes: [cds, protein],
  edges: [
    {
      source: center.node_id,
      predicate: "has_sequence",
      target: cds.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    },
    {
      source: center.node_id,
      predicate: "has_sequence",
      target: protein.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    },
  ],
  total_edges: 2,
  matched_edges: 2,
  predicate_counts: { has_sequence: 2 },
  truncated: false,
};

describe("sequence graph presentation", () => {
  it("keeps only real nodes and edges for the requested sequence type", () => {
    const filtered = filterSequenceNeighborhood(sequenceNeighborhood, "CDS");
    expect(filtered.nodes.map((node) => node.node_id)).toEqual(["seq:cds:1"]);
    expect(filtered.edges.map((edge) => edge.target)).toEqual(["seq:cds:1"]);
    expect(filtered.node).toEqual(sequenceNeighborhood.node);
    expect(sequenceNeighborhood.nodes).toEqual([cds, protein]);
  });
});
