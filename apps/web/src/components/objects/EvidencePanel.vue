<script setup lang="ts">
import type { GraphEdge } from "../../types/graph";
import NotAvailable from "./NotAvailable.vue";

defineProps<{ edges: GraphEdge[] }>();
</script>

<template>
  <ul v-if="edges.length" class="evidence-list">
    <li v-for="(edge, index) in edges" :key="`${edge.source}-${edge.predicate}-${edge.target}-${index}`">
      <div>
        <strong>{{ edge.predicate }}</strong>
        <span class="evidence-status">{{ edge.evidence ? "Asserted" : "Inferred" }}</span>
      </div>
      <span>{{ edge.evidence || edge.source_dataset || "Evidence-linked relation" }}</span>
      <code>{{ edge.source }} -> {{ edge.target }}</code>
    </li>
  </ul>
  <NotAvailable v-else />
</template>

<style scoped>
.evidence-list { display: grid; gap: 12px; padding: 0; margin: 0; list-style: none; }
.evidence-list li { display: grid; gap: 8px; padding: 16px; border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-moss-50); }
.evidence-list div { display: flex; justify-content: space-between; gap: 16px; }
.evidence-list span { color: var(--color-muted); }
.evidence-status { color: var(--color-forest-700) !important; font-size: 0.76rem; font-weight: 800; text-transform: uppercase; }
code { overflow-wrap: anywhere; color: var(--color-forest-700); font-size: 0.8rem; }
</style>
