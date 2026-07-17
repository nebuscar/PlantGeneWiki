import { ref, toValue, watch, type MaybeRefOrGetter } from "vue";
import { getGeneWikiRecord, resolveObject } from "../services/graph";
import type { GeneWikiRecord, GraphNode } from "../types/graph";

export function useGeneRecord(
  publicId: MaybeRefOrGetter<string>,
  speciesId = "arabidopsis_thaliana",
) {
  const node = ref<GraphNode | null>(null);
  const record = ref<GeneWikiRecord | null>(null);
  const loading = ref(false);
  const error = ref("");
  let requestId = 0;

  async function reload() {
    const currentRequest = ++requestId;
    const id = toValue(publicId).trim();
    node.value = null;
    record.value = null;
    error.value = "";
    if (!id) {
      error.value = "Gene identifier is required";
      return;
    }
    loading.value = true;
    try {
      const resolvedNode = await resolveObject("Gene", id, speciesId);
      const resolvedRecord = await getGeneWikiRecord(resolvedNode.node_id);
      if (currentRequest !== requestId) {
        return;
      }
      node.value = resolvedNode;
      record.value = resolvedRecord;
    } catch (reason) {
      if (currentRequest !== requestId) {
        return;
      }
      error.value = reason instanceof Error ? reason.message : "Unable to load Gene";
    } finally {
      if (currentRequest === requestId) {
        loading.value = false;
      }
    }
  }

  watch(() => toValue(publicId), reload, { immediate: true });

  return { node, record, loading, error, reload };
}
