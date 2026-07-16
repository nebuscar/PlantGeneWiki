<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import type { GraphNode } from "../../types/graph";

const props = defineProps<{ node: GraphNode }>();

const routeName = computed(() => {
  const routes: Record<string, string> = {
    Gene: "gene",
    Species: "species",
    Dataset: "dataset",
    SequenceRecord: "sequence-record",
  };
  return routes[props.node.object_type] ?? "";
});

const publicId = computed(() => {
  const propertyId = props.node.properties.id;
  if (typeof propertyId === "string" && propertyId) {
    return propertyId;
  }
  return props.node.label || props.node.node_id;
});
</script>

<template>
  <article class="search-result-card">
    <div class="result-meta">
      <span>{{ node.object_type }}</span>
      <span v-if="node.species_id">{{ node.species_id }}</span>
    </div>
    <h2>
      <RouterLink v-if="routeName" :to="{ name: routeName, params: { id: publicId } }">
        {{ node.label || node.node_id }}
      </RouterLink>
      <span v-else>{{ node.label || node.node_id }}</span>
    </h2>
    <p>{{ node.node_id }}</p>
  </article>
</template>

<style scoped>
.search-result-card { padding: 24px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); box-shadow: var(--shadow-card); }
.result-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; color: var(--color-muted); font-size: 0.78rem; font-weight: 700; text-transform: uppercase; }
.result-meta span { padding: 4px 8px; border-radius: 999px; background: var(--color-moss-100); }
h2 { margin-bottom: 8px; font-size: 1.25rem; }
h2 a { color: var(--color-forest-900); text-decoration: none; }
h2 a:hover { text-decoration: underline; }
p { margin: 0; overflow-wrap: anywhere; color: var(--color-muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; }
</style>
