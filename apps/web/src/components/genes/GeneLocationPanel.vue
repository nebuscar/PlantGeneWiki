<script setup lang="ts">
import { computed } from "vue";
import { readGenomeLocation } from "../../lib/gene-record";
import type { GraphNode } from "../../types/graph";
import NotAvailable from "../objects/NotAvailable.vue";

const props = defineProps<{ node: GraphNode | null }>();
const location = computed(() => readGenomeLocation(props.node));
const available = computed(() => Object.values(location.value).some(Boolean));
</script>

<template>
  <dl v-if="available" class="field-grid">
    <div><dt>Assembly</dt><dd>{{ location.assembly || "Not available" }}</dd></div>
    <div><dt>Coordinates</dt><dd>{{ location.coordinates || "Not available" }}</dd></div>
    <div><dt>Strand</dt><dd>{{ location.strand || "Not available" }}</dd></div>
    <div><dt>Coordinate system</dt><dd>{{ location.coordinateSystem || "Not available" }}</dd></div>
  </dl>
  <NotAvailable v-else />
</template>

<style scoped>
.field-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 0; }
.field-grid div { padding: 14px; border: 1px solid var(--color-border); border-radius: 9px; background: var(--color-moss-50); }
.field-grid dt { margin-bottom: 6px; color: var(--color-muted); font-size: 0.76rem; font-weight: 800; text-transform: uppercase; }
.field-grid dd { margin: 0; overflow-wrap: anywhere; color: var(--color-forest-950); font-weight: 700; }
</style>
