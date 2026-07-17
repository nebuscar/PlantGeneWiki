import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import GraphView from "../../src/views/GraphView.vue";
import { getNeighbors, searchNodes } from "../../src/services/graph";

vi.mock("../../src/services/graph", () => ({
  getNeighbors: vi.fn(),
  getNode: vi.fn(),
  searchNodes: vi.fn(),
}));

const center = {
  node_id: "gene:atha:Atha01",
  object_type: "Gene",
  label: "Atha01",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: {},
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(searchNodes).mockResolvedValue({ query: "Atha01", count: 1, nodes: [center] });
  vi.mocked(getNeighbors).mockResolvedValue({
    node: center,
    nodes: [],
    edges: [],
    total_edges: 0,
    matched_edges: 0,
    predicate_counts: {},
    truncated: false,
  });
});

describe("GraphView", () => {
  it("loads a species-scoped center and predicate neighborhood", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/graph", name: "graph", component: GraphView },
        { path: "/genes/:id", name: "gene", component: { template: "<div />" } },
      ],
    });
    await router.push("/graph");
    const wrapper = mount(GraphView, {
      global: {
        plugins: [router],
        stubs: { GraphCanvas: { template: "<div data-test='graph-canvas' />" } },
      },
    });
    await wrapper.get('[name="center_query"]').setValue("Atha01");
    await wrapper.get('[name="species_id"]').setValue("arabidopsis_thaliana");
    await wrapper.get('[name="predicate"]').setValue("belongs_to_species");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(searchNodes).toHaveBeenCalledWith(
      {
        q: "Atha01",
        objectType: "Gene",
        speciesId: "arabidopsis_thaliana",
        limit: 20,
      },
      expect.any(AbortSignal),
    );
    expect(getNeighbors).toHaveBeenCalledWith(
      center.node_id,
      { predicate: "belongs_to_species", limit: 100 },
      expect.any(AbortSignal),
    );
    expect(wrapper.text()).toContain("Atha01");
  });
});
