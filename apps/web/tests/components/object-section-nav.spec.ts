import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ObjectSectionNav from "../../src/components/objects/ObjectSectionNav.vue";

const observe = vi.fn();

beforeEach(() => {
  observe.mockClear();
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe = observe;
      disconnect = vi.fn();
      unobserve = vi.fn();
    },
  );
  Element.prototype.scrollIntoView = vi.fn();
  document.body.innerHTML = '<section id="overview"></section><section id="function"></section>';
});

describe("ObjectSectionNav", () => {
  it("observes permanent sections and marks one active", () => {
    const wrapper = mount(ObjectSectionNav, {
      props: {
        sections: [
          { id: "overview", label: "Overview" },
          { id: "function", label: "Function" },
        ],
      },
    });
    expect(observe).toHaveBeenCalledTimes(2);
    expect(wrapper.get('a[href="#overview"]').classes()).toContain("is-active");
  });
});
