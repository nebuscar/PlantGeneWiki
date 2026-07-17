<script setup lang="ts">
import cytoscape, { type Core } from "cytoscape";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { toCytoscapeElements } from "../../lib/graph-elements";
import { graphStyles } from "../../lib/graph-style";
import type { GraphRecord, GraphSelection } from "../../types/graph";

const props = withDefaults(
  defineProps<{ neighborhood: GraphRecord | null; sequenceCount?: number }>(),
  { sequenceCount: 0 },
);
const emit = defineEmits<{ select: [selection: GraphSelection] }>();
const container = ref<HTMLElement | null>(null);
let graph: Core | null = null;

function renderGraph() {
  if (!container.value || !props.neighborhood) {
    graph?.elements().remove();
    return;
  }
  const elements = toCytoscapeElements(props.neighborhood, {
    sequenceCount: props.sequenceCount,
  });
  graph?.destroy();
  graph = cytoscape({
    container: container.value,
    elements: [...elements.nodes, ...elements.edges],
    layout: { name: "cose", animate: false, fit: true, padding: 36 },
    style: graphStyles,
  });
  graph.on("tap", "node", (event) => {
    const selection = elements.selectionById.get(event.target.id());
    if (selection) emit("select", selection);
  });
  graph.on("mouseover", "node, edge", (event) => event.target.addClass("hovered"));
  graph.on("mouseout", "node, edge", (event) => event.target.removeClass("hovered"));
  graph.getElementById(props.neighborhood.node.node_id).select();
}

onMounted(() => {
  void nextTick(renderGraph);
});

watch(
  () => [props.neighborhood, props.sequenceCount],
  () => void nextTick(renderGraph),
  { deep: true },
);
onBeforeUnmount(() => graph?.destroy());
</script>

<template>
  <div ref="container" class="graph-canvas" aria-label="Interactive knowledge graph"></div>
</template>

<style scoped>
.graph-canvas { width: 100%; height: min(68vh, 720px); min-height: 480px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: radial-gradient(circle at center, #fff, var(--color-moss-50)); }
</style>
