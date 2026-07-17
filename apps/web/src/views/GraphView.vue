<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import GraphCanvas from "../components/graph/GraphCanvas.vue";
import GraphLegend from "../components/graph/GraphLegend.vue";
import GraphToolbar from "../components/graph/GraphToolbar.vue";
import NodeInspector from "../components/graph/NodeInspector.vue";
import SequenceDrawer from "../components/graph/SequenceDrawer.vue";
import {
  DEFAULT_GRAPH_QUERY,
  graphQueryError,
  readGraphQuery,
  writeGraphQuery,
} from "../lib/graph-query";
import {
  filterSequenceNeighborhood,
  type SequenceType,
} from "../lib/graph-presentation";
import { getNeighbors, getNode, resolveObject } from "../services/graph";
import { ApiError } from "../services/http";
import type {
  GraphNeighborhood,
  GraphNode,
  GraphQueryState,
  GraphRecord,
  GraphSelection,
} from "../types/graph";

const route = useRoute();
const router = useRouter();
const centerQuery = ref("");
const speciesId = ref("");
const selectedPredicate = ref("");
const coreNeighborhood = ref<GraphNeighborhood | null>(null);
const selectedNode = ref<GraphNode | null>(null);
const loading = ref(false);
const error = ref("");
const validationError = ref("");
const sequenceDrawerOpen = ref(false);
const sequenceMode = ref<{ type: SequenceType; record: GraphRecord } | null>(null);
let requestController: AbortController | null = null;

const predicateCounts = computed(() => coreNeighborhood.value?.predicate_counts ?? {});
const sequenceCount = computed(() => predicateCounts.value.has_sequence ?? 0);
const activeRecord = computed(() => sequenceMode.value?.record ?? coreNeighborhood.value);
const activeSequenceCount = computed(() => (sequenceMode.value ? 0 : sequenceCount.value));
const displayedItemCount = computed(() => {
  if (!activeRecord.value) return 0;
  return activeRecord.value.nodes.length + 1 + (activeSequenceCount.value > 0 ? 1 : 0);
});

function cancelRequest() {
  requestController?.abort();
  requestController = null;
}

function errorMessage(reason: unknown, query: GraphQueryState): string {
  if (reason instanceof ApiError && reason.status === 503) {
    return "Knowledge graph is temporarily unavailable.";
  }
  if (reason instanceof ApiError && reason.status === 404) {
    return `Gene not found: ${query.center}.`;
  }
  if (reason instanceof Error && reason.name === "ObjectNotFoundError") {
    return `Gene not found: ${query.center}.`;
  }
  return "Unable to load the knowledge graph.";
}

async function loadGraph(query: GraphQueryState) {
  cancelRequest();
  const controller = new AbortController();
  requestController = controller;
  loading.value = true;
  error.value = "";
  validationError.value = "";
  try {
    const center = query.center.includes(":")
      ? await getNode(query.center, controller.signal)
      : await resolveObject("Gene", query.center, query.species, controller.signal);
    if (controller !== requestController) return;
    const options =
      query.predicate && query.predicate !== "has_sequence"
        ? { predicate: query.predicate, limit: 100 }
        : { excludePredicates: ["has_sequence"], limit: 100 };
    const result = await getNeighbors(center.node_id, options, controller.signal);
    if (controller !== requestController) return;
    coreNeighborhood.value = result;
    selectedNode.value = result.node;
  } catch (reason) {
    if (reason instanceof DOMException && reason.name === "AbortError") return;
    if (controller === requestController) {
      coreNeighborhood.value = null;
      selectedNode.value = null;
      error.value = errorMessage(reason, query);
    }
  } finally {
    if (controller === requestController) loading.value = false;
  }
}

async function loadRoute() {
  const routePath = route.fullPath;
  const parsed = readGraphQuery(route.query);
  if (parsed === null) {
    await router.replace({ name: "graph", query: writeGraphQuery(DEFAULT_GRAPH_QUERY) });
    return;
  }
  centerQuery.value = parsed.center;
  speciesId.value = parsed.species;
  selectedPredicate.value = parsed.predicate;
  sequenceDrawerOpen.value = false;
  sequenceMode.value = null;
  const validation = graphQueryError(parsed);
  validationError.value = validation;
  error.value = "";
  if (validation) {
    cancelRequest();
    loading.value = false;
    coreNeighborhood.value = null;
    selectedNode.value = null;
    return;
  }
  await loadGraph(parsed);
  if (
    route.fullPath === routePath &&
    parsed.predicate === "has_sequence" &&
    coreNeighborhood.value
  ) {
    sequenceDrawerOpen.value = true;
  }
}

async function navigateToQuery(query: GraphQueryState) {
  const location = { name: "graph", query: writeGraphQuery(query) };
  if (router.resolve(location).fullPath === route.fullPath) {
    await loadRoute();
    return;
  }
  await router.push(location);
}

async function submitGraph() {
  const query: GraphQueryState = {
    center: centerQuery.value.trim(),
    species: speciesId.value.trim(),
    view: "core",
    predicate: selectedPredicate.value,
  };
  const validation = graphQueryError(query);
  validationError.value = validation;
  if (validation) {
    cancelRequest();
    loading.value = false;
    return;
  }
  await navigateToQuery(query);
}

