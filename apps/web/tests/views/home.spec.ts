import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AppHeader from "../../src/components/AppHeader.vue";
import HomeView from "../../src/views/HomeView.vue";
import { getGraphSummary } from "../../src/services/graph";

vi.mock("../../src/services/graph", () => ({
  getGraphSummary: vi.fn(),
}));

const summary = {
  database: "graph.sqlite",
  node_count: 100_000_000,
  edge_count: 120_000_000,
  node_types: { Gene: 80_000_000, Species: 500 },
  edge_predicates: { belongs_to_species: 80_000_000 },
};

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "home", component: HomeView },
      { path: "/search", name: "search", component: { template: "<div />" } },
      { path: "/graph", name: "graph", component: { template: "<div />" } },
      { path: "/literature", name: "literature", component: { template: "<div />" } },
      { path: "/tools", name: "tools", component: { template: "<div />" } },
    ],
  });
}

beforeEach(() => {
  vi.mocked(getGraphSummary).mockResolvedValue(summary);
});

describe("HomeView", () => {
  it("loads graph summary metrics", async () => {
    const router = createTestRouter();
    await router.push("/");
    const wrapper = mount(HomeView, { global: { plugins: [createPinia(), router] } });
    await flushPromises();
    expect(getGraphSummary).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("100,000,000");
    expect(wrapper.text()).toContain("120,000,000");
  });
  it("routes successful searches to the search view", async () => {
    const router = createTestRouter();
    await router.push("/");
    const wrapper = mount(HomeView, { global: { plugins: [createPinia(), router] } });
    await flushPromises();
    await wrapper.get("input").setValue("  Atha01G0000010  ");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(router.currentRoute.value).toMatchObject({
      name: "search",
      query: { q: "Atha01G0000010" },
    });
  });
});

describe("AppHeader", () => {
  it("hides compact search on the home route", async () => {
    const router = createTestRouter();
    await router.push("/");
    const wrapper = mount(AppHeader, { global: { plugins: [createPinia(), router] } });
    expect(wrapper.find(".header-search").exists()).toBe(false);
    await router.push("/search");
    await flushPromises();
    expect(wrapper.find(".header-search").exists()).toBe(true);
  });
});
