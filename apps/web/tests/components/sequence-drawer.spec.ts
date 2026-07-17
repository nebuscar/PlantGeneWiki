import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import SequenceDrawer from "../../src/components/graph/SequenceDrawer.vue";
import { getNeighbors } from "../../src/services/graph";
import type { GraphNeighborhood, GraphNode } from "../../src/types/graph";

vi.mock("../../src/services/graph", () => ({ getNeighbors: vi.fn() }));
afterEach(() => vi.clearAllMocks());

const center: GraphNode = {
  node_id: "gene:arabidopsis_thaliana:Atha04G0031690.v1.36",
  object_type: "Gene",
  label: "Atha04G0031690",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: { id: "Atha04G0031690.v1.36" },
};

function sequenceNode(index: number, sequenceType: "CDS" | "PROTEIN"): GraphNode {
  const nodeId = `seq:${sequenceType.toLowerCase()}:${index}`;
  return {
    node_id: nodeId,
    object_type: "SequenceRecord",
    label: `${sequenceType}-${index}`,
    species_id: "arabidopsis_thaliana",
    source_file: "sequence_records.jsonl",
    properties: {
      id: `${sequenceType}-${index}`,
      sequence_type: sequenceType,
      length: 100 + index,
    },
  };
}

const sequenceNodes = [
  ...Array.from({ length: 27 }, (_, index) => sequenceNode(index + 1, "CDS")),
  ...Array.from({ length: 27 }, (_, index) => sequenceNode(index + 1, "PROTEIN")),
];
const sequenceNeighborhood: GraphNeighborhood = {
  node: center,
  nodes: sequenceNodes,
  edges: sequenceNodes.map((node) => ({
    source: center.node_id,
    predicate: "has_sequence",
    target: node.node_id,
    species_id: "arabidopsis_thaliana",
    source_dataset: "dataset:test",
    evidence: "test",
    properties: {},
  })),
  total_edges: 59,
  matched_edges: 54,
  predicate_counts: { has_sequence: 54 },
  truncated: false,
};

it("loads and groups real sequence relationships on demand", async () => {
  vi.mocked(getNeighbors).mockResolvedValue(sequenceNeighborhood);
  const wrapper = mount(SequenceDrawer, {
    props: { open: true, centerNodeId: center.node_id, expectedCount: 54 },
    global: { stubs: { RouterLink: true } },
  });
  await flushPromises();

  expect(getNeighbors).toHaveBeenCalledWith(
    center.node_id,
    { predicate: "has_sequence", limit: 100 },
    expect.any(AbortSignal),
  );
  expect(wrapper.text()).toContain("CDS (27)");
  expect(wrapper.text()).toContain("Protein (27)");
  await wrapper.get('[data-sequence-type="CDS"]').trigger("click");
  expect(wrapper.emitted("showType")?.[0]).toEqual(["CDS", sequenceNeighborhood]);
});

it("reports explicit sequence truncation", async () => {
  const nodes = Array.from({ length: 100 }, (_, index) => sequenceNode(index + 1, "CDS"));
  vi.mocked(getNeighbors).mockResolvedValue({
    node: center,
    nodes,
    edges: nodes.map((node) => ({
      source: center.node_id,
      predicate: "has_sequence",
      target: node.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    })),
    total_edges: 155,
    matched_edges: 150,
    predicate_counts: { has_sequence: 150, has_location: 5 },
    truncated: true,
  });
  const wrapper = mount(SequenceDrawer, {
    props: { open: true, centerNodeId: center.node_id, expectedCount: 150 },
    global: { stubs: { RouterLink: true } },
  });
  await flushPromises();
  expect(wrapper.text()).toContain("Showing 100 of 150 sequence relationships.");
});
