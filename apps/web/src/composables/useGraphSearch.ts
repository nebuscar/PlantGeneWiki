import { onBeforeUnmount, reactive, ref } from "vue";
import { searchNodes } from "../services/graph";
import type { GraphNode } from "../types/graph";

export interface GraphSearchFilters {
  q: string;
  objectType: string;
  speciesId: string;
  limit: number;
}

export function useGraphSearch() {
  const filters = reactive<GraphSearchFilters>({
    q: "",
    objectType: "",
    speciesId: "",
    limit: 25,
  });
  const loading = ref(false);
  const error = ref("");
  const nodes = ref<GraphNode[]>([]);
  const count = ref(0);
  let controller: AbortController | null = null;

  function setFilters(values: Partial<GraphSearchFilters>) {
    Object.assign(filters, values);
  }

  async function executeSearch() {
    controller?.abort();
    controller = null;
    error.value = "";

    const query = filters.q.trim();
    if (!query) {
      loading.value = false;
      nodes.value = [];
      count.value = 0;
      return;
    }

    controller = new AbortController();
    const requestController = controller;
    loading.value = true;
    try {
      const result = await searchNodes(
        {
          q: query,
          objectType: filters.objectType || undefined,
          speciesId: filters.speciesId || undefined,
          limit: filters.limit,
        },
        controller.signal,
      );
      if (controller !== requestController) {
        return;
      }
      nodes.value = result.nodes;
      count.value = result.count;
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") {
        return;
      }
      error.value = reason instanceof Error ? reason.message : "Search request failed";
      nodes.value = [];
      count.value = 0;
    } finally {
      if (controller === requestController) {
        loading.value = false;
      }
    }
  }

  onBeforeUnmount(() => controller?.abort());

  return { filters, loading, error, nodes, count, setFilters, executeSearch };
}
