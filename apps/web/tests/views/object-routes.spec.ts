import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DatasetView from "../../src/views/DatasetView.vue";
import LiteratureView from "../../src/views/LiteratureView.vue";
import SequenceRecordView from "../../src/views/SequenceRecordView.vue";
import SpeciesView from "../../src/views/SpeciesView.vue";
import ToolsView from "../../src/views/ToolsView.vue";
import { getNeighbors, listSpeciesGenes, resolveObject } from "../../src/services/graph";

vi.mock("../../src/services/graph", () => ({
  getNeighbors: vi.fn(),
  listSpeciesGenes: vi.fn(),
  resolveObject: vi.fn(),
}));

const nodes = {
  Species: { node_id: "species:arabidopsis_thaliana", object_type: "Species", label: "Arabidopsis thaliana", species_id: "arabidopsis_thaliana", source_file: "species.jsonl", properties: {} },
  Dataset: { node_id: "dataset:test", object_type: "Dataset", label: "Test dataset", species_id: "arabidopsis_thaliana", source_file: "datasets.jsonl", properties: {} },
  SequenceRecord: { node_id: "seq:test", object_type: "SequenceRecord", label: "Test sequence", species_id: "arabidopsis_thaliana", source_file: "sequences.jsonl", properties: {} },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(resolveObject).mockImplementation(async (type) => nodes[type as keyof typeof nodes]);
  vi.mocked(getNeighbors).mockImplementation(async (id) => {
    const node = Object.values(nodes).find((item) => item.node_id === id)!;
    return {
      node,
      nodes: [],
      edges: [],
      total_edges: 0,
      matched_edges: 0,
      predicate_counts: {},
      truncated: false,
    };
  });
  vi.mocked(listSpeciesGenes).mockResolvedValue({ species_id: "arabidopsis_thaliana", total: 0, limit: 50, offset: 0, genes: [] });
  vi.stubGlobal("IntersectionObserver", class { observe = vi.fn(); disconnect = vi.fn(); unobserve = vi.fn(); });
});

async function mountRoute(path: string, name: string, component: object) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path, name, component }],
  });
  const target = path.replace(":id", name === "species" ? "arabidopsis_thaliana" : "test");
  await router.push(target);
  const wrapper = mount(component, { global: { plugins: [createPinia(), router] } });
  await flushPromises();
  return wrapper;
}

describe("object routes", () => {
  it.each([
    ["/species/:id", "species", SpeciesView, "Species"],
    ["/datasets/:id", "dataset", DatasetView, "Dataset"],
    ["/sequence-records/:id", "sequence-record", SequenceRecordView, "SequenceRecord"],
  ])("renders %s as the correct object type", async (path, name, component, label) => {
    const wrapper = await mountRoute(path, name, component);
    expect(wrapper.text()).toContain(label);
    expect(wrapper.text()).toContain("Not available");
  });
});

describe("planning routes", () => {
  it.each([
    ["/literature", "literature", LiteratureView],
    ["/tools", "tools", ToolsView],
  ])("renders an honest planned module for %s", async (path, name, component) => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path, name, component }],
    });
    await router.push(path);
    const wrapper = mount(component, { global: { plugins: [router] } });
    expect(wrapper.text()).toContain("Planned module");
    expect(wrapper.find("button").exists()).toBe(false);
  });
});
