import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, expect, it, vi } from "vitest";
import GraphView from "../../src/views/GraphView.vue";
import { getNeighbors, getNode, resolveObject } from "../../src/services/graph";
import { ApiError } from "../../src/services/http";
import type { GraphNeighborhood, GraphNode } from "../../src/types/graph";

vi.mock("../../src/services/graph", () => ({
  getNeighbors: vi.fn(),
  getNode: vi.fn(),
  resolveObject: vi.fn(),
}));

const center: GraphNode = {
  node_id: "gene:arabidopsis_thaliana:Atha04G0031690.v1.36",
  object_type: "Gene",
  label: "Atha04G0031690",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: { id: "Atha04G0031690.v1.36" },
};

function coreNode(nodeId: string, objectType: string, label: string): GraphNode {
  return {
    node_id: nodeId,
    object_type: objectType,
    label,
    species_id: "arabidopsis_thaliana",
    source_file: `${objectType.toLowerCase()}.jsonl`,
    properties: {},
  };
}

const species = coreNode(
  "species:arabidopsis_thaliana",
  "Species",
  "Arabidopsis thaliana",
);
const geneDataset = coreNode(
  "dataset:pgcp:arabidopsis:gene_annotation",
  "Dataset",
  "PGCP Gene Annotation",
);
const genomeDataset = coreNode(
  "dataset:pgcp:arabidopsis:genome_annotation",
  "Dataset",
  "PGCP Genome Annotation",
);
const location = coreNode(
  "location:Atha04G0031690",
  "GeneLocation",
  "Chr4:15006485-15008650",
);
const structure = coreNode(
  "structure:Atha04G0031690",
  "GeneStructure",
  "27 transcripts",
);

const coreNeighborhood: GraphNeighborhood = {
  node: center,
  nodes: [species, geneDataset, genomeDataset, location, structure],
  edges: [
    {
      source: center.node_id,
      predicate: "belongs_to_species",
      target: species.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    },
    {
      source: geneDataset.node_id,
      predicate: "contains_gene",
      target: center.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    },
    {
      source: center.node_id,
      predicate: "has_location",
      target: location.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    },
    {
      source: center.node_id,
      predicate: "has_structure",
      target: structure.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    },
    {
      source: center.node_id,
      predicate: "provided_by_dataset",
      target: genomeDataset.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    },
  ],
  total_edges: 59,
  matched_edges: 5,
  predicate_counts: {
    belongs_to_species: 1,
    contains_gene: 1,
    has_location: 1,
    has_sequence: 54,
    has_structure: 1,
    provided_by_dataset: 1,
  },
  truncated: false,
};

function sequenceNode(index: number, sequenceType: "CDS" | "PROTEIN"): GraphNode {
  return {
    node_id: `seq:${sequenceType.toLowerCase()}:${index}`,
    object_type: "SequenceRecord",
    label: `${sequenceType}-${index}`,
    species_id: "arabidopsis_thaliana",
    source_file: "sequence_records.jsonl",
    properties: { sequence_type: sequenceType },
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

beforeEach(() => vi.clearAllMocks());

async function mountGraph(path: string, configure: () => void = () => undefined) {
  vi.mocked(resolveObject).mockResolvedValue(center);
  vi.mocked(getNode).mockResolvedValue(center);
  vi.mocked(getNeighbors).mockResolvedValue(coreNeighborhood);
  configure();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/graph", name: "graph", component: GraphView },
      { path: "/genes/:id", name: "gene", component: { template: "<div />" } },
    ],
  });
  await router.push(path);
  const wrapper = mount(GraphView, {
    global: {
      plugins: [router],
      stubs: {
        GraphCanvas: {
          name: "GraphCanvas",
          props: ["neighborhood", "sequenceCount"],
          emits: ["select"],
          template: "<div data-test='graph-canvas' />",
        },
        SequenceDrawer: {
          name: "SequenceDrawer",
          props: ["open", "centerNodeId", "expectedCount"],
          emits: ["close", "showType"],
          template: "<div v-if='open' data-test='sequence-drawer' />",
        },
      },
    },
  });
  await flushPromises();
  await flushPromises();
  return { router, wrapper };
}

it("seeds and loads the real example from a bare route", async () => {
  const { router, wrapper } = await mountGraph("/graph");
  expect(router.currentRoute.value.query).toEqual({
    center: "Atha04G0031690.v1.36",
    species: "arabidopsis_thaliana",
    view: "core",
  });
  expect(resolveObject).toHaveBeenCalledWith(
    "Gene",
    "Atha04G0031690.v1.36",
    "arabidopsis_thaliana",
    expect.any(AbortSignal),
  );
  expect(getNeighbors).toHaveBeenCalledWith(
    center.node_id,
    { excludePredicates: ["has_sequence"], limit: 100 },
    expect.any(AbortSignal),
  );
  expect(wrapper.text()).toContain("59 source relationships");
  expect(wrapper.text()).toContain("7 displayed items");
});

