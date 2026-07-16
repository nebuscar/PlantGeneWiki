<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import type { GraphNode } from "../../types/graph";

const props = defineProps<{ node: GraphNode | null }>();

const wikiRoute = computed(() => {
  if (!props.node) return null;
  const routes: Record<string, string> = {
    Gene: "gene",
    Species: "species",
    Dataset: "dataset",
    SequenceRecord: "sequence-record",
  };
  const name = routes[props.node.object_type];
  if (!name) return null;
  const propertyId = props.node.properties.id;
  const id = typeof propertyId === "string" ? propertyId : props.node.label || props.node.node_id;
  return { name, params: { id } };
});
</script>

<template>
  <aside class="node-inspector">
    <template v-if="node">
      <span>{{ node.object_type }}</span>
      <h2>{{ node.label || node.node_id }}</h2>
      <code>{{ node.node_id }}</code>
      <dl>
        <div><dt>Species</dt><dd>{{ node.species_id || "Not available" }}</dd></div>
        <div><dt>Source</dt><dd>{{ node.source_file || "Not available" }}</dd></div>
      </dl>
      <RouterLink v-if="wikiRoute" class="inspector-link" :to="wikiRoute">Open Wiki page</RouterLink>
    </template>
    <p v-else>Select a node to inspect its indexed metadata.</p>
  </aside>
</template>

<style scoped>
.node-inspector { min-height: 260px; padding: 24px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }
.node-inspector > span { color: var(--color-leaf-600); font-size: 0.75rem; font-weight: 800; text-transform: uppercase; }
.node-inspector h2 { margin: 8px 0; overflow-wrap: anywhere; color: var(--color-forest-950); font-size: 1.35rem; }
.node-inspector code { overflow-wrap: anywhere; color: var(--color-muted); font-size: 0.75rem; }
dl { display: grid; gap: 10px; margin: 22px 0; }
dl div { display: grid; gap: 3px; }
dt { color: var(--color-muted); font-size: 0.76rem; font-weight: 750; text-transform: uppercase; }
dd { margin: 0; overflow-wrap: anywhere; }
.inspector-link { display: inline-block; padding: 9px 12px; border-radius: 8px; color: #fff; background: var(--color-forest-700); text-decoration: none; font-weight: 750; }
</style>
