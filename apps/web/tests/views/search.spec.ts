import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SearchView from "../../src/views/SearchView.vue";
import { searchNodes } from "../../src/services/graph";

vi.mock("../../src/services/graph", () => ({
  searchNodes: vi.fn(),
}));

function createTestRouter(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/search", name: "search", component: SearchView }],
  });
  void router.push(path);
  return router;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(searchNodes).mockResolvedValue({ query: "", count: 0, nodes: [] });
});

describe("SearchView", () => {
  it("loads filters from route query", async () => {
    const router = createTestRouter(
      "/search?q=Atha&object_type=Gene&species_id=arabidopsis_thaliana",
    );
    await router.isReady();
    const wrapper = mount(SearchView, { global: { plugins: [createPinia(), router] } });
    await flushPromises();
    expect((wrapper.get('[name="q"]').element as HTMLInputElement).value).toBe("Atha");
    expect((wrapper.get('[name="object_type"]').element as HTMLSelectElement).value).toBe("Gene");
    expect((wrapper.get('[name="species_id"]').element as HTMLInputElement).value).toBe(
      "arabidopsis_thaliana",
    );
    expect(searchNodes).toHaveBeenCalledWith(
      {
        q: "Atha",
        objectType: "Gene",
        speciesId: "arabidopsis_thaliana",
        limit: 25,
      },
      expect.any(AbortSignal),
    );
  });

  it("does not search for an empty query", async () => {
    const router = createTestRouter("/search");
    await router.isReady();
    mount(SearchView, { global: { plugins: [createPinia(), router] } });
    await flushPromises();
    expect(searchNodes).not.toHaveBeenCalled();
  });

  it("does not render unsupported evidence filters", async () => {
    const router = createTestRouter("/search?q=Atha");
    await router.isReady();
    const wrapper = mount(SearchView, { global: { plugins: [createPinia(), router] } });
    await flushPromises();
    expect(wrapper.find('[name="evidence_count"]').exists()).toBe(false);
  });
});