it("keeps an invalid supplied route instead of replacing it", async () => {
  const { router, wrapper } = await mountGraph("/graph?center=missing&species=&view=core");
  expect(router.currentRoute.value.query.center).toBe("missing");
  expect(wrapper.text()).toContain("Choose a species before searching by public gene ID.");
  expect(resolveObject).not.toHaveBeenCalled();
});

it("updates the route when a relationship control is selected", async () => {
  const { router, wrapper } = await mountGraph("/graph");
  await wrapper.get('[data-predicate="has_location"]').trigger("click");
  await flushPromises();
  expect(router.currentRoute.value.query.predicate).toBe("has_location");
  expect(getNeighbors).toHaveBeenLastCalledWith(
    center.node_id,
    { predicate: "has_location", limit: 100 },
    expect.any(AbortSignal),
  );
});

it("rejects an empty submitted center without a request", async () => {
  const { wrapper } = await mountGraph("/graph");
  vi.clearAllMocks();
  await wrapper.get('[name="center_query"]').setValue("");
  await wrapper.get("form").trigger("submit");
  expect(wrapper.text()).toContain("Enter a gene ID.");
  expect(resolveObject).not.toHaveBeenCalled();
  expect(getNode).not.toHaveBeenCalled();
  expect(getNeighbors).not.toHaveBeenCalled();
});

it("loads a full node ID without a species scope", async () => {
  const nodeId = encodeURIComponent(center.node_id);
  await mountGraph(`/graph?center=${nodeId}&species=&view=core`);
  expect(getNode).toHaveBeenCalledWith(center.node_id, expect.any(AbortSignal));
  expect(resolveObject).not.toHaveBeenCalled();
});

it("maps service unavailability to stable user copy", async () => {
  const { wrapper } = await mountGraph("/graph", () => {
    vi.mocked(getNeighbors).mockRejectedValue(
      new ApiError(503, "/api/graph/neighbors/gene:test", "private database path"),
    );
  });
  expect(wrapper.text()).toContain("Knowledge graph is temporarily unavailable.");
  expect(wrapper.text()).not.toContain("private database path");
});

it("does not let an older request replace a newer route", async () => {
  let resolveFirst!: (node: GraphNode) => void;
  const first = new Promise<GraphNode>((resolve) => {
    resolveFirst = resolve;
  });
  const second = {
    ...center,
    node_id: "gene:arabidopsis_thaliana:second",
    label: "Second",
  };
  const { router, wrapper } = await mountGraph(
    "/graph?center=first&species=arabidopsis_thaliana&view=core",
    () => {
      vi.mocked(resolveObject).mockReturnValueOnce(first).mockResolvedValueOnce(second);
      vi.mocked(getNeighbors).mockImplementation(async (nodeId) => ({
        ...coreNeighborhood,
        node: nodeId === second.node_id ? second : center,
      }));
    },
  );
  await router.push("/graph?center=second&species=arabidopsis_thaliana&view=core");
  await flushPromises();
  resolveFirst(center);
  await flushPromises();
  expect(wrapper.text()).toContain("Second");
  expect(wrapper.text()).not.toContain("Atha04G0031690");
});

it("opens real sequence modes from the derived summary and returns to core", async () => {
  const { router, wrapper } = await mountGraph("/graph");
  wrapper.getComponent({ name: "GraphCanvas" }).vm.$emit("select", {
    kind: "summary",
    summary: {
      id: "presentation:sequence-summary",
      label: "Sequences (54)",
      predicate: "has_sequence",
      count: 54,
    },
  });
  await flushPromises();
  await flushPromises();
  expect(router.currentRoute.value.query.predicate).toBe("has_sequence");

  const drawer = wrapper.getComponent({ name: "SequenceDrawer" });
  expect(drawer.props("open")).toBe(true);
  drawer.vm.$emit("showType", "CDS", sequenceNeighborhood);
  await flushPromises();

  const sequenceCanvas = wrapper.getComponent({ name: "GraphCanvas" });
  const sequenceRecord = sequenceCanvas.props("neighborhood") as GraphNeighborhood;
  expect(sequenceRecord.nodes).toHaveLength(27);
  expect(sequenceRecord.nodes.every((node) => node.properties.sequence_type === "CDS")).toBe(true);
  expect(sequenceCanvas.props("sequenceCount")).toBe(0);
  expect(wrapper.text()).toContain("Viewing 27 CDS records");

  await wrapper.get('[data-test="back-to-core"]').trigger("click");
  const coreCanvas = wrapper.getComponent({ name: "GraphCanvas" });
  const coreRecord = coreCanvas.props("neighborhood") as GraphNeighborhood;
  expect(coreRecord.nodes).toHaveLength(5);
  expect(coreRecord.node).toEqual(center);
  expect(coreCanvas.props("sequenceCount")).toBe(54);
});
