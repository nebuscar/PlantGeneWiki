import { ref, toValue, watch, type MaybeRefOrGetter } from "vue";
import { getNeighbors, resolveObject } from "../services/graph";
import type { GraphNeighborhood, GraphNode } from "../types/graph";

export function useObjectRecord(objectType: string, publicId: MaybeRefOrGetter<string>) {
  const node = ref<GraphNode | null>(null);
  const neighborhood = ref<GraphNeighborhood | null>(null);
  const loading = ref(false);
  const error = ref("");
  let requestId = 0;

  async function reload() {
    const currentRequest = ++requestId;
    const id = toValue(publicId).trim();
    node.value = null;
    neighborhood.value = null;
    error.value = "";
    if (!id) {
      error.value = `${objectType} identifier is required`;
      return;
    }
    loading.value = true;
    try {
      const resolvedNode = await resolveObject(objectType, id);
      const resolvedNeighborhood = await getNeighbors(resolvedNode.node_id, { limit: 200 });
      if (currentRequest !== requestId) {
        return;
      }
      node.value = resolvedNode;
      neighborhood.value = resolvedNeighborhood;
    } catch (reason) {
      if (currentRequest !== requestId) {
        return;
      }
      error.value = reason instanceof Error ? reason.message : `Unable to load ${objectType}`;
    } finally {
      if (currentRequest === requestId) {
        loading.value = false;
      }
    }
  }

  watch(() => toValue(publicId), reload, { immediate: true });

  return { node, neighborhood, loading, error, reload };
}
