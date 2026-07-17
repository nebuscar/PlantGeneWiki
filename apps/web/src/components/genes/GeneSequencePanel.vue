<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { groupSequenceRecords } from "../../lib/gene-record";
import type { GraphNode } from "../../types/graph";
import NotAvailable from "../objects/NotAvailable.vue";

const props = defineProps<{ nodes: GraphNode[] }>();
const groups = computed(() => groupSequenceRecords(props.nodes));
const available = computed(() => groups.value.cds.length + groups.value.protein.length > 0);
</script>

<template>
  <div v-if="available" class="sequence-groups">
    <section v-for="group in [{ label: 'CDS', records: groups.cds }, { label: 'Protein', records: groups.protein }]" :key="group.label">
      <h3>{{ group.label }} ({{ group.records.length }})</h3>
      <ul v-if="group.records.length">
        <li v-for="record in group.records" :key="record.nodeId">
          <RouterLink :to="{ name: 'sequence-record', params: { id: record.nodeId } }">{{ record.name }}</RouterLink>
          <span>{{ record.length === null ? "Length not available" : `${record.length} ${group.label === "CDS" ? "nt" : "aa"}` }}</span>
        </li>
      </ul>
      <NotAvailable v-else />
    </section>
  </div>
  <NotAvailable v-else />
</template>

<style scoped>
.sequence-groups { display: grid; gap: 22px; }
.sequence-groups h3 { margin: 0 0 10px; color: var(--color-forest-950); font-size: 1rem; }
.sequence-groups ul { display: grid; gap: 8px; padding: 0; margin: 0; list-style: none; }
.sequence-groups li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px 16px; padding: 12px 14px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-moss-50); }
.sequence-groups a { overflow-wrap: anywhere; font-weight: 750; }
.sequence-groups span { color: var(--color-muted); font-size: 0.86rem; }
</style>