async function selectPredicate(predicate: string) {
  selectedPredicate.value = predicate;
  await navigateToQuery({
    center: centerQuery.value.trim(),
    species: speciesId.value.trim(),
    view: "core",
    predicate,
  });
}

function handleSelection(selection: GraphSelection) {
  if (selection.kind === "node") {
    selectedNode.value = selection.node;
    return;
  }
  void selectPredicate("has_sequence");
}

function closeSequenceDrawer() {
  sequenceDrawerOpen.value = false;
  sequenceMode.value = null;
  if (selectedPredicate.value === "has_sequence") void selectPredicate("");
}

function showSequenceType(type: SequenceType, record: GraphNeighborhood) {
  sequenceMode.value = {
    type,
    record: filterSequenceNeighborhood(record, type),
  };
  sequenceDrawerOpen.value = false;
  selectedNode.value = record.node;
}

function backToCore() {
  sequenceMode.value = null;
}

watch(() => route.fullPath, loadRoute, { immediate: true });
onBeforeUnmount(cancelRequest);
</script>

<template>
  <div class="graph-view">
    <header class="graph-heading">
      <p class="eyebrow">Relationship explorer</p>
      <h1>Knowledge Graph</h1>
      <p>
        Explore normalized relationships around a scoped Gene, then open real connected
        knowledge objects for details.
      </p>
    </header>
    <GraphToolbar
      v-model:center-query="centerQuery"
      v-model:species-id="speciesId"
      :predicate-counts="predicateCounts"
      :selected-predicate="selectedPredicate"
      :validation-error="validationError"
      @submit="submitGraph"
      @select-predicate="selectPredicate"
    />
    <div class="graph-meta">
      <GraphLegend />
      <div v-if="coreNeighborhood" class="graph-meta__counts" aria-live="polite">
        <span>{{ coreNeighborhood.total_edges }} source relationships</span>
        <span>{{ displayedItemCount }} displayed items</span>
        <span v-if="coreNeighborhood.truncated">
          Showing {{ coreNeighborhood.edges.length }} of {{ coreNeighborhood.matched_edges }} matches
        </span>
      </div>
    </div>
    <div v-if="sequenceMode" class="sequence-mode" role="status">
      <span>
        Viewing {{ sequenceMode.record.nodes.length }}
        {{ sequenceMode.type === "PROTEIN" ? "Protein" : "CDS" }} records
      </span>
      <button type="button" data-test="back-to-core" @click="backToCore">
        Back to core
      </button>
    </div>
    <LoadingState v-if="loading" />
    <ErrorState
      v-else-if="error"
      title="Knowledge graph unavailable"
      :message="error"
    >
      <button type="button" class="retry-button" @click="loadRoute">Retry</button>
    </ErrorState>
    <div v-else-if="activeRecord" class="graph-layout">
      <GraphCanvas
        :neighborhood="activeRecord"
        :sequence-count="activeSequenceCount"
        @select="handleSelection"
      />
      <NodeInspector :node="selectedNode" />
    </div>
    <div v-else class="graph-empty">
      Submit a valid scoped Gene to load its normalized neighborhood.
    </div>
    <SequenceDrawer
      :open="sequenceDrawerOpen"
      :center-node-id="coreNeighborhood?.node.node_id ?? ''"
      :expected-count="sequenceCount"
      @close="closeSequenceDrawer"
      @show-type="showSequenceType"
    />
  </div>
</template>

<style scoped>
.graph-heading {
  max-width: 820px;
  margin-bottom: 26px;
}
.graph-heading h1 {
  margin-bottom: 12px;
  color: var(--color-forest-950);
  font-size: clamp(2.6rem, 6vw, 5rem);
  letter-spacing: -0.05em;
  line-height: 1;
}
.graph-heading > p:last-child {
  max-width: 720px;
  color: var(--color-muted);
}
.graph-meta {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin: 18px 0;
  color: var(--color-muted);
  font-size: 0.8rem;
}
.graph-meta__counts {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px 16px;
  font-weight: 700;
}
.graph-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(250px, 320px);
  gap: 20px;
}
.sequence-mode {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid #dcd5f5;
  border-radius: 10px;
  color: #5c45ad;
  background: #f7f5ff;
  font-size: 0.86rem;
  font-weight: 750;
}
.sequence-mode button {
  min-height: 34px;
  padding: 6px 10px;
  border: 1px solid #7b61d1;
  border-radius: 8px;
  color: #5c45ad;
  background: #fff;
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 750;
}
.graph-empty {
  min-height: 240px;
  display: grid;
  place-items: center;
  padding: 32px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-muted);
  background: var(--color-surface);
  text-align: center;
}
.retry-button {
  margin-top: 4px;
  padding: 9px 14px;
  border: 0;
  border-radius: 8px;
  color: #fff;
  background: var(--color-forest-700);
  cursor: pointer;
  font-size: 0.86rem;
  font-weight: 750;
}
@media (max-width: 860px) {
  .graph-layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 600px) {
  .graph-meta {
    align-items: flex-start;
    flex-direction: column;
  }
  .graph-meta__counts {
    justify-content: flex-start;
  }
}
</style>
