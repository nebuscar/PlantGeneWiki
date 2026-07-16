import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import GlobalSearch from "../../src/components/GlobalSearch.vue";

describe("GlobalSearch", () => {
  it("does not navigate for blank search", async () => {
    const wrapper = mount(GlobalSearch);
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("submit")).toBeUndefined();
  });

  it("emits trimmed search text", async () => {
    const wrapper = mount(GlobalSearch);
    await wrapper.get("input").setValue("  Atha01G0000010  ");
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("submit")).toEqual([["Atha01G0000010"]]);
  });
});
