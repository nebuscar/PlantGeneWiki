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
const dataset = coreNode("dataset:pgcp:arabidopsis", "Dataset", "PGCP Arabidopsis");
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
  nodes: [species, dataset, location, structure],
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
      source: dataset.node_id,
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
      target: dataset.node_id,
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
      stubs: { GraphCanvas: { template: "<div data-test='graph-canvas' />" } },
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
  expect(wrapper.text()).toContain("6 displayed items");
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
