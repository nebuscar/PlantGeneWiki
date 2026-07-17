<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { groupSequenceRecords } from "../../lib/gene-record";
import type { SequenceType } from "../../lib/graph-presentation";
import { getNeighbors } from "../../services/graph";
import type { GraphNeighborhood } from "../../types/graph";
import GeneSequencePanel from "../genes/GeneSequencePanel.vue";

const props = defineProps<{
  open: boolean;
  centerNodeId: string;
  expectedCount: number;
}>();
const emit = defineEmits<{
  close: [];
  showType: [type: SequenceType, record: GraphNeighborhood];
}>();
const record = ref<GraphNeighborhood | null>(null);
const loading = ref(false);
const error = ref("");
let controller: AbortController | null = null;

const groups = computed(() => groupSequenceRecords(record.value?.nodes ?? []));
const returnedEdges = computed(() => record.value?.edges.length ?? 0);
const truncationMessage = computed(() =>
  record.value?.truncated
    ? `Showing ${returnedEdges.value} of ${record.value.matched_edges} sequence relationships.`
    : "",
);

function cancelRequest() {
  controller?.abort();
  controller = null;
}

async function loadRecord() {
  cancelRequest();
  record.value = null;
  error.value = "";
  if (!props.open || !props.centerNodeId) {
    loading.value = false;
    return;
  }
  const requestController = new AbortController();
  controller = requestController;
  loading.value = true;
  try {
    const result = await getNeighbors(
      props.centerNodeId,
      { predicate: "has_sequence", limit: 100 },
      requestController.signal,
    );
    if (controller === requestController) record.value = result;
  } catch (reason) {
    if (reason instanceof DOMException && reason.name === "AbortError") return;
    if (controller === requestController) {
      error.value = "Unable to load sequence relationships.";
    }
  } finally {
    if (controller === requestController) loading.value = false;
  }
}

function showType(type: SequenceType) {
  if (record.value) emit("showType", type, record.value);
}

watch(() => [props.open, props.centerNodeId], loadRecord, { immediate: true });
onBeforeUnmount(cancelRequest);
</script>

<template>
  <aside
    v-if="open"
    class="sequence-drawer"
    role="dialog"
    aria-modal="false"
    aria-labelledby="sequence-drawer-title"
  >
    <header class="sequence-drawer__header">
      <div>
        <h2 id="sequence-drawer-title">Sequence records</h2>
        <p>{{ expectedCount }} normalized sequence relationships</p>
      </div>
      <button type="button" class="sequence-drawer__close" aria-label="Close sequence drawer" @click="emit('close')">
        Close
      </button>
    </header>
    <p v-if="loading" class="sequence-drawer__state" role="status">
      Loading sequence relationships…
    </p>
    <div v-else-if="error" class="sequence-drawer__state" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="loadRecord">Retry</button>
    </div>
    <template v-else-if="record">
      <p v-if="truncationMessage" class="sequence-drawer__notice">
        {{ truncationMessage }}
      </p>
      <div class="sequence-drawer__actions" aria-label="Show real sequence nodes">
        <button
          type="button"
          data-sequence-type="CDS"
          :disabled="groups.cds.length === 0"
          @click="showType('CDS')"
        >
          CDS ({{ groups.cds.length }})
          <span>Show in graph</span>
        </button>
        <button
          type="button"
          data-sequence-type="PROTEIN"
          :disabled="groups.protein.length === 0"
          @click="showType('PROTEIN')"
        >
          Protein ({{ groups.protein.length }})
          <span>Show in graph</span>
        </button>
      </div>
      <GeneSequencePanel :nodes="record.nodes" />
    </template>
    <p v-else class="sequence-drawer__state">No sequence relationships are available.</p>
  </aside>
</template>

<style scoped>
.sequence-drawer {
  position: fixed;
  inset: 0 0 0 auto;
  z-index: 30;
  width: min(520px, 100vw);
  overflow-y: auto;
  padding: 24px;
  border-left: 1px solid var(--color-border);
  background: var(--color-surface);
  box-shadow: -18px 0 48px rgb(9 46 42 / 14%);
}
.sequence-drawer__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--color-border);
}
.sequence-drawer__header h2 {
  margin: 0 0 4px;
  color: var(--color-forest-950);
  font-size: 1.55rem;
}
.sequence-drawer__header p {
  margin: 0;
  color: var(--color-muted);
  font-size: 0.84rem;
}
.sequence-drawer__close,
.sequence-drawer__state button {
  min-height: 36px;
  padding: 7px 11px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-forest-700);
  background: #fff;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 750;
}
.sequence-drawer__state {
  min-height: 180px;
  display: grid;
  place-items: center;
  color: var(--color-muted);
  text-align: center;
}
.sequence-drawer__state p {
  margin-bottom: 10px;
}
.sequence-drawer__notice {
  padding: 10px 12px;
  border: 1px solid #dcd5f5;
  border-radius: 8px;
  color: #5c45ad;
  background: #f7f5ff;
  font-size: 0.82rem;
  font-weight: 700;
}
.sequence-drawer__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 22px;
}
.sequence-drawer__actions button {
  display: grid;
  gap: 3px;
  padding: 14px;
  border: 1px solid #dcd5f5;
  border-radius: 10px;
  color: #5c45ad;
  background: #f7f5ff;
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 800;
  text-align: left;
}
.sequence-drawer__actions button:hover:not(:disabled) {
  border-color: #7b61d1;
  background: #f1edff;
}
.sequence-drawer__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}
.sequence-drawer__actions span {
  font-size: 0.74rem;
  font-weight: 650;
}
@media (max-width: 520px) {
  .sequence-drawer {
    padding: 18px;
  }
  .sequence-drawer__actions {
    grid-template-columns: 1fr;
  }
}
</style>
