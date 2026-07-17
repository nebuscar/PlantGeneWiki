<script setup lang="ts">
import { computed } from "vue";
import { readFunctionAnnotations } from "../../lib/gene-record";
import type { GraphNode } from "../../types/graph";
import NotAvailable from "../objects/NotAvailable.vue";

const props = defineProps<{ node: GraphNode | null }>();
const annotations = computed(() => readFunctionAnnotations(props.node));
const available = computed(() =>
  Boolean(
    annotations.value.description ||
      annotations.value.goTerms.length ||
      annotations.value.tfType ||
      annotations.value.tfFamily,
  ),
);
</script>

<template>
  <div v-if="available" class="function-panel">
    <div v-if="annotations.description"><h3>Description</h3><p>{{ annotations.description }}</p></div>
    <div v-if="annotations.goTerms.length">
      <h3>Gene Ontology</h3>
      <ul class="go-list"><li v-for="term in annotations.goTerms" :key="term">{{ term }}</li></ul>
    </div>
    <dl v-if="annotations.tfType || annotations.tfFamily">
      <div><dt>TF Type</dt><dd>{{ annotations.tfType || "Not available" }}</dd></div>
      <div><dt>TF Family</dt><dd>{{ annotations.tfFamily || "Not available" }}</dd></div>
    </dl>
  </div>
  <NotAvailable v-else />
</template>

<style scoped>
.function-panel { display: grid; gap: 20px; }
.function-panel h3 { margin: 0 0 8px; color: var(--color-forest-950); font-size: 1rem; }
.function-panel p { margin: 0; line-height: 1.7; }
.go-list { display: flex; flex-wrap: wrap; gap: 8px; padding: 0; margin: 0; list-style: none; }
.go-list li { padding: 5px 9px; border: 1px solid var(--color-border); border-radius: 999px; background: var(--color-moss-50); color: var(--color-forest-700); font-size: 0.82rem; font-weight: 750; }
.function-panel dl { display: flex; flex-wrap: wrap; gap: 14px; margin: 0; }
.function-panel dl div { min-width: 150px; padding: 12px; border-left: 3px solid var(--color-forest-500); background: var(--color-moss-50); }
.function-panel dt { color: var(--color-muted); font-size: 0.76rem; font-weight: 800; text-transform: uppercase; }
.function-panel dd { margin: 4px 0 0; font-weight: 800; }
</style>
