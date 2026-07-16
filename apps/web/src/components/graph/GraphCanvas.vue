<script setup lang="ts">
import cytoscape, { type Core } from "cytoscape";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { toCytoscapeElements } from "../../lib/graph-elements";
import type { GraphNeighborhood, GraphNode } from "../../types/graph";

const props = defineProps<{ neighborhood: GraphNeighborhood | null }>();
const emit = defineEmits<{ select: [node: GraphNode] }>();
const container = ref<HTMLElement | null>(null);
let graph: Core | null = null;

function renderGraph() {
  if (!container.value || !props.neighborhood) {
    graph?.elements().remove();
    return;
  }
  const elements = toCytoscapeElements(props.neighborhood);
  graph?.destroy();
  graph = cytoscape({
    container: container.value,
    elements: [...elements.nodes, ...elements.edges],
    layout: { name: "cose", animate: false, fit: true, padding: 36 },
    style: [
      {
        selector: "node",
        style: {
          "background-color": "#71808a",
          label: "data(label)",
          color: "#17332d",
          "font-size": 10,
          "text-wrap": "ellipsis",
          "text-max-width": "110px",
          "text-valign": "bottom",
          "text-margin-y": 8,
          width: 34,
          height: 34,
        },
      },
      { selector: 'node[objectType = "Gene"]', style: { "background-color": "#1769aa" } },
      { selector: 'node[objectType = "Species"]', style: { "background-color": "#3b8c59" } },
      { selector: 'node[objectType = "Dataset"]', style: { "background-color": "#d77a1f" } },
      { selector: 'node[objectType = "SequenceRecord"]', style: { "background-color": "#7b61d1" } },
      { selector: "node[?isCenter]", style: { width: 48, height: 48, "border-width": 4, "border-color": "#0b3d36" } },
      {
        selector: "edge",
        style: {
          width: 1.6,
          "line-color": "#aab8b1",
          "target-arrow-color": "#aab8b1",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          label: "data(predicate)",
          "font-size": 8,
          color: "#627067",
          "text-background-color": "#ffffff",
          "text-background-opacity": 0.85,
          "text-background-padding": "2px",
        },
      },
      { selector: "node:selected", style: { "border-width": 5, "border-color": "#68a65f" } },
    ],
  });
  graph.on("tap", "node", (event) => {
    const node = elements.nodeById.get(event.target.id());
    if (node) emit("select", node);
  });
  graph.getElementById(props.neighborhood.node.node_id).select();
}

onMounted(() => {
  void nextTick(renderGraph);
});

watch(() => props.neighborhood, () => void nextTick(renderGraph), { deep: true });
onBeforeUnmount(() => graph?.destroy());
</script>

<template>
  <div ref="container" class="graph-canvas" aria-label="Interactive knowledge graph"></div>
</template>

<style scoped>
.graph-canvas { width: 100%; height: min(68vh, 720px); min-height: 480px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: radial-gradient(circle at center, #fff, var(--color-moss-50)); }
</style>
