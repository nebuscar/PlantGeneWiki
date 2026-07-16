import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import GeneView from "../../src/views/GeneView.vue";
import { getNeighbors, resolveObject } from "../../src/services/graph";

vi.mock("../../src/services/graph", () => ({
  getNeighbors: vi.fn(),
  resolveObject: vi.fn(),
}));

const geneNode = {
  node_id: "gene:atha:Atha01G0000010.v1.36",
  object_type: "Gene",
  label: "Atha01G0000010.v1.36",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: {},
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(resolveObject).mockResolvedValue(geneNode);
  vi.mocked(getNeighbors).mockResolvedValue({ node: geneNode, nodes: [], edges: [] });
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe = vi.fn();
      disconnect = vi.fn();
      unobserve = vi.fn();
    },
  );
});

describe("GeneView", () => {
  it("keeps permanent sections when values are absent", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/genes/:id", name: "gene", component: GeneView }],
    });
    await router.push("/genes/Atha01G0000010.v1.36");
    const wrapper = mount(GeneView, { global: { plugins: [createPinia(), router] } });
    await flushPromises();
    for (const heading of [
      "Overview",
      "Identifiers",
      "Location",
      "Structure",
      "Function",
      "Sequences",
      "Homology",
      "Evidence",
      "Publications",
    ]) {
      expect(wrapper.text()).toContain(heading);
    }
    expect(wrapper.text()).toContain("Not available");
  });
});
