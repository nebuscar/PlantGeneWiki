<script setup lang="ts">
import { computed, ref } from "vue";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import GraphCanvas from "../components/graph/GraphCanvas.vue";
import GraphLegend from "../components/graph/GraphLegend.vue";
import GraphToolbar from "../components/graph/GraphToolbar.vue";
import NodeInspector from "../components/graph/NodeInspector.vue";
import { toCytoscapeElements } from "../lib/graph-elements";
import { getNeighbors, getNode, searchNodes } from "../services/graph";
import type { GraphNeighborhood, GraphNode } from "../types/graph";

const centerQuery = ref("");
const speciesId = ref("");
const predicate = ref("");
const neighborhood = ref<GraphNeighborhood | null>(null);
const selectedNode = ref<GraphNode | null>(null);
const loading = ref(false);
const error = ref("");
let controller: AbortController | null = null;

const graphCounts = computed(() => neighborhood.value
  ? toCytoscapeElements(neighborhood.value)
  : null);

function exactNode(nodes: GraphNode[], query: string) {
  return nodes.find((node) => node.node_id === query || node.label === query || node.properties.id === query);
}

async function loadGraph() {
  const query = centerQuery.value.trim();
  if (!query) return;
  controller?.abort();
  const requestController = new AbortController();
  controller = requestController;
  loading.value = true;
  error.value = "";
  try {
    let center: GraphNode;
    if (query.includes(":")) {
      center = await getNode(query, requestController.signal);
    } else {
      const result = await searchNodes(
        {
          q: query,
          objectType: "Gene",
          speciesId: speciesId.value.trim() || undefined,
          limit: 20,
        },
        requestController.signal,
      );
      center = exactNode(result.nodes, query) ?? result.nodes[0];
      if (!center) throw new Error(`Gene not found: ${query}`);
    }
    const result = await getNeighbors(center.node_id, {
      predicate: predicate.value.trim() || undefined,
      limit: 100,
    }, requestController.signal);
    if (controller !== requestController) return;
    neighborhood.value = result;
    selectedNode.value = result.node;
  } catch (reason) {
    if (reason instanceof DOMException && reason.name === "AbortError") return;
    if (controller === requestController) {
      error.value = reason instanceof Error ? reason.message : "Unable to load graph";
    }
  } finally {
    if (controller === requestController) loading.value = false;
  }
}
</script>

<template>
  <div class="graph-view">
    <header class="graph-heading">
      <p class="eyebrow">Relationship explorer</p>
      <h1>Knowledge Graph</h1>
      <p>Center the graph on an indexed Gene, filter its typed neighborhood, and inspect connected knowledge objects.</p>
    </header>
    <GraphToolbar
      v-model:center-query="centerQuery"
      v-model:species-id="speciesId"
      v-model:predicate="predicate"
      @submit="loadGraph"
    />
    <div class="graph-meta"><GraphLegend /><span v-if="graphCounts">{{ graphCounts.nodes.length }} nodes / {{ graphCounts.edges.length }} edges</span></div>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error"><button type="button" @click="loadGraph">Retry</button></ErrorState>
    <div v-else class="graph-layout">
      <GraphCanvas :neighborhood="neighborhood" @select="selectedNode = $event" />
      <NodeInspector :node="selectedNode" />
    </div>
  </div>
</template>

<style scoped>
.graph-heading { max-width: 820px; margin-bottom: 26px; }
.graph-heading h1 { margin-bottom: 12px; color: var(--color-forest-950); font-size: clamp(2.6rem, 6vw, 5rem); letter-spacing: -0.05em; }
.graph-heading > p:last-child { color: var(--color-muted); }
.graph-meta { display: flex; justify-content: space-between; gap: 20px; margin: 18px 0; color: var(--color-muted); font-size: 0.8rem; }
.graph-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(250px, 320px); gap: 20px; }
@media (max-width: 860px) { .graph-layout { grid-template-columns: 1fr; } }
</style>
